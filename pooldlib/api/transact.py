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
                                 Fee as FeeModel)
from pooldlib.exceptions import (InsufficentFundsTransferError,
                                 InsufficentFundsTransactionError)


class Transact(object):
    """``pooldlib`` API for working with user/user, user/community, etc transfers and
    (external) transactions. A user depositing funds in their poold account via stripe
    would be an example (external) transaction.

    Example transfer usage:

        >>> t = Transact()
        >>> t.transfer(Decimal('25.0000'), destination=a_community, origin=a_user)
        >>> if not t.verify(): raise TransactionError()
        >>> t.execute()
        >>> # (USD) Balance of a_user is decreased by $25.000
        >>> # (USD) Balance of a_community is increased by $25.000

    Example transaction usage:

        >>> t = Transact()
        >>> t.transaction(a_user, 'stripe', 'stripe-reference-number', credit=Decimal('50.0000'), currency='USD')
        >>> t.transaction(a_user, 'stripe', 'stripe-reference-number', debit=Decimal('5.0000'), currency='USD', fee=1)
        >>> t.transaction(a_user, 'poold', 'stripe-reference-number', debit=Decimal('5.0000'), currency='USD', fee=1)
        >>> if not t.verify(): raise TransactionError()
        >>> t.execute()
        >>> # (USD) Balance of a_user is increased by $40.000
    """

    def __init__(self):
        self.reset()

    def transfer(self, amount, destination=None, origin=None, currency=None, fee=None):
        """Add a (balance) **transfer** execution to the `Transact` list.
        Valid transfers are:
            - :class:`pooldlib.postgresql.models.User` to :class:`pooldlib.postgresql.models.User`
            - :class:`pooldlib.postgresql.models.User` to :class:`pooldlib.postgresql.models.Community`
            - :class:`pooldlib.postgresql.models.Community` to :class:`pooldlib.postgresql.models.User`

        :param amount: Amount of currency to be transferred.
        :type amount: decimal.Decimal
        :param origin: Instance of balance holding model which is receiving in the transfer.
        :type origin: :class:`pooldlib.postgresql.models.User` or
                  :class:`pooldlib.postgresql.models.Community`
        :param origin: Instance of balance holding model which is sending in the transfer.
        :type origin: :class:`pooldlib.postgresql.models.User` or
                       :class:`pooldlib.postgresql.models.Community`
        :param currency: Currency type for which to execute the transfer.
        :type currency: :class:`pooldlib.postgresql.models.Currency` or string.
        :param fee: Fee associated with the transfer.
        :type fee: :class:`pooldlib.postgresql.models.Fee`, string name of Fee or integer id of Fee.
        """
        if currency is None:
            currency = 'USD'

        if fee is not None:
            if isinstance(fee, int):
                fee = FeeModel.query.get(fee)
            if isinstance(fee, basestring):
                fee = FeeModel.query.filter_by(name=fee).first()

        credit_balance = destination.balance_for_currency(currency, for_update=True)
        party = None
        if fee:
            party = getattr(destination, 'username', None) or destination.name
        self._transfer_credit(credit_balance, amount, fee=fee, party=party)

        party = None
        if fee:
            party = getattr(origin, 'username', None) or origin.name
        debit_balance = origin.balance_for_currency(currency, for_update=True)
        self._transfer_debit(debit_balance, amount, fee=fee, party=party)

    def transaction(self, balance_holder, external_party, external_reference, debit=None, credit=None, currency=None, fee=None):
        """Add an external **transaction** to the `Transact` list.
        One of either ``debit`` or ``credit`` **must** be defined.

        :param balance_holder: Instance of the balance holding model which
                               is involved in the transaction.
        :type balance_holder: :class:`pooldlib.postgresql.models.User` or
                              :class:`pooldlib.postgresql.models.Community`
        :param external_party: The third party facilitating the transaction (i.e. stripe, etc).
        :type external_party: string
        :param external_reference: Identifier provided by third party referencing transaction.
        :type external_reference: string.
        :param debit: The amount to be debited from the target balance.
        :type debit: decimal.Decimal or `None`.
        :param credit: The amount to be credited to the target balance.
        :type credit: decimal.Decimal or `None`.
        :param currency: Currency type for which to execute the transfer.
        :type currency: :class:`pooldlib.postgresql.models.Currency`, string or `None`
                        (defaults to USD).
        :param fee: Fee associated with the transfer.
        :type fee: :class:`pooldlib.postgresql.models.Fee`, string name of Fee or integer id of Fee.
        """
        if currency is None:
            currency = 'USD'

        if fee is not None:
            if isinstance(fee, int):
                fee = FeeModel.query.get(fee)
            if isinstance(fee, basestring):
                fee = FeeModel.query.filter_by(name=fee).first()

        txn_balance = balance_holder.balance_for_currency(currency, for_update=True)
        if credit is not None:
            self._transaction_credit(txn_balance, credit, fee=fee, party=external_party, reference=external_reference)
        elif debit is not None:
            self._transaction_debit(txn_balance, debit, fee=fee, party=external_party, reference=external_reference)

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

    def _transfer_credit(self, balance, amount, fee=None, party=None):
        t = self._transfers['credit'][balance.id] or self._new_transfer(balance)
        t.credit = t.credit or Decimal('0.0000')
        t.credit += amount
        balance.amount += amount

        if fee:
            il = self._new_internal_ledger(party,
                                           balance.currency,
                                           'transfer',
                                           fee,
                                           credit=amount)
            self._internal_ledger_items.append(il)

        self._transfers['credit'][balance.id] = t

    def _transfer_debit(self, balance, amount, fee=None, party=None):
        t = self._transfers['debit'][balance.id] or self._new_transfer(balance)
        t.debit = t.debit or Decimal('0.0000')
        t.debit += amount
        balance.amount -= amount

        if fee:
            il = self._new_internal_ledger(party,
                                           balance.currency,
                                           'transfer',
                                           fee,
                                           debit=amount)
            self._internal_ledger_items.append(il)

        if balance.amount < Decimal('0.0000'):
            msg = 'Transfer of %s failed, balance %s has insufficient funds.' % (amount, balance)
            self._errors.append((InsufficentFundsTransferError, msg))

        self._transfers['debit'][balance.id] = t

    def _transaction_credit(self, balance, amount, fee=None, party=None, reference=None):
        t = self._transactions['credit'][balance.id] or self._new_transaction(balance)
        t.credit = t.credit or Decimal('0.0000')
        t.credit += amount
        balance.amount += amount

        el = self._new_external_ledger(party,
                                       balance.currency,
                                       'transaction',
                                       reference,
                                       fee,
                                       credit=amount)
        self._external_ledger_items.append(el)

        self._transactions['credit'][balance.id] = t

    def _transaction_debit(self, balance, amount, fee=None, party=None, reference=None):
        t = self._transactions['debit'][balance.id] or self._new_transaction(balance)
        t.debit = t.debit or Decimal('0.0000')
        t.debit += amount
        balance.amount -= amount

        el = self._new_external_ledger(party,
                                       balance.currency,
                                       'transaction',
                                       reference,
                                       fee,
                                       debit=amount)
        self._external_ledger_items.append(el)

        if balance.amount < Decimal('0.0000'):
            msg = 'Transaction of %s failed, balance %s has insufficient funds.' % (amount, balance)
            self._errors.append((InsufficentFundsTransactionError, msg))

        self._transactions['debit'][balance.id] = t

    def _new_transfer(self, balance):
        t = TransferModel()
        t.balance = balance
        t.group_id = self.id
        return t

    def _new_transaction(self, balance):
        t = TransactionModel()
        t.balance = balance
        return t

    def _new_internal_ledger(self, party, currency, record_table, fee, debit=None, credit=None):
        il = InternalLedgerModel()
        il.record_id = self.id
        il.record_table = record_table
        il.party = party
        il.currency = currency
        il.fee = fee

        if credit is not None:
            il.credit = credit
        elif debit is not None:
            il.debit = debit
        return il

    def _new_external_ledger(self, party, currency, record_table, reference, fee, debit=None, credit=None):
        el = ExternalLedgerModel()
        el.record_id = self.id
        el.record_table = record_table
        el.external_reference_number = reference
        el.party = party
        el.currency = currency
        el.fee = fee

        if credit is not None:
            el.credit = credit
        elif debit is not None:
            el.debit = debit
        return el
