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


def create_fixtures():
    _create_currencies()
    _create_fees()


def _create_currencies():
    from pooldlib.postgresql import Currency

    c = Currency(title='United States Dollar',
                 code='USD',
                 number=840,
                 unit='Dollar',
                 unit_plural='Dollars',
                 sign='$')
    c.title = 'United States Dollar'
    c.code = 'USD'
    c.number = 840
    c.unit = 'Dollar'
    c.unit_plural = 'Dollars'
    c.sign = '$'

    db.session.add(c)
    db.session.commit()


def _create_fees():
    from pooldlib.postgresql import Fee

    def factory(name, description):
        f = Fee()
        f.name = name
        f.description = description
        db.session.add(f)

    fees = (('processing', 'Financial transaction processing fee.'),
            ('stripe-txn', 'Stripe transaction fee.'))

    for (n, d) in fees:
        factory(n, d)
    db.session.commit()
