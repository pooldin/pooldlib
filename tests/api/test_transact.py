from uuid import uuid4 as uuid
from decimal import Decimal

from nose.tools import raises, assert_equal, assert_true

from pooldlib.postgresql import (Transfer as TransferModel,
                                 Transaction as TransactionModel,
                                 InternalLedger as InternalLedgerModel,
                                 ExternalLedger as ExternalLedgerModel)
from pooldlib.api import Transact
from pooldlib.exceptions import (InsufficentFundsTransferError,
                                 InsufficentFundsTransactionError)

from tests.base import PooldLibPostgresBaseTest


class TestUserCampaignTransfer(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestUserCampaignTransfer, self).setUp()

        n = uuid().hex
        self.user_a = self.create_user(n, '%s %s' % (n[:16], n[16:]))
        self.user_a_balance = self.create_balance(user=self.user_a, currency_code='USD')

        n = uuid().hex
        self.user_b = self.create_user(n, '%s %s' % (n[:16], n[16:]))
        self.user_b_balance = self.create_balance(user=self.user_b, currency_code='USD')

        self.community_a = self.create_user(uuid().hex, uuid().hex)
        self.community_a_balance = self.create_balance(community=self.community_a, currency_code='USD')

    def test_basic_transfer(self):
        t = Transact()
        t.transfer(Decimal('25.0000'), destination=self.community_a, origin=self.user_a)
        assert_true(t.verify())

        t.execute()

        xfers = TransferModel.query.filter_by(group_id=t.id).all()
        assert_equal(2, len(xfers))

        debit_xfer = [x for x in xfers if x.balance == self.user_a.balance_for_currency('USD')]
        assert_equal(1, len(debit_xfer))
        assert_equal(Decimal('25.0000'), debit_xfer[0].debit)

        credit_xfer = [x for x in xfers if x.balance == self.community_a.balance_for_currency('USD')]
        assert_equal(1, len(credit_xfer))
        assert_equal(Decimal('25.0000'), credit_xfer[0].credit)

    @raises(InsufficentFundsTransferError)
    def test_insufficient_funds_transfer(self):
        t = Transact()
        t.transfer(Decimal('55.0000'), destination=self.community_a, origin=self.user_a)

        t.execute()

    def test_transfer_with_fee(self):
        t = Transact()
        t.transfer(Decimal('25.0000'), destination=self.community_a, origin=self.user_a)
        t.transfer(Decimal('5.0000'), destination=self.user_b, origin=self.user_a, fee=1)

        assert_true(t.verify())

        t.execute()

        xfers = TransferModel.query.filter_by(group_id=t.id).all()
        assert_equal(3, len(xfers))

        debit_xfer = [x for x in xfers if x.balance == self.user_a.balance_for_currency('USD')]
        assert_equal(1, len(debit_xfer))
        assert_equal(Decimal('30.0000'), debit_xfer[0].debit)
        assert_equal(None, debit_xfer[0].credit)

        credit_xfer = [x for x in xfers if x.balance == self.community_a.balance_for_currency('USD')]
        assert_equal(1, len(credit_xfer))
        assert_equal(Decimal('25.0000'), credit_xfer[0].credit)
        assert_equal(None, credit_xfer[0].debit)

        debit_xfer = [x for x in xfers if x.balance == self.user_b.balance_for_currency('USD')]
        assert_equal(1, len(debit_xfer))
        assert_equal(Decimal('5.0000'), debit_xfer[0].credit)
        assert_equal(None, debit_xfer[0].debit)

        iledgers = InternalLedgerModel.query.filter_by(record_id=t.id).all()
        assert_equal(2, len(iledgers))

        credit_iledger = [l for l in iledgers if l.party == self.user_b.username]
        assert_equal(1, len(credit_iledger))
        assert_equal(Decimal('5.0000'), credit_iledger[0].credit)
        assert_equal(None, credit_iledger[0].debit)

        debit_iledger = [l for l in iledgers if l.party == self.user_a.username]
        assert_equal(1, len(debit_iledger))
        assert_equal(Decimal('5.0000'), debit_iledger[0].debit)
        assert_equal(None, debit_iledger[0].credit)


