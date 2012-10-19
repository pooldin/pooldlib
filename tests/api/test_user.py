from uuid import uuid4 as uuid

from nose.tools import raises, assert_equal, assert_true, assert_false

from pooldlib.exceptions import (InvalidPasswordError,
                                 IllegalPasswordUpdateError,
                                 UnknownUserError,
                                 UsernameUnavailableError,
                                 EmailUnavailableError)
from pooldlib.api import user
from pooldlib.postgresql import db
from pooldlib.postgresql import (User as UserModel,
                                 UserMeta as UserMetaModel)

from tests.base import PooldLibPostgresBaseTest


class TestGetUser(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetUser, self).setUp()

        self.username_a = uuid().hex
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
        u = user.get(self.username_a)
        assert_equal(self.username_a, u.username)
        assert_equal(self.name_a, u.name)
        assert_equal(self.email_a, u.email)

    def test_get_with_email(self):
        u = user.get(self.email_a)
        assert_equal(self.username_a, u.username)
        assert_equal(self.name_a, u.name)
        assert_equal(self.email_a, u.email)

    def test_get_non_existant_user(self):
        non_user = user.get('nonexistant')
        assert_true(non_user is None)

    def test_get_disabled_user(self):
        self.user_a.enabled = False
        self.session.commit()
        disabled_user = user.get(self.username_a)
        assert_true(disabled_user is None)


class TestCreateUser(PooldLibPostgresBaseTest):

    @raises(UsernameUnavailableError)
    def test_create_duplicate_username(self):
        username = uuid().hex
        name = '%s %s' % (username[:16], username[16:])
        email = '%s@example.com' % username
        self.create_user(username, name, email)
        user.create(username, username)

    @raises(EmailUnavailableError)
    def test_create_duplicate_email(self):
        username_one = uuid().hex
        username_two = uuid().hex
        name_one = '%s %s' % (username_one[:16], username_one[16:])
        name_two = '%s %s' % (username_two[:16], username_two[16:])
        email = '%s@example.com' % username_one
        self.create_user(username_one, name_one, email)
        user.create(username_two, username_two, name=name_two, email=email)


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

    @raises(InvalidPasswordError)
    def test_update_with_password_invalid_password(self):
        user.update(self.username, password='thisshouldfail')

    def test_update_with_password(self):
        new_password = 'abcde123'
        old_pass_encrypt = self.user.password
        user.update(self.username, password=new_password)

        assert_false(old_pass_encrypt == self.user.password)
        assert_true(self.user.is_password(new_password))

    @raises(UnknownUserError)
    def test_update_non_existant_user(self):
        user.update('nonexistant', name='nonexistant')

    @raises(UnknownUserError)
    def test_update_disabled_user(self):
        self.user.enabled = False
        self.session.commit()
        user.update(self.username, name='nonexistant')

    @raises(EmailUnavailableError)
    def test_update_with_existing_email(self):
        username_two = uuid().hex
        name_two = '%s %s' % (username_two[:16], username_two[16:])
        email_two = '%s@example.com' % username_two
        self.create_user(username_two, name_two, email_two)
        user.create(username_two, username_two, name=name_two, email=self.email)

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

    @raises(UnknownUserError)
    def test_password_reset_non_existant_user(self):
        user.reset_password('nonexistant')

    @raises(UnknownUserError)
    def test_password_reset_disabled_user(self):
        self.user.enabled = False
        self.session.commit()
        user.verify_password(self.username, 'okpass1')


class TestDeactivateUser(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestDeactivateUser, self).setUp()

        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)
        self.user_balance = self.create_balance(user=self.user, currency_code='USD')
        self.session = db.session

    def test_disabled_user_username_lookup(self):
        user.disable(self.username)
        assert_true(user.get(self.username) is None)

    def test_disabled_user_id_lookup(self):
        id = self.user.id
        user.disable(id)
        assert_true(user.get(id) is None)

    def test_disabled_user_email_lookup(self):
        user.disable(self.email)
        assert_true(user.get(self.email) is None)


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
        assert_true(user.verify_password(self.username, password))

    def test_verify_incorrect_password(self):
        password = 'incorrect-password'
        assert_false(user.verify_password(self.username, password))

    @raises(UnknownUserError)
    def test_verify_non_existant_user(self):
        user.verify_password('nonexistant', 'badpass')

    @raises(UnknownUserError)
    def test_verify_disabled_user_username_lookup(self):
        self.user.enabled = False
        self.session.commit()
        user.verify_password(self.username, 'okpass1')

    @raises(UnknownUserError)
    def test_verify_disabled_user_id_lookup(self):
        self.user.enabled = False
        self.session.commit()
        user.verify_password(self.user.id, 'okpass1')

    @raises(UnknownUserError)
    def test_verify_disabled_user_email_lookup(self):
        self.user.enabled = False
        self.session.commit()
        user.verify_password(self.user.id, 'okpass1')


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
