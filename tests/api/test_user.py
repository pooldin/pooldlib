import os
from random import randint
from datetime import datetime, timedelta
from uuid import uuid4 as uuid
from decimal import Decimal

from nose.tools import raises, assert_equal, assert_true, assert_false
from mock import Mock, patch

import stripe

from pooldlib import config, DIR
from pooldlib.exceptions import (InvalidPasswordError,
                                 UsernameUnavailableError,
                                 EmailUnavailableError,
                                 PreviousStripeAssociationError,
                                 ExternalAPIUsageError,
                                 ExternalAPIError,
                                 ExternalAPIUnavailableError,
                                 UserCreditCardDeclinedError)
from pooldlib.api import user
from pooldlib.payment import StripeCustomer
from pooldlib.postgresql import db
from pooldlib.postgresql import (User as UserModel,
                                 UserMeta as UserMetaModel,
                                 Fee as FeeModel,
                                 Currency as CurrencyModel,
                                 ExternalLedger as ExternalLedgerModel,
                                 Transaction as TransactionModel,
                                 CampaignGoalLedger as CampaignGoalLedgerModel,
                                 Balance as BalanceModel)
from tests import tag
from tests.base import PooldLibPostgresBaseTest


EXPIRED_FAIL_CARD_NUMBER = 4000000000000069
PROCESSING_ERROR_FAIL_CARD_NUMBER = 4000000000000119

# Example return from stripe.Charge.create()
#{
#  "amount": 10639,
#  "amount_refunded": 0,
#  "card": {
#    "address_city": null,
#    "address_country": null,
#    "address_line1": null,
#    "address_line1_check": null,
#    "address_line2": null,
#    "address_state": null,
#    "address_zip": null,
#    "address_zip_check": null,
#    "country": "US",
#    "cvc_check": null,
#    "exp_month": 11,
#    "exp_year": 2013,
#    "fingerprint": "8pT3CdGS5lSzYJh0",
#    "last4": "4242",
#    "name": null,
#    "object": "card",
#    "type": "Visa"
#  },
#  "created": 1351786736,
#  "currency": "usd",
#  "customer": null,
#  "description": "User: 1, paying towards campaign: 115.",
#  "disputed": false,
#  "failure_message": null,
#  "fee": 639,
#  "fee_details": [
#    {
#      "amount": 339,
#      "application": null,
#      "currency": "usd",
#      "description": "Stripe processing fees",
#      "type": "stripe_fee"
#    },
#    {
#      "amount": 300,
#      "application": "ca_0Wgg7SVq56NlInyDzaxZToyyUQ9CDxIO",
#      "currency": "usd",
#      "description": null,
#      "type": "application_fee"
#    }
#  ],
#  "id": "ch_0ekAtBfTSp7EB0",
#  "invoice": null,
#  "livemode": false,
#  "object": "charge",
#  "paid": true,
#  "refunded": false
#}


class TestGetUser(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetUser, self).setUp()

        self.username_a = uuid().hex.lower()
        self.name_a = '%s %s' % (self.username_a[:16], self.username_a[16:])
        self.email_a = '%s@example.com' % self.username_a
        self.user_a = self.create_user(self.username_a, self.name_a, self.email_a)
        self.user_a_balance = self.create_balance(user=self.user_a, currency_code='USD')

        self.username_b = uuid().hex
        self.name_b = '%s %s' % (self.username_b[:16], self.username_b[16:])
        self.email_b = '%s@example.com' % self.username_b
        self.user_b = self.create_user(self.username_b, self.name_b, self.email_b)
        self.user_b_balance = self.create_balance(user=self.user_b, currency_code='USD')

        self.session = db.session

    @tag('user')
    def test_get_with_username(self):
        u = user.get_by_username(self.username_a)
        assert_equal(self.username_a, u.username)
        assert_equal(self.name_a, u.name)
        assert_equal(self.email_a, u.email)

    @tag('user')
    def test_get_with_email(self):
        u = user.get_by_email(self.email_a)
        assert_equal(self.username_a, u.username)
        assert_equal(self.name_a, u.name)
        assert_equal(self.email_a, u.email)

    @tag('user')
    def test_get_with_email_case_difference(self):
        u = user.get_by_email(self.email_a.upper())
        assert_equal(self.username_a, u.username)
        assert_equal(self.name_a, u.name)
        assert_equal(self.email_a, u.email)

    @tag('user')
    def test_get_non_existant_user(self):
        non_user = user.get_by_username('nonexistant')
        assert_true(non_user is None)

    @tag('user')
    def test_get_disabled_user(self):
        self.user_a.enabled = False
        self.session.commit()
        disabled_user = user.get_by_username(self.username_a)
        assert_true(disabled_user is None)


