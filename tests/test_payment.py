import os
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4 as uuid

import stripe
from nose.tools import raises, assert_equal, assert_true
from mock import patch, Mock

from pooldlib import config, DIR, payment
from pooldlib.postgresql.models import (Currency as CurrencyModel,
                                        Fee as FeeModel)

from tests import tag
from tests.base import PooldLibPostgresBaseTest


class TestTotalAfterFees(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestTotalAfterFees, self).setUp()

        self.stripe_fee = FeeModel.query.filter_by(name='stripe-transaction').first()
        self.poold_fee = FeeModel.query.filter_by(name='poold-transaction').first()

    @tag('payment')
    def test_single_non_stripe_fee(self):
        charge = Decimal('100.0000')
        # fractional pct = 0.03
        # flat fee = 0.00
        poold_fee = Decimal('3.0000')
        fees = {'poold-transaction': poold_fee}
        total = Decimal('103.0000')

        ret = payment.total_after_fees(charge,
                                       fees=(self.poold_fee, ))
        assert_equal(charge, ret['charge']['initial'])
        assert_equal(total, ret['charge']['final'])
        for fee in ret['fees']:
            assert_equal(fees[fee['name']], fee['fee'])

    @tag('payment')
    def test_single_stripe_fee(self):
        charge = Decimal('100.0000')
        # fractional pct = 0.03
        # flat fee = 0.00
        stripe_fee = Decimal('3.3000')
        fees = {'stripe-transaction': stripe_fee}
        total = Decimal('103.3000')

        ret = payment.total_after_fees(charge,
                                       fees=(self.stripe_fee, ))
        assert_equal(charge, ret['charge']['initial'])
        assert_equal(total, ret['charge']['final'])
        for fee in ret['fees']:
            assert_equal(fees[fee['name']], fee['fee'])

    @tag('payment')
    def test_multiple_with_stripe_fee(self):
        charge = Decimal('100.0000')
        # fractional pct = 0.029
        # flat fee = 0.30
        stripe_fee = Decimal('3.3900')
        # fractional pct = 0.03
        # flat fee = 0.00
        poold_fee = Decimal('3.0000')
        fees = {'poold-transaction': poold_fee,
                'stripe-transaction': stripe_fee}
        total = Decimal('106.3900')

        ret = payment.total_after_fees(charge,
                                       fees=(self.stripe_fee, self.poold_fee))

        assert_equal(charge, ret['charge']['initial'])
        assert_equal(total, ret['charge']['final'])
        for fee in ret['fees']:
            assert_equal(fees[fee['name']], fee['fee'])


