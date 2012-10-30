from uuid import uuid4 as uuid

from nose.tools import raises, assert_equal, assert_true, assert_false
from mock import patch

import stripe

from pooldlib.exceptions import (InvalidPasswordError,
                                 UsernameUnavailableError,
                                 EmailUnavailableError,
                                 PreviousStripeAssociationError,
                                 ExternalAPIUsageError,
                                 ExternalAPIError,
                                 ExternalAPIUnavailableError)
from pooldlib.api import user
from pooldlib.postgresql import db
from pooldlib.postgresql import (User as UserModel,
                                 UserMeta as UserMetaModel)

from tests.base import PooldLibPostgresBaseTest


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

    def test_get_with_username(self):
        u = user.get_by_username(self.username_a)
        assert_equal(self.username_a, u.username)
        assert_equal(self.name_a, u.name)
        assert_equal(self.email_a, u.email)

    def test_get_with_email(self):
        u = user.get_by_email(self.email_a)
        assert_equal(self.username_a, u.username)
        assert_equal(self.name_a, u.name)
        assert_equal(self.email_a, u.email)

    def test_get_with_email_case_difference(self):
        u = user.get_by_email(self.email_a.upper())
        assert_equal(self.username_a, u.username)
        assert_equal(self.name_a, u.name)
        assert_equal(self.email_a, u.email)

    def test_get_non_existant_user(self):
        non_user = user.get_by_username('nonexistant')
        assert_true(non_user is None)

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

    def test_create_user_returned(self):
        username = uuid().hex
        name = '%s %s' % (username[:16], username[16:])
        email = '%s@example.com' % username
        u = user.create(username, username, name=name, email=email)
        assert_true(isinstance(u, UserModel))

    @raises(UsernameUnavailableError)
    def test_create_duplicate_username(self):
        user.create(self.username, self.username, name=self.name)

    @raises(EmailUnavailableError)
    def test_create_duplicate_email(self):
        username = uuid().hex
        name = '%s %s' % (username[:16], username[16:])
        email = '%s@example.com' % self.username
        user.create(username, username, name=name, email=email)

    def test_create_user_no_name_no_metadata(self):
        username = uuid().hex
        user.create(username, username + '1')
        check_user = UserModel.query.filter_by(username=username).all()
        assert_equal(1, len(check_user))
        check_user = check_user[0]
        assert_equal(username, check_user.username)
        assert_true(check_user.enabled)
        assert_false(check_user.verified)

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

    @raises(InvalidPasswordError)
    def test_create_with_short_password(self):
        user.create('imauser', 'short1')

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

    def test_clear_name_attribute(self):
        check_user = UserModel.query.filter_by(username=self.username).first()
        assert_equal(self.name, check_user.name)

        user.update(self.user, name='')
        check_user = UserModel.query.filter_by(username=self.username).first()
        assert_true(check_user.name is None)

    @raises(InvalidPasswordError)
    def test_update_with_password_invalid_password(self):
        user.update(self.username, password='thisshouldfail')

    def test_update_with_password(self):
        new_password = 'abcde123'
        old_pass_encrypt = self.user.password
        user.update(self.user, password=new_password)

        assert_false(old_pass_encrypt == self.user.password)
        assert_true(self.user.is_password(new_password))

    @raises(EmailUnavailableError)
    def test_update_with_existing_email(self):
        username_two = uuid().hex
        name_two = '%s %s' % (username_two[:16], username_two[16:])
        email_two = '%s@example.com' % username_two
        new_user = self.create_user(username_two, name_two, email_two)
        user.update(new_user, email=self.email)

    @raises(UsernameUnavailableError)
    def test_update_with_existing_username(self):
        username_two = uuid().hex
        name_two = '%s %s' % (username_two[:16], username_two[16:])
        email_two = '%s@example.com' % username_two
        new_user = self.create_user(username_two, name_two, email_two)
        user.update(new_user, username=self.username)

    def test_update_single_field(self):
        newname = uuid().hex
        newname = '%s %s' % (newname[:16], newname[16:])
        assert_true(newname != self.user.name)

        old_mod = self.user.modified
        user.update(self.user, name=newname)

        check_user = UserModel.query.filter_by(username=self.username).first()
        assert_equal(newname, check_user.name)
        assert_true(old_mod < check_user.modified)

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

    def test_verify_correct_password(self):
        password = self.user.username + '1'
        assert_true(user.verify_password(self.user, password))

    def test_verify_incorrect_password(self):
        password = 'incorrect-password'
        assert_false(user.verify_password(self.user, password))