class TestCreateUser(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCreateUser, self).setUp()
        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)
        self.user_balance = self.create_balance(user=self.user, currency_code='USD')

    @tag('user')
    def test_create_user_returned(self):
        username = uuid().hex
        name = '%s %s' % (username[:16], username[16:])
        email = '%s@example.com' % username
        u = user.create(username, username, name=name, email=email)
        assert_true(isinstance(u, UserModel))

    @tag('user')
    @raises(UsernameUnavailableError)
    def test_create_duplicate_username(self):
        user.create(self.username, self.username, name=self.name)

    @tag('user')
    @raises(EmailUnavailableError)
    def test_create_duplicate_email(self):
        username = uuid().hex
        name = '%s %s' % (username[:16], username[16:])
        email = '%s@example.com' % self.username
        user.create(username, username, name=name, email=email)

    @tag('user')
    def test_create_user_no_name_no_metadata(self):
        username = uuid().hex
        user.create(username, username + '1')
        check_user = UserModel.query.filter_by(username=username).all()
        assert_equal(1, len(check_user))
        check_user = check_user[0]
        assert_equal(username, check_user.username)
        assert_true(check_user.enabled)
        assert_false(check_user.verified)

    @tag('user')
    def test_create_user_no_metadata(self):
        username = uuid().hex
        name = '%s %s' % (username[:16], username[16:])
        user.create(username, username + '1', name=name)

        check_user = UserModel.query.filter_by(username=username).all()
        assert_equal(1, len(check_user))
        check_user = check_user[0]
        assert_equal(username, check_user.username)
        assert_equal(name, check_user.name)
        assert_true(check_user.enabled)
        assert_false(check_user.verified)

    @tag('user')
    def test_create_user_with_metadata(self):
        username = uuid().hex
        name = '%s %s' % (username[:16], username[16:])
        email = '%s@example.com' % username
        test_key = 'There once was a man from florence...'
        user.create(username, username + '1', name=name, email=email, test_key=test_key)

        check_user = UserModel.query.filter_by(username=username).all()
        assert_equal(1, len(check_user))
        check_user = check_user[0]
        assert_equal(username, check_user.username)
        assert_equal(name, check_user.name)
        assert_equal(email, check_user.email)
        assert_equal(test_key, check_user.test_key)
        assert_true(check_user.enabled)
        assert_false(check_user.verified)

    @tag('user')
    @raises(InvalidPasswordError)
    def test_create_with_short_password(self):
        user.create('imauser', 'short1')

    @tag('user')
    @raises(InvalidPasswordError)
    def test_create_with_numberless_password(self):
        user.create('imauser', 'badpassword')


class TestUpdateUser(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestUpdateUser, self).setUp()

        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)
        self.user_balance = self.create_balance(user=self.user, currency_code='USD')
        self.session = db.session

        self.create_user_meta(self.user, meta_key_one='meta value one')

    @tag('user')
    def test_clear_name_attribute(self):
        check_user = UserModel.query.filter_by(username=self.username).first()
        assert_equal(self.name, check_user.name)

        user.update(self.user, name='')
        check_user = UserModel.query.filter_by(username=self.username).first()
        assert_true(check_user.name is None)

    @tag('user')
    @raises(InvalidPasswordError)
    def test_update_with_password_invalid_password(self):
        user.update(self.username, password='thisshouldfail')

    @tag('user')
    def test_update_with_password(self):
        new_password = 'abcde123'
        old_pass_encrypt = self.user.password
        user.update(self.user, password=new_password)

        assert_false(old_pass_encrypt == self.user.password)
        assert_true(self.user.is_password(new_password))

    @tag('user')
    @raises(EmailUnavailableError)
    def test_update_with_existing_email(self):
        username_two = uuid().hex
        name_two = '%s %s' % (username_two[:16], username_two[16:])
        email_two = '%s@example.com' % username_two
        new_user = self.create_user(username_two, name_two, email_two)
        user.update(new_user, email=self.email)

    @tag('user')
    @raises(UsernameUnavailableError)
    def test_update_with_existing_username(self):
        username_two = uuid().hex
        name_two = '%s %s' % (username_two[:16], username_two[16:])
        email_two = '%s@example.com' % username_two
        new_user = self.create_user(username_two, name_two, email_two)
        user.update(new_user, username=self.username)

    @tag('user')
    def test_update_single_field(self):
        newname = uuid().hex
        newname = '%s %s' % (newname[:16], newname[16:])
        assert_true(newname != self.user.name)

        old_mod = self.user.modified
        user.update(self.user, name=newname)

        check_user = UserModel.query.filter_by(username=self.username).first()
        assert_equal(newname, check_user.name)
        assert_true(old_mod < check_user.modified)

    @tag('user')
    def test_update_name_and_username(self):
        id = self.user.id
        newusername = newname = uuid().hex
        newname = '%s %s' % (newname[:16], newname[16:])
        assert_true(newname != self.user.name)
        assert_true(newusername != self.user.username)

        old_mod = self.user.modified
        user.update(self.user, name=newname, username=newusername)

        check_user = UserModel.query.get(id)
        assert_equal(newname, check_user.name)
        assert_equal(newusername, check_user.username)
        assert_true(old_mod < check_user.modified)

    @tag('user')
    def test_update_meta_email(self):
        newemail = '%s@example.com' % uuid().hex
        assert_equal(self.email, self.user.email)
        user.update(self.user, email=newemail)
        assert_equal(newemail, self.user.email)

        check_user_meta = UserMetaModel.query.join(UserModel)\
                                             .filter(UserModel.username == self.username)\
                                             .filter(UserMetaModel.key == 'email')\
                                             .first()
        assert_equal(newemail, check_user_meta.value)

    @tag('user')
    def test_update_add_meta(self):
        newkey = 'testy-mckey'
        newvalue = 'testy-mcvalue'
        kwargs = {newkey: newvalue}
        assert_true(not hasattr(user, newkey))
        user.update(self.user, **kwargs)
        assert_equal(newvalue, getattr(self.user, newkey))

        check_user_meta = UserMetaModel.query.join(UserModel)\
                                             .filter(UserModel.username == self.username)\
                                             .filter(UserMetaModel.key == newkey)\
                                             .first()
        assert_equal(newkey, check_user_meta.key)
        assert_equal(newvalue, check_user_meta.value)

    @tag('user')
    def test_remove_meta(self):
        old_meta_value = self.user.meta_key_one
        test_user = UserModel.query.filter_by(username=self.username).first()
        assert_true(hasattr(test_user, 'meta_key_one'))
        assert_equal(old_meta_value, test_user.meta_key_one)

        user.update(self.user, meta_key_one=None)
        assert_true(not hasattr(test_user, 'meta_key_one'))


class TestResetPassword(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestResetPassword, self).setUp()

        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)
        self.user_balance = self.create_balance(user=self.user, currency_code='USD')
        self.session = db.session

    @tag('user')
    def test_password_reset(self):
        old_pass_encrypt = self.user.password
        new_password = user.reset_password(self.user)

        assert_false(old_pass_encrypt == self.user.password)
        assert_true(self.user.is_password(new_password))


