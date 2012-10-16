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
from pooldlib.exceptions import InsufficentFundsTransferError


class Transact(object):
    """``pooldlib`` API for working with user/user, user/community, etc transfers.
    Example usage:

        >>> t = Transact()
        >>> t.transfer(Decimal('25.0000'), destination=a_community, origin=a_user)
        >>> if not t.verify(): raise TransactionError()
        >>> t.execute()
    """

    def __init__(self):
        self.id = uuid()
        self.reset()

    def transfer(self, amount, destination=None, origin=None, currency=None, fee=None):
        """Add a balance transfer to be executed to the
        :class:`pooldlib.api.Transact` list.

        :param amount: Amount of currency to be transferred.
        :type amount: :class:`decimal.Decimal`
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

    def external(self, amount, party, destination=None, origin=None):
        pass

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

    def _new_transfer(self, balance):
        t = TransferModel()
        t.balance = balance
        t.group_id = self.id
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

    def reset(self):
        """Reset the current state of the transact list.
        """
        self._transfers = defaultdict(lambda: defaultdict(int))
        self._external_ledger_items = list()
        self._internal_ledger_items = list()
        self._errors = list()
