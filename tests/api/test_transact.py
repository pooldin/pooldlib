from uuid import uuid4 as uuid
from decimal import Decimal

from nose.tools import raises, assert_equal, assert_true
from nose import SkipTest

from pooldlib.postgresql import (Transfer as TransferModel,
                                 Transaction as TransactionModel,
                                 InternalLedger as InternalLedgerModel,
                                 ExternalLedger as ExternalLedgerModel,
                                 CommunityGoalLedger as CommunityGoalLedgerModel,
                                 Currency as CurrencyModel,
                                 Fee as FeeModel)
from pooldlib import Transact
from pooldlib.exceptions import (InsufficentFundsTransferError,
                                 InsufficentFundsTransactionError)

from tests import tag
from tests.base import PooldLibPostgresBaseTest


# TODO :: Transaction related tests need to be fixed!


class TestUserCommunityGoalTransfer(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestUserCommunityGoalTransfer, self).setUp()
        self.currency = CurrencyModel.query.filter_by(code='USD').first()
        self.currency = CurrencyModel.query.filter_by(code='USD').first()
        self.fee = FeeModel.query.get(1)

        n = uuid().hex
        self.user_a = self.create_user(n, '%s %s' % (n[:16], n[16:]))
        self.user_a_balance = self.create_balance(user=self.user_a, currency_code='USD')

        self.community = self.create_community(uuid().hex, uuid().hex)
        self.community_balance = self.create_balance(community=self.community, currency_code='USD')

        self.community_goal = self.create_community_goal(self.community, uuid().hex, uuid().hex)

    @tag('transact')
    def test_simple_transfer_to(self):
        t = Transact()
        t.transfer_to_community_goal(Decimal('25.0000'),
                                     self.currency,
                                     self.community_goal,
                                     self.user_a)
        assert_true(t.verify())
        t.execute()

        xfers = TransferModel.query.filter_by(record_id=t.id).all()

        check_balance = self.user_a.balance_for_currency(self.currency)
        debit_xfer = [x for x in xfers if x.balance == check_balance]
        assert_equal(1, len(debit_xfer))
        assert_equal(Decimal('25.0000'), check_balance.amount)
        assert_equal(Decimal('25.0000'), debit_xfer[0].debit)
        assert_equal(None, debit_xfer[0].credit)

        check_balance = self.community.balance_for_currency(self.currency)
        credit_xfer = [x for x in xfers if x.balance == check_balance]
        assert_equal(1, len(credit_xfer))
        assert_equal(Decimal('75.0000'), check_balance.amount)
        assert_equal(Decimal('25.0000'), credit_xfer[0].credit)
        assert_equal(None, credit_xfer[0].debit)

        comm_ledger = CommunityGoalLedgerModel.query.filter_by(community_goal=self.community_goal).all()
        assert_equal(1, len(comm_ledger))
        comm_ledger = comm_ledger[0]
        assert_equal(Decimal('25.0000'), comm_ledger.credit)
        assert_equal(None, comm_ledger.debit)
        assert_equal(self.community.id, comm_ledger.community_id)
        assert_equal(self.community_goal.id, comm_ledger.community_goal_id)
        assert_equal(self.user_a.id, comm_ledger.party_id)
        assert_equal('user', comm_ledger.party_type)

    @tag('transact')
    def test_simple_transfer_from(self):
        t = Transact()
        t.transfer_from_community_goal(Decimal('25.0000'),
                                       self.currency,
                                       self.community_goal,
                                       self.user_a)
        assert_true(t.verify())
        t.execute()

        xfers = TransferModel.query.filter_by(record_id=t.id).all()

        check_balance = self.user_a.balance_for_currency(self.currency)
        debit_xfer = [x for x in xfers if x.balance == check_balance]
        assert_equal(1, len(debit_xfer))
        assert_equal(Decimal('75.0000'), check_balance.amount)
        assert_equal(Decimal('25.0000'), debit_xfer[0].credit)
        assert_equal(None, debit_xfer[0].debit)

        check_balance = self.community.balance_for_currency(self.currency)
        credit_xfer = [x for x in xfers if x.balance == check_balance]
        assert_equal(1, len(credit_xfer))
        assert_equal(Decimal('25.0000'), check_balance.amount)
        assert_equal(Decimal('25.0000'), credit_xfer[0].debit)
        assert_equal(None, credit_xfer[0].credit)

        comm_ledger = CommunityGoalLedgerModel.query.filter_by(community_goal=self.community_goal).all()
        assert_equal(1, len(comm_ledger))
        comm_ledger = comm_ledger[0]
        assert_equal(Decimal('25.0000'), comm_ledger.debit)
        assert_equal(None, comm_ledger.credit)
        assert_equal(self.community.id, comm_ledger.community_id)
        assert_equal(self.community_goal.id, comm_ledger.community_goal_id)
        assert_equal(self.user_a.id, comm_ledger.party_id)
        assert_equal('user', comm_ledger.party_type)