class TestDeactivateUser(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestDeactivateUser, self).setUp()

        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)
        self.user_balance = self.create_balance(user=self.user, currency_code='USD')
        self.session = db.session

    @tag('user')
    def test_disabled_user(self):
        user.disable(self.user)
        assert_true(user.get_by_email(self.email) is None)


class TestVerifyPassword(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestVerifyPassword, self).setUp()

        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)
        self.user_balance = self.create_balance(user=self.user, currency_code='USD')
        self.session = db.session

    @tag('user')
    def test_verify_correct_password(self):
        password = self.user.username + '1'
        assert_true(user.verify_password(self.user, password))

    @tag('user')
    def test_verify_incorrect_password(self):
        password = 'incorrect-password'
        assert_false(user.verify_password(self.user, password))


class TestValidatePassword(PooldLibPostgresBaseTest):

    @tag('user')
    def test_validate_good_password(self):
        assert_true(user.validate_password('1abcdef'))

    @tag('user')
    def test_validate_password_no_number(self):
        assert_false(user.validate_password('abcdefg'))

    @tag('user')
    def test_validate_password_to_short(self):
        assert_false(user.validate_password('defg'))

    @tag('user')
    @raises(InvalidPasswordError)
    def test_validate_password_no_number_exception(self):
        user.validate_password('abcdefg', exception_on_invalid=True)

    @tag('user')
    @raises(InvalidPasswordError)
    def test_validate_password_too_short_exception(self):
        user.validate_password('defg', exception_on_invalid=True)


class TestAssociateStripeTokenFailure(PooldLibPostgresBaseTest):
    # These are functional tests which depend on the stripe api.
    # To run all stripe api related tests run: $ make tests-stripe
    # To run all tests which utilize external services run: $ make
    EXP_FAIL_CARD_NUMBER = 4000000000000069
    DECLINE_FAIL_CARD_NUMBER = 4000000000000002
    PROCESSING_ERROR_FAIL_CARD_NUMBER = 4000000000000119
    TEST_CARD_CVC = 123

    def setUp(self):
        super(TestAssociateStripeTokenFailure, self).setUp()

        try:
            config_path = os.path.join(os.path.dirname(DIR), '.env')
            config.update_with_file(config_path)
        except:
            pass

        n = uuid().hex
        username = 'StripeUser-%s' % n[:16]
        name = 'StripeUser %s' % n[16:]
        email = 'StripeUser-%s@example.com' % n[16:]
        self.user = self.create_user(username, name, email=email)

    @tag('external', 'stripe', 'stripe-error')
    @raises(UserCreditCardDeclinedError)
    def test_declined_card(self):
        exp = datetime.now() + timedelta(days=365)
        card = dict(number=self.DECLINE_FAIL_CARD_NUMBER,
                    cvc=self.TEST_CARD_CVC,
                    exp_month=exp.month,
                    exp_year=exp.year)
        token = stripe.Token.create(api_key=config.STRIPE_SECRET_KEY, card=card)
        user.associate_stripe_token(self.user, token.id, config.STRIPE_SECRET_KEY)

    @tag('external', 'stripe', 'stripe-error')
    @raises(UserCreditCardDeclinedError)
    def test_failed_exp(self):
        exp = datetime.now() + timedelta(days=365)
        card = dict(number=self.EXP_FAIL_CARD_NUMBER,
                    cvc=self.TEST_CARD_CVC,
                    exp_month=exp.month,
                    exp_year=exp.year)
        token = stripe.Token.create(api_key=config.STRIPE_SECRET_KEY, card=card)
        user.associate_stripe_token(self.user, token.id, config.STRIPE_SECRET_KEY)

    @tag('external', 'stripe', 'stripe-error')
    @raises(UserCreditCardDeclinedError)
    def test_failed_processing_error(self):
        exp = datetime.now() + timedelta(days=365)
        card = dict(number=self.PROCESSING_ERROR_FAIL_CARD_NUMBER,
                    cvc=self.TEST_CARD_CVC,
                    exp_month=exp.month,
                    exp_year=exp.year)
        token = stripe.Token.create(api_key=config.STRIPE_SECRET_KEY, card=card)
        user.associate_stripe_token(self.user, token.id, config.STRIPE_SECRET_KEY)


