from pooldlib.postgresql import db

SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/pooldin-test'
SQLALCHEMY_RECORD_QUERIES = False
SQLALCHEMY_ECHO = False
DEBUG = True


def setup_package(self):
    config = dict()
    config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    config['SQLALCHEMY_ECHO'] = SQLALCHEMY_ECHO
    config['SQLALCHEMY_RECORD_QUERIES'] = SQLALCHEMY_RECORD_QUERIES
    config['DEBUG'] = DEBUG
    db.init_connection(config)
    db.create_all()


def teardown_package(self):
    db.drop_all()