class TestTokenExchange(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestTokenExchange, self).setUp()
        self.currency = CurrencyModel.query.filter_by(code='USD').first()
        self.fee = FeeModel.query.get(1)

        n = uuid().hex
        username = 'StripeUser-%s' % n[:16]
        name = 'StripeUser %s' % n[16:]
        email = 'StripeUser-%s@example.com' % n[16:]
        self.user = self.create_user(username, name, email=email)

        try:
            config_path = os.path.join(os.path.dirname(DIR), '.env')
            config.update_with_file(config_path)
        except:
            pass

        self.logger_patcher = patch('pooldlib.payment.logger')
        self.patched_logger = self.logger_patcher.start()
        self.addCleanup(self.logger_patcher.stop)

    @tag('external', 'stripe')
    def test_token_exchange(self):
        # This is a functional test which depends on the stripe api.
        # To run all stripe api related tests run: $ make tests-stripe
        # To run all tests which utilize external services run: $ make
        # NOTE :: this test depends on the following environment variables
        # NOTE :: being defined: TEST_CARD_VISA_NUMBER, TEST_CARD_VISA_CVC, STRIPE_SECRET_KEY

        exp = datetime.now() + timedelta(days=365)
        # Get a token from stripe for tests
        card = dict(number=config.TEST_CARD_VISA_NUMBER,
                    cvc=config.TEST_CARD_VISA_CVC,
                    exp_month=exp.month,
                    exp_year=exp.year)
        token = stripe.Token.create(api_key=config.STRIPE_SECRET_KEY, card=card)

        stripe_customer = payment.StripeCustomer(config.STRIPE_SECRET_KEY)
        stripe_user_id = stripe_customer.token_for_customer(token.id, self.user)
        # We don't know what the token will be, but we know it should be a
        # string, and start with 'cus_'
        assert_true(isinstance(stripe_user_id, basestring))
        assert_true(stripe_user_id.startswith('cus_'))

    @tag('payment')
    @patch('pooldlib.payment._Customer', spec=stripe.Customer)
    def test_customer_create_call(self, mock_customer_module):
        mock_customer = Mock()
        mock_customer.id = 'cus_%s' % uuid().hex
        mock_customer_module.create.return_value = mock_customer

        token = uuid().hex

        stripe_customer = payment.StripeCustomer(None)
        stripe_user_id = stripe_customer.token_for_customer(token, self.user)

        exp_kwargs = dict(description='Poold user: %s' % self.user.id,
                          card=token,
                          email=self.user.email)
        mock_customer_module.create.assert_called_once_with(api_key=None, **exp_kwargs)
        assert_equal(mock_customer.id, stripe_user_id)
        self.patched_logger.transaction.assert_called_once_with('New Stripe Customer Created',
                                                                **exp_kwargs)

    @tag('payment')
    @raises(stripe.AuthenticationError)
    @patch('pooldlib.payment._Customer', spec=stripe.Customer)
    def test_authentication_error(self, mock_customer):
        msg = 'Test message'

        def exception(*args, **kwargs):
            raise stripe.AuthenticationError(msg)
        mock_customer.create.side_effect = exception

        token = uuid().hex
        kwargs = dict(card=token,
                      description='Poold user: %s' % self.user.id,
                      email=self.user.email)
        meta = dict(user=str(self.user), request_args=kwargs)
        data = dict(error=stripe.AuthenticationError.__name__,
                    message=msg)
        stripe_customer = payment.StripeCustomer(None)
        try:
            stripe_customer.token_for_customer(token, self.user)
        except:
            msg = 'Stripe Authentication Error.'
            self.patched_logger.error.assert_called_once_with(msg, data=data, **meta)
            raise

    @tag('payment')
    @raises(stripe.InvalidRequestError)
    @patch('pooldlib.payment._Customer', spec=stripe.Customer)
    def test_invalid_request_error(self, mock_customer):
        msg = 'Test message'

        def exception(*args, **kwargs):
            raise stripe.InvalidRequestError(msg, None)
        mock_customer.create.side_effect = exception

        token = uuid().hex
        kwargs = dict(card=token,
                      description='Poold user: %s' % self.user.id,
                      email=self.user.email)
        meta = dict(user=str(self.user), request_args=kwargs)
        data = dict(error=stripe.InvalidRequestError.__name__,
                    message=msg)
        stripe_customer = payment.StripeCustomer(None)
        try:
            stripe_customer.token_for_customer(token, self.user)
        except:
            msg = 'Stripe Invalid Request Error.'
            self.patched_logger.error.assert_called_once_with(msg, data=data, **meta)
            raise

    @tag('payment')
    @raises(stripe.APIConnectionError)
    @patch('pooldlib.payment._Customer', spec=stripe.Customer)
    def test_api_connection_error(self, mock_customer):
        msg = 'Test message'

        def exception(*args, **kwargs):
            raise stripe.APIConnectionError(msg)
        mock_customer.create.side_effect = exception

        token = uuid().hex
        kwargs = dict(card=token,
                      description='Poold user: %s' % self.user.id,
                      email=self.user.email)
        meta = dict(user=str(self.user), request_args=kwargs)
        data = dict(error=stripe.APIConnectionError.__name__,
                    message=msg)
        stripe_customer = payment.StripeCustomer(None)
        try:
            stripe_customer.token_for_customer(token, self.user)
        except:
            msg = 'There was an error connecting to the Stripe API.'
            self.patched_logger.error.assert_called_once_with(msg, data=data, **meta)
            raise

    @tag('payment')
    @raises(stripe.APIError)
    @patch('pooldlib.payment._Customer', spec=stripe.Customer)
    def test_api_error(self, mock_customer):
        msg = 'Test message'

        def exception(*args, **kwargs):
            raise stripe.APIError(msg)
        mock_customer.create.side_effect = exception

        token = uuid().hex
        kwargs = dict(card=token,
                      description='Poold user: %s' % self.user.id,
                      email=self.user.email)
        meta = dict(user=str(self.user), request_args=kwargs)
        data = dict(error=stripe.APIError.__name__,
                    message=msg)
        stripe_customer = payment.StripeCustomer(None)
        try:
            stripe_customer.token_for_customer(token, self.user)
        except:
            msg = 'An unknown error occurred while interacting with the Stripe API.'
            self.patched_logger.error.assert_called_once_with(msg, data=data, **meta)
            raise