class TestAssociateStripeToken(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestAssociateStripeToken, self).setUp()
        self.payment_patcher = patch('pooldlib.api.user.StripeCustomer')
        self.payment_patched = self.payment_patcher.start()
        self.patched_payment = Mock()
        self.payment_patched.return_value = self.patched_payment
        self.addCleanup(self.payment_patcher.stop)

        n = uuid().hex
        username = 'StripeUser-%s' % n[:16]
        name = 'StripeUser %s' % n[16:]
        email = 'StripeUser-%s@example.com' % n[16:]
        self.user = self.create_user(username, name, email=email)

        n = uuid().hex
        username = 'StripeUser-%s' % n[:16]
        name = 'StripeUser %s' % n[16:]
        email = 'StripeUser-%s@example.com' % n[16:]
        self.existing_user = self.create_user(username, name, email=email)
        self.existing_user_id = uuid().hex
        self.create_user_meta(self.existing_user, stripe_customer_id=self.existing_user_id)

    @tag('user')
    def test_simple_exchange(self):
        stripe_customer_id = 'cus_%s' % uuid().hex
        self.patched_payment.token_for_customer.return_value = stripe_customer_id

        token = uuid().hex
        user.associate_stripe_token(self.user, token, None)

        self.patched_payment.token_for_customer.assert_called_once_with(token, self.user)
        user_meta = UserMetaModel.query.filter_by(user_id=self.user.id)\
                                       .filter_by(key='stripe_customer_id')\
                                       .first()
        assert_true(user_meta is not None)
        assert_equal(stripe_customer_id, user_meta.value)

    @tag('user')
    @raises(PreviousStripeAssociationError)
    def test_exchange_preexisting_user(self):
        stripe_customer_id = 'cus_%s' % uuid().hex
        self.patched_payment.token_for_customer.return_value = stripe_customer_id

        token = uuid().hex
        user.associate_stripe_token(self.existing_user, token, None)

    @tag('user')
    def test_exchange_preexisting_user_forced(self):
        user_meta = UserMetaModel.query.filter_by(user_id=self.existing_user.id)\
                                       .filter_by(key='stripe_customer_id')\
                                       .first()
        assert_true(user_meta is not None)
        assert_equal(self.existing_user_id, user_meta.value)

        stripe_customer_id = 'cus_%s' % uuid().hex
        self.patched_payment.token_for_customer.return_value = stripe_customer_id

        token = uuid().hex
        user.associate_stripe_token(self.existing_user, token, None, force=True)

        self.patched_payment.token_for_customer.assert_called_once_with(token, self.existing_user)
        user_meta = UserMetaModel.query.filter_by(user_id=self.existing_user.id)\
                                       .filter_by(key='stripe_customer_id')\
                                       .first()
        assert_true(user_meta is not None)
        assert_equal(stripe_customer_id, user_meta.value)

    @tag('user')
    def test_exchange_preexisting_user_identical_customer_returned(self):
        stripe_customer_id = 'cus_%s' % uuid().hex
        self.create_user_meta(self.user, stripe_customer_id=stripe_customer_id)

        user_meta = UserMetaModel.query.filter_by(user_id=self.user.id)\
                                       .filter_by(key='stripe_customer_id')\
                                       .first()
        assert_true(user_meta is not None)
        assert_equal(stripe_customer_id, user_meta.value)

        self.patched_payment.token_for_customer.return_value = stripe_customer_id

        token = uuid().hex
        user.associate_stripe_token(self.user, token, None)

        self.patched_payment.token_for_customer.assert_called_once_with(token, self.user)
        user_meta = UserMetaModel.query.filter_by(user_id=self.user.id)\
                                       .filter_by(key='stripe_customer_id')\
                                       .first()
        assert_true(user_meta is not None)
        assert_equal(stripe_customer_id, user_meta.value)

    @tag('user')
    @raises(ExternalAPIUsageError)
    def test_stripe_authentication_error(self):
        def exception(*args, **kwargs):
            msg = 'Test Message'
            raise stripe.AuthenticationError(msg)
        self.patched_payment.token_for_customer.side_effect = exception
        token = uuid().hex
        user.associate_stripe_token(self.user, token, None)

    @tag('user')
    @raises(ExternalAPIUsageError)
    def test_stripe_invalid_request_error(self):
        def exception(*args, **kwargs):
            msg = 'Test Message'
            raise stripe.InvalidRequestError(msg, None)
        self.patched_payment.token_for_customer.side_effect = exception
        token = uuid().hex
        user.associate_stripe_token(self.user, token, None)

    @tag('user')
    @raises(ExternalAPIError)
    def test_stripe_api_error(self):
        def exception(*args, **kwargs):
            msg = 'Test Message'
            raise stripe.APIError(msg)
        self.patched_payment.token_for_customer.side_effect = exception
        token = uuid().hex
        user.associate_stripe_token(self.user, token, None)

    @tag('user')
    @raises(ExternalAPIUnavailableError)
    def test_stripe_api_connection_error(self):
        def exception(*args, **kwargs):
            msg = 'Test Message'
            raise stripe.APIConnectionError(msg)
        self.patched_payment.token_for_customer.side_effect = exception
        token = uuid().hex
        user.associate_stripe_token(self.user, token, None)