class TestUserCommunityTransfer(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestUserCommunityTransfer, self).setUp()
        self.currency = CurrencyModel.query.filter_by(code='USD').first()
        self.fee = FeeModel.query.get(1)

        n = uuid().hex
        self.user_a = self.create_user(n, '%s %s' % (n[:16], n[16:]))
        self.user_a_balance = self.create_balance(user=self.user_a, currency_code='USD')

        n = uuid().hex
        self.user_b = self.create_user(n, '%s %s' % (n[:16], n[16:]))
        self.user_b_balance = self.create_balance(user=self.user_b, currency_code='USD')

        self.community_a = self.create_community(uuid().hex, uuid().hex)
        self.community_a_balance = self.create_balance(community=self.community_a, currency_code='USD')

    @tag('transact')
    def test_basic_transfer(self):
        t = Transact()
        t.transfer(Decimal('25.0000'), self.currency, destination=self.community_a, origin=self.user_a)
        assert_true(t.verify())

        t.execute()

        xfers = TransferModel.query.filter_by(record_id=t.id).all()
        assert_equal(2, len(xfers))

        debit_xfer = [x for x in xfers if x.balance == self.user_a.balance_for_currency(self.currency)]
        assert_equal(1, len(debit_xfer))
        assert_equal(Decimal('25.0000'), debit_xfer[0].debit)

        credit_xfer = [x for x in xfers if x.balance == self.community_a.balance_for_currency(self.currency)]
        assert_equal(1, len(credit_xfer))
        assert_equal(Decimal('25.0000'), credit_xfer[0].credit)

    @tag('transact')
    @raises(InsufficentFundsTransferError)
    def test_insufficient_funds_transfer(self):
        t = Transact()
        t.transfer(Decimal('55.0000'), self.currency, destination=self.community_a, origin=self.user_a)

        t.execute()

    @tag('transact')
    def test_transfer_with_fee(self):
        t = Transact()
        t.transfer(Decimal('25.0000'), self.currency, destination=self.community_a, origin=self.user_a)
        t.transfer(Decimal('5.0000'), self.currency, destination=self.user_b, origin=self.user_a, fee=self.fee)

        assert_true(t.verify())

        t.execute()

        xfers = TransferModel.query.filter_by(record_id=t.id).all()
        assert_equal(3, len(xfers))

        check_balance = self.user_a.balance_for_currency(self.currency)
        debit_xfer = [x for x in xfers if x.balance == check_balance]
        assert_equal(1, len(debit_xfer))
        assert_equal(Decimal('20.0000'), check_balance.amount)
        assert_equal(Decimal('30.0000'), debit_xfer[0].debit)
        assert_equal(None, debit_xfer[0].credit)

        check_balance = self.community_a.balance_for_currency(self.currency)
        credit_xfer = [x for x in xfers if x.balance == check_balance]
        assert_equal(1, len(credit_xfer))
        assert_equal(Decimal('75.0000'), check_balance.amount)
        assert_equal(Decimal('25.0000'), credit_xfer[0].credit)
        assert_equal(None, credit_xfer[0].debit)

        check_balance = self.user_b.balance_for_currency(self.currency)
        debit_xfer = [x for x in xfers if x.balance == check_balance]
        assert_equal(1, len(debit_xfer))
        assert_equal(Decimal('55.0000'), check_balance.amount)
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
        self.currency = CurrencyModel.query.filter_by(code='USD').first()
        self.fee = FeeModel.query.get(1)

        n = uuid().hex
        self.user_a = self.create_user(n, '%s %s' % (n[:16], n[16:]))
        self.user_a_balance = self.create_balance(user=self.user_a, currency_code='USD')

        self.community_a = self.create_community(uuid().hex, uuid().hex)
        self.community_a_balance = self.create_balance(community=self.community_a, currency_code='USD')

    @tag('transact')
    def test_basic_transaction(self):
        t = Transact()
        t.transaction(self.user_a,
                      'test-party',
                      'test-reference-number-test_basic_transaction',
                      self.currency,
                      credit=Decimal('25.0000'))
        t.external_ledger(self.user_a,
                          'test-party',
                          'test-reference-number-test_basic_transaction',
                          self.currency,
                          credit=Decimal('25.0000'))
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
        assert_equal('test-party', ldgr.processor)

        assert_equal(Decimal('75.0000'), self.user_a_balance.amount)

    @tag('transact')
    @raises(InsufficentFundsTransactionError)
    def test_insufficient_funds_transaction(self):
        t = Transact()
        t.transaction(self.user_a,
                      'test-party',
                      'test-reference-number-test_test_insufficient_funds_transaction',
                      self.currency,
                      debit=Decimal('55.0000'))
        t.execute()

    @tag('transact')
    def test_transfer_with_fee(self):
        raise SkipTest()
        t = Transact()
        t.transaction(self.user_a,
                      'test-party',
                      'test-reference-number-test_transfer_with_fee',
                      self.currency,
                      debit=Decimal('25.0000'))
        t.external_ledger(self.user_a,
                          'test-party',
                          'test-reference-number-test_transfer_with_fee',
                          self.currency,
                          debit=Decimal('5.0000'),
                          fee=self.fee)
        t.transaction(self.user_a,
                      'test-party',
                      'test-reference-number-test_transfer_with_fee',
                      self.currency,
                      debit=Decimal('5.0000'),
                      fee=self.fee)
        t.external_ledger(self.user_a,
                          'test-party',
                          'test-reference-number-test_transfer_with_fee',
                          self.currency,
                          debit=Decimal('5.0000'),
                          fee=self.fee)
        t.transaction(self.user_a,
                      'poold',
                      'test-reference-number-test_transfer_with_fee',
                      self.currency,
                      debit=Decimal('5.0000'),
                      fee=self.fee)
        t.external_ledger(self.user_a,
                          'poold',
                          'test-reference-number-test_transfer_with_fee',
                          self.currency,
                          debit=Decimal('5.0000'),
                          fee=self.fee)

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
