from sqlalchemy.exc import IntegrityError

from nose.tools import raises, assert_equal, assert_true

from pooldlib.postgresql import User

from tests.base import PooldLibDBBaseTest


class TestUserModel(PooldLibDBBaseTest):

    def test_create(self):
        u = User()
        u.name = 'Testy McTesterson'
        u.username = 'mctesterson'
        u.password = 'mctesterson'
        self.commit_model(u)

        qs = User.query.filter_by(username='mctesterson').all()
        assert_equal(1, len(qs))

        assert_true(u.password.startswith('sha1'))
        assert_true(len(u.password.split('$', 2)) == 3)

    @raises(IntegrityError)
    def test_create_duplicate(self):
        u = User()
        u.name = 'Testy McTesterson'
        u.username = 'mctesterson'
        u.password = 'mctesterson'
        self.commit_model(u)

        u = User()
        u.name = 'Testy McTesterson'
        u.username = 'mctesterson'
        u.password = 'mctesterson'
        self.commit_model(u)