class TestAssociateStripeAuthorizationCode(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestAssociateStripeAuthorizationCode, self).setUp()
        self.stripe_user_patcher = patch('pooldlib.api.user.StripeUser')
        self.stripe_user_patched = self.stripe_user_patcher.start()
        self.stripe_user_instance = Mock()
        self.stripe_user_patched.return_value = self.stripe_user_instance
        self.addCleanup(self.stripe_user_patcher.stop)

        n = uuid().hex
        username = 'StripeUser-%s' % n[:16]
        name = 'StripeUser %s' % n[16:]
        email = 'StripeUser-%s@example.com' % n[16:]
        self.user = self.create_user(username, name, email=email)

        n = uuid().hex
        username = 'StripeUser-%s' % n[:16]
        name = 'StripeUser %s' % n[16:]
        email = 'StripeUser-%s@example.com' % n[16:]
        self.existing_user = self.create_user(username, name, email=email)
        self.existing_user_id = uuid().hex
        self.stripe_user_id = uuid().hex
        self.create_user_meta(self.existing_user, stripe_user_id=self.stripe_user_id)

    @tag('user')
    def test_simple_associate(self):
        auth_token = uuid().hex
        ret = dict(user_id=uuid().hex,
                   access_token=uuid().hex,
                   public_key=uuid().hex,
                   scope='read-write')

        self.stripe_user_instance.process_authorization_code.return_value = ret

        # Confirm the user has no previous association
        assert_true(self._get_user_meta(self.user, 'stripe_user_id') is None)
        assert_true(self._get_user_meta(self.user, 'stripe_user_token') is None)
        assert_true(self._get_user_meta(self.user, 'stripe_user_public_key') is None)
        assert_true(self._get_user_meta(self.user, 'stripe_user_grant_scope') is None)

        user.associate_stripe_authorization_code(self.user, auth_token, None)
        self.stripe_user_instance.process_authorization_code.assert_called_once_with(auth_token, self.user)

        assert_equal(ret['user_id'], self._get_user_meta(self.user, 'stripe_user_id').value)
        assert_equal(ret['access_token'], self._get_user_meta(self.user, 'stripe_user_token').value)
        assert_equal(ret['public_key'], self._get_user_meta(self.user, 'stripe_user_public_key').value)
        assert_equal(ret['scope'], self._get_user_meta(self.user, 'stripe_user_grant_scope').value)

    @tag('user')
    @raises(PreviousStripeAssociationError)
    def test_associate_preexisting_user(self):
        auth_token = uuid().hex
        ret = dict(user_id=uuid().hex,
                   access_token=uuid().hex,
                   public_key=uuid().hex,
                   scope='read-write')

        self.stripe_user_instance.process_authorization_code.return_value = ret
        user.associate_stripe_authorization_code(self.existing_user, auth_token, None)

    @tag('user')
    def test_associate_preexisting_user_force(self):
        auth_token = uuid().hex
        ret = dict(user_id=uuid().hex,
                   access_token=uuid().hex,
                   public_key=uuid().hex,
                   scope='read-write')

        self.stripe_user_instance.process_authorization_code.return_value = ret

        # Confirm the user has preexisting stripe user id
        assert_equal(self.stripe_user_id, self._get_user_meta(self.existing_user, 'stripe_user_id').value)

        user.associate_stripe_authorization_code(self.user, auth_token, None, force=True)
        self.stripe_user_instance.process_authorization_code.assert_called_once_with(auth_token, self.user)

        assert_equal(ret['user_id'], self._get_user_meta(self.user, 'stripe_user_id').value)
        assert_equal(ret['access_token'], self._get_user_meta(self.user, 'stripe_user_token').value)
        assert_equal(ret['public_key'], self._get_user_meta(self.user, 'stripe_user_public_key').value)
        assert_equal(ret['scope'], self._get_user_meta(self.user, 'stripe_user_grant_scope').value)

    @tag('user')
    def test_associate_preexisting_user_identical_user_id_returned(self):
        auth_token = uuid().hex
        ret = dict(user_id=self.stripe_user_id,
                   access_token=uuid().hex,
                   public_key=uuid().hex,
                   scope='read-write')

        self.stripe_user_instance.process_authorization_code.return_value = ret

        # Confirm the user has preexisting stripe user id
        assert_equal(self.stripe_user_id, self._get_user_meta(self.existing_user, 'stripe_user_id').value)

        user.associate_stripe_authorization_code(self.user, auth_token, None, force=True)
        self.stripe_user_instance.process_authorization_code.assert_called_once_with(auth_token, self.user)

        assert_equal(ret['user_id'], self._get_user_meta(self.user, 'stripe_user_id').value)
        assert_equal(ret['access_token'], self._get_user_meta(self.user, 'stripe_user_token').value)
        assert_equal(ret['public_key'], self._get_user_meta(self.user, 'stripe_user_public_key').value)
        assert_equal(ret['scope'], self._get_user_meta(self.user, 'stripe_user_grant_scope').value)

    @tag('user')
    @raises(ExternalAPIUsageError)
    def test_stripe_authentication_error(self):
        auth_token = uuid().hex
        msg = 'Test message'

        def exception(*args, **kwargs):
            raise stripe.AuthenticationError(msg)
        self.stripe_user_instance.process_authorization_code.side_effect = exception
        user.associate_stripe_authorization_code(self.user, auth_token, None)

    @tag('user')
    @raises(ExternalAPIUsageError)
    def test_stripe_invalid_request_error(self):
        auth_token = uuid().hex
        msg = 'Test message'

        def exception(*args, **kwargs):
            raise stripe.InvalidRequestError(msg, None)
        self.stripe_user_instance.process_authorization_code.side_effect = exception
        user.associate_stripe_authorization_code(self.user, auth_token, None)

    @tag('user')
    @raises(ExternalAPIError)
    def test_stripe_api_error(self):
        auth_token = uuid().hex
        msg = 'Test message'

        def exception(*args, **kwargs):
            raise stripe.APIError(msg)
        self.stripe_user_instance.process_authorization_code.side_effect = exception
        user.associate_stripe_authorization_code(self.user, auth_token, None)

    @tag('user')
    @raises(ExternalAPIUnavailableError)
    def test_stripe_api_connection_error(self):
        auth_token = uuid().hex
        msg = 'Test message'

        def exception(*args, **kwargs):
            raise stripe.APIConnectionError(msg)
        self.stripe_user_instance.process_authorization_code.side_effect = exception
        user.associate_stripe_authorization_code(self.user, auth_token, None)

    def _get_user_meta(self, user, key):
        user_meta = UserMetaModel.query.filter_by(user_id=user.id)\
                                       .filter_by(key=key)\
                                       .first()
        return user_meta