class TestUserTransaction(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestUserTransaction, self).setUp()

        n = uuid().hex
        self.user_a = self.create_user(n, '%s %s' % (n[:16], n[16:]))
        self.user_a_balance = self.create_balance(user=self.user_a, currency_code='USD')

        self.community_a = self.create_user(uuid().hex, uuid().hex)
        self.community_a_balance = self.create_balance(community=self.community_a, currency_code='USD')

    def test_basic_transaction(self):
        t = Transact()
        t.transaction(self.user_a, 'test-party', 'test-reference-number-test_basic_transaction', credit=Decimal('25.0000'), currency='USD')
        assert_true(t.verify())

        t.execute()

        txn = TransactionModel.query.filter_by(balance_id=self.user_a_balance.id).all()
        assert_equal(1, len(txn))
        txn = txn[0]
        assert_equal(Decimal('25.0000'), txn.credit)
        assert_true(txn.debit is None)

        ldgr = ExternalLedgerModel.query.filter_by(record_id=t.id).all()
        assert_equal(1, len(ldgr))
        ldgr = ldgr[0]
        assert_equal(Decimal('25.0000'), ldgr.credit)
        assert_equal('test-party', ldgr.party)

        assert_equal(Decimal('75.0000'), self.user_a_balance.amount)

    @raises(InsufficentFundsTransactionError)
    def test_insufficient_funds_transaction(self):
        t = Transact()
        t.transaction(self.user_a, 'test-party', 'test-reference-number-test_test_insufficient_funds_transaction', debit=Decimal('55.0000'), currency='USD')
        t.execute()

    def test_transfer_with_fee(self):
        t = Transact()
        t.transaction(self.user_a, 'test-party', 'test-reference-number-test_transfer_with_fee', debit=Decimal('25.0000'), currency='USD')
        t.transaction(self.user_a, 'test-party', 'test-reference-number-test_transfer_with_fee', debit=Decimal('5.0000'), currency='USD', fee=1)
        t.transaction(self.user_a, 'poold', 'test-reference-number-test_transfer_with_fee', debit=Decimal('5.0000'), currency='USD', fee=1)

        assert_true(t.verify())

        t.execute()

        txn = TransactionModel.query.filter_by(balance_id=self.user_a_balance.id).all()
        assert_equal(1, len(txn))
        txn = txn[0]
        assert_equal(Decimal('35.0000'), txn.debit)
        assert_true(txn.credit is None)

        ldgr = ExternalLedgerModel.query.filter_by(record_id=t.id).all()
        assert_equal(3, len(ldgr))

        party_ldgr = [l for l in ldgr if l.party == 'test-party' and l.fee is None]
        assert_equal(1, len(party_ldgr))
        party_ldgr = party_ldgr[0]
        assert_equal(Decimal('25.0000'), party_ldgr.debit)
        assert_equal('test-party', party_ldgr.party)
        assert_true(party_ldgr.credit is None)

        party_fee_ldgr = [l for l in ldgr if l.party == 'test-party' and l.fee is not None]
        assert_equal(1, len(party_fee_ldgr))
        party_fee_ldgr = party_fee_ldgr[0]
        assert_equal(Decimal('5.0000'), party_fee_ldgr.debit)
        assert_equal('test-party', party_fee_ldgr.party)
        assert_true(party_fee_ldgr.credit is None)

        poold_ldgr = [l for l in ldgr if l.party == 'poold']
        assert_equal(1, len(poold_ldgr))
        poold_ldgr = poold_ldgr[0]
        assert_equal(Decimal('5.0000'), poold_ldgr.debit)
        assert_equal('poold', poold_ldgr.party)
        assert_true(poold_ldgr.credit is None)

        assert_equal(Decimal('15.0000'), self.user_a_balance.amount)
