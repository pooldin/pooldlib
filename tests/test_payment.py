import os
from datetime import datetime, timedelta
from uuid import uuid4 as uuid

import stripe
from nose.tools import raises, assert_equal, assert_true
from mock import patch, Mock

from pooldlib import payment
from pooldlib import Config, DIR
from pooldlib.postgresql.models import (Currency as CurrencyModel,
                                        Fee as FeeModel)

from tests import tag
from tests.base import PooldLibPostgresBaseTest


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
        self.user_balance = self.create_balance(user=self.user, currency_code='USD')

        config_path = os.path.join(DIR, '.env')
        self.config = Config.from_file(config_path)
        payment.configure(self.config)

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

        exp = datetime.now() + timedelta(days=265)
        # Get a token from stripe for tests
        card = dict(number=self.config.TEST_CARD_VISA_NUMBER,
                    cvc=self.config.TEST_CARD_VISA_CVC,
                    exp_month=exp.month,
                    exp_year=exp.year)
        token = stripe.Token.create(card=card)

        stripe_user_id = payment.exchange_stripe_token_for_user(token.id, self.user)
        # We don't know what the token will be, but we know it should be a
        # string, and start with 'cus_'
        assert_true(isinstance(stripe_user_id, basestring))
        assert_true(stripe_user_id.startswith('cus_'))

    @patch('pooldlib.payment.Customer', spec=stripe.Customer)
    def test_stripe_create_call(self, mock_customer_module):
        mock_customer = Mock()
        mock_customer.id = 'cus_%s' % uuid().hex
        mock_customer_module.create.return_value = mock_customer

        token = uuid().hex

        stripe_user_id = payment.exchange_stripe_token_for_user(token, self.user)

        exp_kwargs = dict(description='Poold user: %s' % self.user.id,
                          card=token,
                          email=self.user.email)
        mock_customer_module.create.assert_called_once_with(**exp_kwargs)
        assert_equal(mock_customer.id, stripe_user_id)
        self.patched_logger.transaction.assert_called_once_with('New Stripe User Created',
                                                                **exp_kwargs)

    @raises(stripe.AuthenticationError)
    @patch('pooldlib.payment.Customer', spec=stripe.Customer)
    def test_authentication_error(self, mock_customer):
        msg = 'Test message'

        def exception(*args, **kwargs):
            raise stripe.AuthenticationError(msg)
        mock_customer.create.side_effect = exception

        token = uuid().hex
        try:
            payment.exchange_stripe_token_for_user(token, self.user)
        except:
            msg = 'Stripe Authentication Error: %s' % msg
            self.patched_logger.error.assert_called_once_with(msg)
            raise

    @raises(stripe.InvalidRequestError)
    @patch('pooldlib.payment.Customer', spec=stripe.Customer)
    def test_invalid_request_error(self, mock_customer):
        msg = 'Test message'

        def exception(*args, **kwargs):
            raise stripe.InvalidRequestError(msg, None)
        mock_customer.create.side_effect = exception

        token = uuid().hex
        try:
            payment.exchange_stripe_token_for_user(token, self.user)
        except:
            msg = 'Stripe Invalid Request Error: %s' % msg
            self.patched_logger.error.assert_called_once_with(msg)
            raise

    @raises(stripe.APIConnectionError)
    @patch('pooldlib.payment.Customer', spec=stripe.Customer)
    def test_api_connection_error(self, mock_customer):
        msg = 'Test message'

        def exception(*args, **kwargs):
            raise stripe.APIConnectionError(msg)
        mock_customer.create.side_effect = exception

        token = uuid().hex
        try:
            payment.exchange_stripe_token_for_user(token, self.user)
        except:
            msg = 'There was an error connecting to the Stripe API: %s' % msg
            self.patched_logger.error.assert_called_once_with(msg)
            raise

    @raises(stripe.APIError)
    @patch('pooldlib.payment.Customer', spec=stripe.Customer)
    def test_api_error_error(self, mock_customer):
        msg = 'Test message'

        def exception(*args, **kwargs):
            raise stripe.APIError(msg)
        mock_customer.create.side_effect = exception

        token = uuid().hex
        try:
            payment.exchange_stripe_token_for_user(token, self.user)
        except:
            msg = 'An unknown error occurred while interacting with the Stripe API: %s' % msg
            self.patched_logger.error.assert_called_once_with(msg)
            raise