class TestPaymentToCampaign(PooldLibPostgresBaseTest):
    # These are functional tests which depend on the stripe api.
    # To run all stripe api related tests run: $ make tests-stripe
    # To run all tests which utilize external services run: $ make
    # NOTE :: this test depends on the following environment variables
    # NOTE :: being defined: TEST_CARD_VISA_NUMBER, TEST_CARD_VISA_CVC, STRIPE_SECRET_KEY
    TEST_CARD_VISA_NUMBER = 4242424242424242
    TEST_CARD_VISA_CVC = 123

    def setUp(self):
        super(TestPaymentToCampaign, self).setUp()

        try:
            config_path = os.path.join(os.path.dirname(DIR), '.env')
            config.update_with_file(config_path)
        except:
            pass

        n = uuid().hex
        username = 'StripeUser-%s' % n[:16]
        name = 'StripeUser %s' % n[16:]
        email = 'StripeUser-%s@example.com' % n[16:]
        self.user = self.create_user(username, name, email=email)
        self.user_balance = self.create_balance(user=self.user, currency_code='USD', amount=Decimal(0))

        exp = datetime.now() + timedelta(days=365)
        stripe_customer_id = _create_stripe_customer_for_card(self.TEST_CARD_VISA_NUMBER,
                                                              self.TEST_CARD_VISA_CVC,
                                                              exp.month,
                                                              exp.year,
                                                              self.user)

        self.create_user_meta(self.user, stripe_customer_id=stripe_customer_id)

        n = uuid().hex
        username = 'StripeUser-%s' % n[:16]
        name = 'StripeUser %s' % n[16:]
        email = 'StripeUser-%s@example.com' % n[16:]
        self.organizer = self.create_user(username, name, email=email)
        self.organizer_balance = self.create_balance(user=self.organizer, currency_code='USD', amount=Decimal(0))
        self.create_user_meta(self.organizer, stripe_user_id=uuid().hex)
        self.create_user_meta(self.organizer, stripe_user_token=config.STRIPE_CONNECT_AUTH_TOKEN)

        self.com_name = 'Test Stripe Payment Campaign'
        self.com_description = 'To Test Stripe Payment Campaign'
        self.campaign = self.create_campaign(self.com_name, self.com_description)
        self.campaign_balance = self.create_balance(campaign=self.campaign, currency_code='USD', amount=Decimal(0))

        self.stripe_fee = FeeModel.query.filter_by(name='stripe-transaction').first()
        self.poold_fee = FeeModel.query.filter_by(name='poold-transaction').first()
        self.currency = CurrencyModel.query.filter_by(code='USD').first()

        self.stripe_balance = BalanceModel.query.join(CurrencyModel)\
                                                .filter(CurrencyModel.code == 'USD')\
                                                .join(UserModel)\
                                                .filter(UserModel.username == 'stripe-transaction')\
                                                .first()
        self.poold_balance = BalanceModel.query.join(CurrencyModel)\
                                               .filter(CurrencyModel.code == 'USD')\
                                               .join(UserModel)\
                                               .filter(UserModel.username == 'poold-transaction')\
                                               .first()

    @tag('external', 'stripe')
    @patch('pooldlib.api.user.get_campaign_organizer')
    def test_simple_payment(self, mock_get_organizer):
        mock_get_organizer.return_value = self.organizer
        amount = Decimal('100')

        ldgr_ids = user.payment_to_campaign(self.user,
                                            self.campaign,
                                            amount,
                                            self.currency,
                                            fees=(self.stripe_fee,))
        deposit_id, withdrawal_id = ldgr_ids
        user_txn = TransactionModel.query.filter_by(id=deposit_id)\
                                         .filter_by(balance_id=self.user_balance.id)\
                                         .first()
        dept_ldgr = ExternalLedgerModel.query.filter_by(record_id=deposit_id)\
                                             .filter_by(processor='stripe')\
                                             .filter_by(fee_id=None)\
                                             .first()
        withd_ldgr = ExternalLedgerModel.query.filter_by(record_id=withdrawal_id)\
                                              .filter_by(processor='stripe')\
                                              .filter_by(fee_id=None)\
                                              .first()

        assert_equal(Decimal('100.0000'), user_txn.credit)
        assert_true(user_txn.debit is None)
        assert_equal(Decimal('103.3000'), dept_ldgr.credit)
        assert_true(dept_ldgr.debit is None)
        assert_equal(Decimal('100.0000'), withd_ldgr.debit)
        assert_true(withd_ldgr.credit is None)

        org_txn = TransactionModel.query.filter_by(id=withdrawal_id)\
                                        .filter_by(balance_id=self.organizer_balance.id)\
                                        .first()
        assert_equal(Decimal('100.0000'), org_txn.debit)
        assert_true(org_txn.credit is None)

        stripe_ldgr = ExternalLedgerModel.query.filter_by(record_id=deposit_id)\
                                               .filter_by(fee_id=self.stripe_fee.id)\
                                               .first()
        assert_equal(Decimal('3.3000'), stripe_ldgr.debit)
        assert_true(stripe_ldgr.credit is None)

    @tag('external', 'stripe', 'stripe-payment')
    @patch('pooldlib.api.user.get_campaign_organizer')
    def test_payment_multiple_fees(self, mock_get_organizer):
        mock_get_organizer.return_value = self.organizer
        m_currency = Mock()
        m_currency.code = 'USD'
        amount = Decimal('100')

        ldgr_ids = user.payment_to_campaign(self.user,
                                            self.campaign,
                                            amount,
                                            self.currency,
                                            fees=(self.stripe_fee, self.poold_fee),
                                            full_name="Imalittle Teapot")
        deposit_id, withdrawal_id = ldgr_ids

        user_txn = TransactionModel.query.filter_by(id=deposit_id)\
                                         .filter_by(balance_id=self.user_balance.id)\
                                         .first()
        dpt_ldgrs = ExternalLedgerModel.query.filter_by(record_id=deposit_id)\
                                             .filter_by(processor='stripe')\
                                             .filter_by(fee_id=None)\
                                             .first()
        assert_equal(Decimal('100.0000'), user_txn.credit)
        assert_true(user_txn.debit is None)
        assert_equal(Decimal('106.3900'), dpt_ldgrs.credit)
        assert_true(dpt_ldgrs.debit is None)
        assert_equal("Imalittle Teapot", dpt_ldgrs.full_name)

        org_txn = TransactionModel.query.filter_by(id=withdrawal_id)\
                                        .filter_by(balance_id=self.organizer_balance.id)\
                                        .first()
        assert_equal(Decimal('100.0000'), org_txn.debit)
        assert_true(org_txn.credit is None)

        stripe_ldgr = ExternalLedgerModel.query.filter_by(record_id=deposit_id)\
                                               .filter_by(fee_id=self.stripe_fee.id)\
                                               .first()
        assert_equal(Decimal('3.3900'), stripe_ldgr.debit)
        assert_true(stripe_ldgr.credit is None)
        assert_true(stripe_ldgr.full_name is None)

        poold_ldgr = ExternalLedgerModel.query.filter_by(record_id=deposit_id)\
                                              .filter_by(fee_id=self.poold_fee.id)\
                                              .first()
        assert_equal(Decimal('3.0000'), poold_ldgr.debit)
        assert_true(poold_ldgr.credit is None)
        assert_true(poold_ldgr.full_name is None)


