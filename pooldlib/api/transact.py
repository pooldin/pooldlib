from uuid import uuid4 as uuid
from decimal import Decimal
from collections import defaultdict

from pooldlib.postgresql import db
from pooldlib.postgresql import Transaction, Transfer, ExternalLedger, InternalLedger, Fee
from pooldlib.exceptions import InsufficentFundsTransferError


class Transact(object):

    def __init__(self):
        self.id = uuid()
        self.reset()

    def transfer(self, amount, creditor=None, debtor=None, currency=None, fee=None):

        if currency is None:
            currency = 'USD'

        if fee is not None:
            if isinstance(fee, int):
                fee = Fee.query.get(fee)
            if isinstance(fee, basestring):
                fee = Fee.query.filter_by(name=fee).first()

        credit_balance = creditor.balance_for_currency(currency=currency)
        party = None
        if fee:
            party = getattr(creditor, 'username', None) or creditor.name
        self._transfer_credit(credit_balance, amount, fee=fee, party=party)

        party = None
        if fee:
            party = getattr(debtor, 'username', None) or debtor.name
        debit_balance = debtor.balance_for_currency(currency=currency)
        self._transfer_debit(debit_balance, amount, fee=fee, party=party)

    def external(self, party, creditor=None, debtor=None, credit=None, debit=None):
        pass

    def verify(self):
        return len(self._errors) == 0

    def execute(self):
        if self._errors:
            exc, msg = self._errors.pop()
            self.reset()
            raise exc(msg)

        for xfer_class_values in self._transfers.values():
            for xfer in xfer_class_values.values():
                db.session.add(xfer)
        db.session.flush()

        db.session.commit()

    def _transfer_credit(self, balance, amount, fee=None, party=None):
        t = self._transfers['credit'][balance.id] or self._new_transfer(balance)
        t.credit = t.credit or Decimal('0.0000')
        t.credit += amount
        balance.amount += amount

        if fee:
            il = self._new_internal_ledger(party, balance.currency, fee, credit=amount)
            self._internal_ledger_items.append(il)

        self._transfers['credit'][balance.id] = t

    def _transfer_debit(self, balance, amount, fee=None, party=None):
        t = self._transfers['debit'][balance.id] or self._new_transfer(balance)
        t.debit = t.debit or Decimal('0.0000')
        t.debit += amount
        balance.amount -= amount

        if fee:
            il = self._new_internal_ledger(party, balance.currency, fee, debit=amount)
            self._internal_ledger_items.append(il)

        if balance.amount < Decimal('0.0000'):
            msg = 'Transfer of %s failed, balance %s has insufficient funds.' % (amount, balance)
            self._errors.append((InsufficentFundsTransferError, msg))

        self._transfers['debit'][balance.id] = t

    def _new_transfer(self, balance):
        t = Transfer()
        t.balance = balance
        t.group_id = self.id
        return t

    def _new_internal_ledger(self, party, currency, fee, debit=None, credit=None):
        il = InternalLedger()
        il.record_id = self.id
        il.record_table = 'transfer'
        il.party = party
        il.currency = currency
        il.fee = fee

        if credit is not None:
            il.credit = credit
        elif debit is not None:
            il.debit = debit
        return il

    def reset(self):
        self._transfers = defaultdict(lambda: defaultdict(int))
        self._external_ledger_items = list()
        self._internal_ledger_items = list()
        self._errors = list()
