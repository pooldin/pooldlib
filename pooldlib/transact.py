"""
pooldlib.api.transact
===============================

.. currentmodule:: pooldlib.api.transact

"""
from uuid import uuid4 as uuid
from decimal import Decimal
from collections import defaultdict


from pooldlib.sqlalchemy import transaction_session
from pooldlib.postgresql import (Transaction as TransactionModel,
                                 Transfer as TransferModel,
                                 ExternalLedger as ExternalLedgerModel,
                                 InternalLedger as InternalLedgerModel,
                                 CampaignGoalLedger as CampaignGoalLedgerModel)
from pooldlib.exceptions import (InsufficentFundsTransferError,
                                 InsufficentFundsTransactionError)


class Transact(object):
    """``pooldlib`` API for working with user/user, user/campaign, etc transfers and
    (external) transactions. A user depositing funds in their poold account via stripe
    would be an example (external) transaction.

    Example User to Campaign transfer:

        >>> t = Transact()
        >>> t.transfer(Decimal('25.0000'), destination=a_campaign, origin=a_user)
        >>> if not t.verify(): raise TransactionError()
        >>> t.execute()
        >>> # (USD) Balance of a_user is decreased by $25.000
        >>> # (USD) Balance of a_campaign is increased by $25.000

    Example User to Campaign Goal transfer with Fee:

        >>> t = Transact()
        >>> currency = CurrencyModel.query.filter_by(code='USD').first()
        >>> fee = FeeModel.query.get(1)
        >>> t.transfer_to_campaign_goal(Decimal('25.0000'), currency, a_campaign_goal, a_user)
        >>> t.transfer(Decimal('1.0000'), currency, destination=pooldin_co_user, origin=a_user, fee=fee)
        >>> if not t.verify(): raise TransactionError()
        >>> t.execute()
        >>> # (USD) Balance of a_user is decreased by $26.00.
        >>> # (USD) Balance of a_campaign is increased by $25.00, and a
        >>> # transfer of $25.00 is registered for a_campaign_goal.

    Example transaction usage:

        >>> t = Transact()
        >>> currency = CurrencyModel.query.filter_by(code='USD').first()
        >>> fee = FeeModel.query.get(1)
        >>> t.transaction(a_user, 'stripe', 'stripe-reference-number', currency, credit=Decimal('50.0000'))
        >>> t.transaction(a_user, 'stripe', 'stripe-reference-number', currency, debit=Decimal('5.0000'), fee=fee)
        >>> t.transaction(a_user, 'poold', 'stripe-reference-number', currency, debit=Decimal('5.0000'), fee=fee)
        >>> if not t.verify(): raise TransactionError()
        >>> t.execute()
        >>> # (USD) Balance of a_user is increased by $40.00.
    """

    def __init__(self):
        self.reset()

    def transfer_to_campaign_goal(self, amount, currency, campaign_goal, transfer_from, id=None):
        """Add a balance **transfer** to the `Transact` list. Use this method if the balance
        transfer is contributing to a specific ``CampaignGoal``. Funds will be transfered *from*
        ``transfer_from`` *to* ``campaign_goal.campaign`` and accounted for in the `CampaignGoalLedger`
        for ``campaign_goal``.

        :param amount: Amount of currency to be transferred.
        :type amount: decimal.Decimal
        :param currency: Currency for which to execute the transfer.
        :type currency: :class:`pooldlib.postgresql.models.Currency`
        :param campaign_goal: Instance of balance holding model which is receiving in the transfer.
        :type campaign_goal: :class:`pooldlib.postgresql.models.CampaignGoal`
        :param transfer_from: The balance holder which is contributing to ``campaign_goal``.
        :type transfer_from: :class:`pooldlib.postgresql.models.User` or
                             :class:`pooldlib.postgresql.models.Campaign`
        """
        if amount is None:
            raise TypeError("``amount`` cannot be None.")
        if currency is None:
            raise TypeError("``currency`` cannot be None.")
        self.transfer(amount,
                      currency,
                      destination=campaign_goal.campaign,
                      origin=transfer_from,
                      id=id)

        self._record_campaign_goal_transfer(campaign_goal, transfer_from, credit=amount)

    def transfer_from_campaign_goal(self, amount, currency, campaign_goal, transfer_to, id=None):
        """Add a balance **transfer** to the `Transact` list. Use this method if the balance
        transfer is originating from a specific ``CampaignGoal``. Funds will be transfered *from*
        ``campaign_goal.campaign`` *to* ``transfer_to`` and accounted for in the `CampaignGoalLedger`
        for ``campaign_goal``.

        :param amount: Amount of currency to be transferred.
        :type amount: decimal.Decimal
        :param currency: Currency for which to execute the transfer.
        :type currency: :class:`pooldlib.postgresql.models.Currency`
        :param campaign_goal: Instance of balance holding model which is sending in the transfer.
        :type campaign_goal: :class:`pooldlib.postgresql.models.CampaignGoal`
        :param transfer_to: The balance holder which is recieving in the transfer from ``campaign_goal``.
        :type transfer_to: :class:`pooldlib.postgresql.models.User` or
                           :class:`pooldlib.postgresql.models.Campaign`
        """
        if amount is None:
            raise TypeError("``amount`` cannot be None.")
        if currency is None:
            raise TypeError("``currency`` cannot be None.")
        self.transfer(amount,
                      currency,
                      destination=transfer_to,
                      origin=campaign_goal.campaign,
                      id=id)

        self._record_campaign_goal_transfer(campaign_goal, transfer_to, debit=amount)

    def transfer(self, amount, currency, destination=None, origin=None, fee=None, id=None):
        """Add a balance **transfer** to the `Transact` list.  Valid transfers are:

            - :class:`pooldlib.postgresql.models.User` to :class:`pooldlib.postgresql.models.User`
            - :class:`pooldlib.postgresql.models.User` to :class:`pooldlib.postgresql.models.Campaign`
            - :class:`pooldlib.postgresql.models.Campaign` to :class:`pooldlib.postgresql.models.User`

        :param amount: Amount of currency to be transferred.
        :type amount: decimal.Decimal
        :param origin: Instance of balance holding model which is receiving in the transfer.
        :type origin: :class:`pooldlib.postgresql.models.User` or
                      :class:`pooldlib.postgresql.models.Campaign`
        :param origin: Instance of balance holding model which is sending in the transfer.
        :type origin: :class:`pooldlib.postgresql.models.User` or
                      :class:`pooldlib.postgresql.models.Campaign`
        :param currency: Currency type for which to execute the transfer.
        :type currency: :class:`pooldlib.postgresql.models.Currency` or string.
        :param fee: Fee associated with the transfer.
        :type fee: :class:`pooldlib.postgresql.models.Fee`, string name of Fee or integer id of Fee.
        """
        party = None
        if fee:
            party = getattr(destination, 'username', None) or destination.name
        credit_balance = destination.balance_for_currency(currency, for_update=True)
        self._transfer_credit(credit_balance, amount, fee=fee, party=party, id=id)

        party = None
        if fee:
            party = getattr(origin, 'username', None) or origin.name
        debit_balance = origin.balance_for_currency(currency, for_update=True)
        self._transfer_debit(debit_balance, amount, fee=fee, party=party, id=id)

    def transaction(self, balance_holder, external_party, external_reference, currency, debit=None, credit=None, fee=None, id=None):
        """Add an external **transaction** to the `Transact` list.
        One of either ``debit`` or ``credit`` **must** be defined.

        :param balance_holder: Instance of the balance holding model which
                               is involved in the transaction.
        :type balance_holder: :class:`pooldlib.postgresql.models.User` or
                              :class:`pooldlib.postgresql.models.Campaign`
        :param external_party: The third party facilitating the transaction (i.e. stripe, etc).
        :type external_party: string
        :param external_reference: Identifier provided by third party referencing transaction.
        :type external_reference: string.
        :param currency: Currency type for which to execute the transfer.
        :type currency: :class:`pooldlib.postgresql.models.Currency`
        :param debit: The amount to be debited from the target balance.
        :type debit: decimal.Decimal or `None`.
        :param credit: The amount to be credited to the target balance.
        :type credit: decimal.Decimal or `None`.
        :param fee: Fee associated with the transfer.
        :type fee: :class:`pooldlib.postgresql.models.Fee`, string name of Fee or integer id of Fee.
        """
        txn_balance = balance_holder.balance_for_currency(currency, for_update=True)
        if credit is not None:
            self._transaction_credit(txn_balance, credit, fee=fee, id=id)
        elif debit is not None:
            self._transaction_debit(txn_balance, debit, fee=fee, id=id)

    def external_ledger(self, balance_holder, processor, reference_number, currency,
                        debit=None, credit=None, fee=None, id=None, full_name=None):
        balance = balance_holder.balance_for_currency(currency, for_update=True)
        el = self._new_external_ledger(processor,
                                       balance.currency,
                                       'transaction',
                                       reference_number,
                                       fee,
                                       credit=credit,
                                       debit=debit,
                                       id=id,
                                       full_name=full_name)
        self._external_ledger_items.append(el)

    def verify(self):
        """Verify that there are no errors associated with the transact list.

        :returns: bool -- ``True`` if no errors are found.
        """
        return len(self._errors) == 0

    def execute(self):
        """Atomically execute the full transact list.

        :raises: InsufficentFundsTransferError
        """
        if self._errors:
            exc, msg = self._errors.pop()
            self.reset()
            raise exc(msg)

        with transaction_session(auto_commit=True) as session:
            for xfer_class_values in self._transfers.values():
                for xfer in xfer_class_values.values():
                    session.add(xfer)
            session.flush()

            for txn_class_values in self._transactions.values():
                for txn in txn_class_values.values():
                    session.add(txn)
            session.flush()

    def reset(self):
        """Reset the current state of the transact list.
        """
        self._transfers = defaultdict(lambda: defaultdict(int))
        self._internal_ledger_items = list()
        self._transactions = defaultdict(lambda: defaultdict(int))
        self._external_ledger_items = list()
        self._errors = list()
        self.id = uuid()

    def _transfer_credit(self, balance, amount, fee=None, party=None, id=None):
        t = self._transfers['credit'][balance.id] or self._new_transfer(balance, id=id)
        t.credit = t.credit or Decimal('0.0000')
        t.credit += amount
        balance.amount += amount

        if fee:
            il = self._new_internal_ledger(party,
                                           balance.currency,
                                           'transfer',
                                           fee,
                                           credit=amount,
                                           id=None)
            self._internal_ledger_items.append(il)

        self._transfers['credit'][balance.id] = t

    def _transfer_debit(self, balance, amount, fee=None, party=None, id=None):
        t = self._transfers['debit'][balance.id] or self._new_transfer(balance, id=id)
        t.debit = t.debit or Decimal('0.0000')
        t.debit += amount
        balance.amount -= amount

        if fee:
            il = self._new_internal_ledger(party,
                                           balance.currency,
                                           'transfer',
                                           fee,
                                           debit=amount,
                                           id=None)
            self._internal_ledger_items.append(il)

        if balance.amount < Decimal('0.0000'):
            msg = 'Transfer of %s failed, %s balance %s has insufficient funds (%s).'
            msg %= (amount, balance.type, balance, balance.amount)
            self._errors.append((InsufficentFundsTransferError, msg))

        self._transfers['debit'][balance.id] = t

    def _transaction_credit(self, balance, amount, fee=None, id=None):
        t = self._transactions['credit'][balance.id] or self._new_transaction(balance, id=id)
        t.credit = t.credit or Decimal('0.0000')
        t.credit += amount
        balance.amount += amount
        self._transactions['credit'][balance.id] = t

    def _transaction_debit(self, balance, amount, fee=None, id=None):
        t = self._transactions['debit'][balance.id] or self._new_transaction(balance, id=id)
        t.debit = t.debit or Decimal('0.0000')
        t.debit += amount
        balance.amount -= amount

        if balance.amount < Decimal('0.0000'):
            msg = 'Transaction of %s failed, %s balance %s has insufficient funds (%s).'
            msg %= (amount, balance.type, balance, balance.amount)
            self._errors.append((InsufficentFundsTransactionError, msg))

        self._transactions['debit'][balance.id] = t

    def _new_transfer(self, balance, id=None):
        t = TransferModel()
        t.balance = balance
        t.record_id = id or self.id
        return t

    def _new_transaction(self, balance, id=None):
        t = TransactionModel()
        t.balance = balance
        t.id = id or self.id
        return t

    def _new_internal_ledger(self, party, currency, record_table, fee, debit=None, credit=None, id=None):
        il = InternalLedgerModel()
        il.record_id = id or self.id
        il.record_table = record_table
        il.party = party
        il.currency = currency
        il.fee = fee

        if credit is not None:
            il.credit = credit
        elif debit is not None:
            il.debit = debit
        return il

    def _new_external_ledger(self, processor, currency, record_table, reference_number,
                             fee, debit=None, credit=None, id=None, full_name=None):
        el = ExternalLedgerModel()
        el.record_id = id or self.id
        el.record_table = record_table
        el.reference_number = reference_number
        el.processor = processor
        el.currency = currency
        el.fee = fee
        el.full_name = full_name

        if credit is not None:
            el.credit = credit
        elif debit is not None:
            el.debit = debit
        return el

    def _record_campaign_goal_transfer(self, campaign_goal, transferrer, debit=None, credit=None):
        cgl = CampaignGoalLedgerModel()
        cgl.campaign_goal = campaign_goal
        cgl.campaign = campaign_goal.campaign
        cgl.party_type = transferrer.__class__.__name__.lower()
        cgl.party_id = transferrer.id
        if debit is not None:
            cgl.debit = debit
            self._transfers['debit'][campaign_goal.name] = cgl
        elif credit is not None:
            cgl.credit = credit
            self._transfers['credit'][campaign_goal.name] = cgl
        else:
            msg = "One of ``debit`` or ``credit`` must be defined!"
            raise TypeError(msg)
