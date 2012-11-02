from decimal import Decimal

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
    db.drop_all()
    db.create_all()
    create_fixtures()


def teardown_package(self):
    pass
    #db.drop_all()


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
    from pooldlib.postgresql import Fee, User, Balance

    def factory(name, description, percentage, flat):
        u = User()
        u.username = name
        u.password = name
        db.session.add(u)
        db.session.flush()

        b = Balance()
        b.type = 'user'
        b.user_id = u.id
        b.amount = 0
        b.currency_id = 1
        db.session.add(b)

        f = Fee()
        f.name = name
        f.description = description
        f.fractional_pct = percentage
        f.flat = flat
        f.user_id = u.id
        db.session.add(f)

    fees = (('poold-transaction', 'Poold Inc. transaction processing fee.', Decimal('0.0300'), Decimal('0.0000')),
            ('stripe-transaction', 'Stripe transaction  processing fee.', Decimal('0.0290'), Decimal('0.3000')),
            ('gimmy-more', 'Fee used for testing.', Decimal('0.0500'), Decimal('0.5000')))

    for (n, d, p, f) in fees:
        factory(n, d, p, f)
    db.session.commit()


def tag(*tags):
    def wrap(func):
        for tag in tags:
            setattr(func, tag, True)
        return func
    return wrap