class TestValidatePassword(PooldLibPostgresBaseTest):

    def test_validate_good_password(self):
        assert_true(user.validate_password('1abcdef'))

    def test_validate_password_no_number(self):
        assert_false(user.validate_password('abcdefg'))

    def test_validate_password_to_short(self):
        assert_false(user.validate_password('defg'))

    @raises(InvalidPasswordError)
    def test_validate_password_no_number_exception(self):
        user.validate_password('abcdefg', exception_on_invalid=True)

    @raises(InvalidPasswordError)
    def test_validate_password_too_short_exception(self):
        user.validate_password('defg', exception_on_invalid=True)


class TestAssociateStripeToken(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestAssociateStripeToken, self).setUp()
        self.payment_patcher = patch('pooldlib.api.user.pooldlib.payment')
        self.patched_payment = self.payment_patcher.start()
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
        self.create_user_meta(self.existing_user, stripe_user_id=self.existing_user_id)

    def test_simple_exchange(self):
        stripe_user_id = 'cus_%s' % uuid().hex
        self.patched_payment.exchange_stripe_token_for_user.return_value = stripe_user_id

        token = uuid().hex
        user.associate_stripe_token(self.user, token)

        self.patched_payment.exchange_stripe_token_for_user.assert_called_once_with(token, self.user)
        user_meta = UserMetaModel.query.filter_by(user_id=self.user.id)\
                                       .filter_by(key='stripe_user_id')\
                                       .first()
        assert_true(user_meta is not None)
        assert_equal(stripe_user_id, user_meta.value)

    @raises(PreviousStripeAssociationError)
    def test_exchange_preexisting_user(self):
        stripe_user_id = 'cus_%s' % uuid().hex
        self.patched_payment.exchange_stripe_token_for_user.return_value = stripe_user_id

        token = uuid().hex
        user.associate_stripe_token(self.existing_user, token)

    def test_exchange_preexisting_user_forced(self):
        user_meta = UserMetaModel.query.filter_by(user_id=self.existing_user.id)\
                                       .filter_by(key='stripe_user_id')\
                                       .first()
        assert_true(user_meta is not None)
        assert_equal(self.existing_user_id, user_meta.value)

        stripe_user_id = 'cus_%s' % uuid().hex
        self.patched_payment.exchange_stripe_token_for_user.return_value = stripe_user_id

        token = uuid().hex
        user.associate_stripe_token(self.existing_user, token, force=True)

        self.patched_payment.exchange_stripe_token_for_user.assert_called_once_with(token, self.existing_user)
        user_meta = UserMetaModel.query.filter_by(user_id=self.existing_user.id)\
                                       .filter_by(key='stripe_user_id')\
                                       .first()
        assert_true(user_meta is not None)
        assert_equal(stripe_user_id, user_meta.value)

    def test_exchange_preexisting_user_identical_customer_returned(self):
        stripe_user_id = 'cus_%s' % uuid().hex
        self.create_user_meta(self.user, stripe_user_id=stripe_user_id)

        user_meta = UserMetaModel.query.filter_by(user_id=self.user.id)\
                                       .filter_by(key='stripe_user_id')\
                                       .first()
        assert_true(user_meta is not None)
        assert_equal(stripe_user_id, user_meta.value)

        self.patched_payment.exchange_stripe_token_for_user.return_value = stripe_user_id

        token = uuid().hex
        user.associate_stripe_token(self.user, token)

        self.patched_payment.exchange_stripe_token_for_user.assert_called_once_with(token, self.user)
        user_meta = UserMetaModel.query.filter_by(user_id=self.user.id)\
                                       .filter_by(key='stripe_user_id')\
                                       .first()
        assert_true(user_meta is not None)
        assert_equal(stripe_user_id, user_meta.value)

    @raises(ExternalAPIUsageError)
    def test_stripe_authentication_error(self):
        def exception(*args, **kwargs):
            msg = 'Test Message'
            raise stripe.AuthenticationError(msg)
        self.patched_payment.exchange_stripe_token_for_user.side_effect = exception
        token = uuid().hex
        user.associate_stripe_token(self.user, token)

    @raises(ExternalAPIUsageError)
    def test_stripe_invalid_request_error(self):
        def exception(*args, **kwargs):
            msg = 'Test Message'
            raise stripe.InvalidRequestError(msg, None)
        self.patched_payment.exchange_stripe_token_for_user.side_effect = exception
        token = uuid().hex
        user.associate_stripe_token(self.user, token)

    @raises(ExternalAPIError)
    def test_stripe_api_error(self):
        def exception(*args, **kwargs):
            msg = 'Test Message'
            raise stripe.APIError(msg)
        self.patched_payment.exchange_stripe_token_for_user.side_effect = exception
        token = uuid().hex
        user.associate_stripe_token(self.user, token)

    @raises(ExternalAPIUnavailableError)
    def test_stripe_api_unavailable_error(self):
        def exception(*args, **kwargs):
            msg = 'Test Message'
            raise stripe.APIConnectionError(msg)
        self.patched_payment.exchange_stripe_token_for_user.side_effect = exception
        token = uuid().hex
        user.associate_stripe_token(self.user, token)