class TestPaymentToCampaignGoal(PooldLibPostgresBaseTest):
    # These are functional tests which depend on the stripe api.
    # To run all stripe api related tests run: $ make tests-stripe
    # To run all tests which utilize external services run: $ make
    # NOTE :: this test depends on the following environment variables
    # NOTE :: being defined: TEST_CARD_VISA_NUMBER, TEST_CARD_VISA_CVC, STRIPE_SECRET_KEY
    TEST_CARD_VISA_NUMBER = 4242424242424242
    TEST_CARD_VISA_CVC = 123

    def setUp(self):
        super(TestPaymentToCampaignGoal, self).setUp()

        try:
            config_path = os.path.join(os.path.dirname(DIR), '.env')
            config.update_with_file(config_path)
        except:
            pass

        n = uuid().hex
        username = 'StripeUser-%s' % n[:16]
        name = 'StripeUser %s' % n[16:]
        email = 'StripeUser-%s@example.com' % n[16:]
        self.user = self.create_user(username, name, email=email)
        self.user_balance = self.create_balance(user=self.user, currency_code='USD', amount=Decimal(0))

        exp = datetime.now() + timedelta(days=365)
        stripe_customer_id = _create_stripe_customer_for_card(self.TEST_CARD_VISA_NUMBER,
                                                              self.TEST_CARD_VISA_CVC,
                                                              exp.month,
                                                              exp.year,
                                                              self.user)

        self.create_user_meta(self.user, stripe_customer_id=stripe_customer_id)

        n = uuid().hex
        username = 'StripeUser-%s' % n[:16]
        name = 'StripeUser %s' % n[16:]
        email = 'StripeUser-%s@example.com' % n[16:]
        self.organizer = self.create_user(username, name, email=email)
        self.organizer_balance = self.create_balance(user=self.organizer, currency_code='USD', amount=Decimal(0))
        self.create_user_meta(self.organizer, stripe_user_id=uuid().hex)
        self.create_user_meta(self.organizer, stripe_user_token=config.STRIPE_CONNECT_AUTH_TOKEN)

        self.com_name = 'Test Stripe Payment Campaign'
        self.com_description = 'To Test Stripe Payment Campaign'
        self.campaign = self.create_campaign(self.com_name, self.com_description)
        self.campaign_balance = self.create_balance(campaign=self.campaign, currency_code='USD', amount=Decimal(0))
        self.campaign_goal = self.create_campaign_goal(self.campaign,
                                                       self.com_name + ' Goal',
                                                       self.com_description + ' Goal')

        self.stripe_fee = FeeModel.query.filter_by(name='stripe-transaction').first()
        self.poold_fee = FeeModel.query.filter_by(name='poold-transaction').first()
        self.currency = CurrencyModel.query.filter_by(code='USD').first()

        self.stripe_balance = BalanceModel.query.join(CurrencyModel)\
                                                .filter(CurrencyModel.code == 'USD')\
                                                .join(UserModel)\
                                                .filter(UserModel.username == 'stripe-transaction')\
                                                .first()
        self.poold_balance = BalanceModel.query.join(CurrencyModel)\
                                               .filter(CurrencyModel.code == 'USD')\
                                               .join(UserModel)\
                                               .filter(UserModel.username == 'poold-transaction')\
                                               .first()

    @tag('external', 'stripe')
    @patch('pooldlib.api.user.get_campaign_organizer')
    def test_simple_payment(self, mock_get_organizer):
        mock_get_organizer.return_value = self.organizer
        amount = Decimal('100')

        ldgr_ids = user.payment_to_campaign(self.user,
                                            self.campaign,
                                            amount,
                                            self.currency,
                                            goal=self.campaign_goal,
                                            fees=(self.stripe_fee,))
        deposit_id, withdrawal_id = ldgr_ids

        user_goal_deposit = CampaignGoalLedgerModel.query.filter_by(party_id=self.user.id).first()
        assert_equal(Decimal('100.0000'), user_goal_deposit.credit)
        assert_true(user_goal_deposit.debit is None)
        org_goal_withdrawal = CampaignGoalLedgerModel.query.filter_by(party_id=self.organizer.id).first()
        assert_equal(Decimal('100.0000'), org_goal_withdrawal.debit)
        assert_true(org_goal_withdrawal.credit is None)

        user_txn = TransactionModel.query.filter_by(id=deposit_id)\
                                         .filter_by(balance_id=self.user_balance.id)\
                                         .first()
        dept_ldgr = ExternalLedgerModel.query.filter_by(record_id=deposit_id)\
                                             .filter_by(processor='stripe')\
                                             .filter_by(fee_id=None)\
                                             .first()
        withd_ldgr = ExternalLedgerModel.query.filter_by(record_id=withdrawal_id)\
                                              .filter_by(processor='stripe')\
                                              .filter_by(fee_id=None)\
                                              .first()

        assert_equal(Decimal('100.0000'), user_txn.credit)
        assert_true(user_txn.debit is None)
        assert_equal(Decimal('103.3000'), dept_ldgr.credit)
        assert_true(dept_ldgr.debit is None)
        assert_equal(Decimal('100.0000'), withd_ldgr.debit)
        assert_true(withd_ldgr.credit is None)

        org_txn = TransactionModel.query.filter_by(id=withdrawal_id)\
                                        .filter_by(balance_id=self.organizer_balance.id)\
                                        .first()
        assert_equal(Decimal('100.0000'), org_txn.debit)
        assert_true(org_txn.credit is None)

        stripe_ldgr = ExternalLedgerModel.query.filter_by(record_id=deposit_id)\
                                               .filter_by(fee_id=self.stripe_fee.id)\
                                               .first()
        assert_equal(Decimal('3.3000'), stripe_ldgr.debit)
        assert_true(stripe_ldgr.credit is None)

    @tag('external', 'stripe')
    @patch('pooldlib.api.user.get_campaign_organizer')
    def test_payment_multiple_fees(self, mock_get_organizer):
        mock_get_organizer.return_value = self.organizer
        m_currency = Mock()
        m_currency.code = 'USD'
        amount = Decimal('100')

        ldgr_ids = user.payment_to_campaign(self.user,
                                            self.campaign,
                                            amount,
                                            self.currency,
                                            goal=self.campaign_goal,
                                            fees=(self.stripe_fee, self.poold_fee))
        deposit_id, withdrawal_id = ldgr_ids

        user_goal_deposit = CampaignGoalLedgerModel.query.filter_by(party_id=self.user.id).first()
        assert_equal(Decimal('100.0000'), user_goal_deposit.credit)
        assert_true(user_goal_deposit.debit is None)
        org_goal_withdrawal = CampaignGoalLedgerModel.query.filter_by(party_id=self.organizer.id).first()
        assert_equal(Decimal('100.0000'), org_goal_withdrawal.debit)
        assert_true(org_goal_withdrawal.credit is None)

        user_txn = TransactionModel.query.filter_by(id=deposit_id)\
                                         .filter_by(balance_id=self.user_balance.id)\
                                         .first()
        dep_ldgr = ExternalLedgerModel.query.filter_by(record_id=deposit_id)\
                                            .filter_by(processor='stripe')\
                                            .filter_by(fee_id=None)\
                                            .first()
        withd_ldgr = ExternalLedgerModel.query.filter_by(record_id=withdrawal_id)\
                                              .filter_by(processor='stripe')\
                                              .filter_by(fee_id=None)\
                                              .first()

        assert_equal(Decimal('100.0000'), user_txn.credit)
        assert_true(user_txn.debit is None)
        assert_equal(Decimal('106.3900'), dep_ldgr.credit)
        assert_true(dep_ldgr.debit is None)
        assert_equal(Decimal('100.0000'), withd_ldgr.debit)
        assert_true(withd_ldgr.credit is None)

        org_txn = TransactionModel.query.filter_by(id=withdrawal_id)\
                                        .filter_by(balance_id=self.organizer_balance.id)\
                                        .first()
        assert_equal(Decimal('100.0000'), org_txn.debit)
        assert_true(org_txn.credit is None)

        stripe_ldgr = ExternalLedgerModel.query.filter_by(record_id=deposit_id)\
                                               .filter_by(fee_id=self.stripe_fee.id)\
                                               .first()
        assert_equal(Decimal('3.3900'), stripe_ldgr.debit)
        assert_true(stripe_ldgr.credit is None)

        poold_ldgr = ExternalLedgerModel.query.filter_by(record_id=deposit_id)\
                                              .filter_by(fee_id=self.poold_fee.id)\
                                              .first()
        assert_equal(Decimal('3.0000'), poold_ldgr.debit)
        assert_true(poold_ldgr.credit is None)


