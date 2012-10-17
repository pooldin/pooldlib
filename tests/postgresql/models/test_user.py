from sqlalchemy.exc import IntegrityError

from nose.tools import raises, assert_equal, assert_true

from pooldlib.postgresql import db, User

from tests.base import PooldLibPostgresBaseTest


class TestUserModel(PooldLibPostgresBaseTest):

    def setUp(self):
        self.session = db.session

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
        u1 = User()
        u1.name = 'Testy McDuplicate'
        u1.username = 'mcduplicate'
        u1.password = 'mcduplicate'
        self.session.add(u1)
        self.session.flush()

        u2 = User()
        u2.name = 'Testy McDuplicate'
        u2.username = 'mcduplicate'
        u2.password = 'mcduplicate'
        self.session.add(u2)
        self.session.flush()
