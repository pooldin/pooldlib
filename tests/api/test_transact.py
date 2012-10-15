from decimal import Decimal

from nose.tools import raises, assert_equal, assert_true

from pooldlib.postgresql import Transfer, InternalLedger
from pooldlib.api import TransactAPI
from pooldlib.exceptions import InsufficentFundsTransferError

from tests.base import PooldLibPostgresBaseTest


class TestUserCampaignTransfer(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestUserCampaignTransfer, self).setUp()

        self.user_a = self.create_user('user_a', 'A. User')
        self.user_a_balance = self.create_balance(user=self.user_a, currency_code='USD')
        self.user_b = self.create_user('poold.in', 'Poold.in')
        self.user_b_balance = self.create_balance(user=self.user_b, currency_code='USD')

        self.community_a = self.create_user('community_a', 'It\'s campaign_a!')
        self.community_a_balance = self.create_balance(community=self.community_a, currency_code='USD')
        self.community_b = self.create_user('campaign_b', 'It\'s campaign_b!')
        self.community_b_balance = self.create_balance(community=self.community_b, currency_code='USD')

    def test_basic_transfer(self):
        t = TransactAPI()
        t.transfer(Decimal('25.0000'), to_user=self.community_a, from_user=self.user_a)
        assert_true(t.verify())

        t.execute()

        xfers = Transfer.query.filter_by(group_id=t.id).all()
        assert_equal(2, len(xfers))

        debit_xfer = [x for x in xfers if x.balance == self.user_a.balance_for_currency('USD')]
        assert_equal(1, len(debit_xfer))
        assert_equal(Decimal('25.0000'), debit_xfer[0].debit)

        credit_xfer = [x for x in xfers if x.balance == self.community_a.balance_for_currency('USD')]
        assert_equal(1, len(credit_xfer))
        assert_equal(Decimal('25.0000'), credit_xfer[0].credit)

    @raises(InsufficentFundsTransferError)
    def test_insufficient_funds_transfer(self):
        t = TransactAPI()
        t.transfer(Decimal('55.0000'), to_user=self.community_a, from_user=self.user_a)

        t.execute()

    def test_transfer_with_fee(self):
        t = TransactAPI()
        t.transfer(Decimal('25.0000'), to_user=self.community_a, from_user=self.user_a)
        t.transfer(Decimal('5.0000'), to_user=self.user_b, from_user=self.user_a, fee=1)

        assert_true(t.verify())

        t.execute()

        xfers = Transfer.query.filter_by(group_id=t.id).all()
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

        iledgers = InternalLedger.query.filter_by(record_id=t.id).all()
        assert_equal(2, len(iledgers))

        credit_iledger = [l for l in iledgers if l.party == self.user_b.username]
        assert_equal(1, len(credit_iledger))
        assert_equal(Decimal('5.0000'), credit_iledger[0].credit)
        assert_equal(None, credit_iledger[0].debit)

        debit_iledger = [l for l in iledgers if l.party == self.user_a.username]
        assert_equal(1, len(debit_iledger))
        assert_equal(Decimal('5.0000'), debit_iledger[0].debit)
        assert_equal(None, debit_iledger[0].credit)