class TestFailedPaymentToCampaign(PooldLibPostgresBaseTest):
    # These are functional tests which depend on the stripe api.
    # To run all stripe api related tests run: $ make tests-stripe
    # To run all tests which utilize external services run: $ make
    FAIL_CARD_NUMBER = 4000000000000341
    TEST_CARD_CVC = 123

    def setUp(self):
        super(TestFailedPaymentToCampaign, self).setUp()

        try:
            config_path = os.path.join(os.path.dirname(DIR), '.env')
            config.update_with_file(config_path)
        except:
            pass

        n = uuid().hex
        username = 'StripeUser-%s' % n[:16]
        name = 'StripeUser %s' % n[16:]
        email = 'StripeUser-%s@example.com' % n[16:]
        self.user = self.create_user(username, name, email=email)

        n = uuid().hex
        username = 'StripeUser-%s' % n[:16]
        name = 'StripeUser %s' % n[16:]
        email = 'StripeUser-%s@example.com' % n[16:]
        self.organizer = self.create_user(username, name, email=email)
        self.create_user_meta(self.organizer, stripe_user_id=uuid().hex)
        self.create_user_meta(self.organizer, stripe_user_token=config.STRIPE_CONNECT_AUTH_TOKEN)

        self.stripe_fee = FeeModel.query.filter_by(name='stripe-transaction').first()
        self.poold_fee = FeeModel.query.filter_by(name='poold-transaction').first()

    @tag('external', 'stripe', 'stripe-error')
    @raises(UserCreditCardDeclinedError)
    @patch('pooldlib.api.user.get_campaign_organizer')
    def test_fail_card(self, mock_get_organizer):
        exp = datetime.now() + timedelta(days=365)
        stripe_customer_id = _create_stripe_customer_for_card(self.FAIL_CARD_NUMBER,
                                                              self.TEST_CARD_CVC,
                                                              exp.month,
                                                              exp.year,
                                                              self.user)

        self.create_user_meta(self.user, stripe_customer_id=stripe_customer_id)

        mock_get_organizer.return_value = self.organizer
        m_currency = Mock()
        m_currency.code = 'USD'
        m_campaign = Mock()
        m_campaign.id = randint(1, 999)
        amount = Decimal('100')

        user.payment_to_campaign(self.user,
                                 m_campaign,
                                 amount,
                                 m_currency,
                                 fees=(self.stripe_fee, self.poold_fee))


def _create_stripe_customer_for_card(number, cvc, exp_month, exp_year, user):
    card = dict(number=number,
                cvc=cvc,
                exp_month=exp_month,
                exp_year=exp_year)

    token = stripe.Token.create(api_key=config.STRIPE_SECRET_KEY, card=card)
    client = StripeCustomer(config.STRIPE_SECRET_KEY)
    stripe_customer = client.token_for_customer(token.id, user)
    return stripe_customer
