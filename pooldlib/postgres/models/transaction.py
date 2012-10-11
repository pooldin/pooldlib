from .. import common, db
from ..types import UUID


class Transfer(common.LedgerModel):
    group_id = db.Column(UUID, unique=True)
    balance = db.relationship('Balance', backref='transfers', lazy='dynamic')
    balance_id = db.Column(db.BigInteger(unsigned=True),
                           db.ForeignKey('balance.id'),
                           nullable=False)


class Transaction(common.LedgerModel):
    balance = db.relationship('Balance', backref='transactions', lazy='dynamic')
    balance_id = db.Column(db.BigInteger(unsigned=True),
                           db.ForeignKey('balance.id'),
                           nullable=False)
    community_goal = db.relationship('CommunityGoal', backref='purchased_goals', lazy='dynamic')
    community_goal_id = db.Column(db.BigInteger(unsigned=True),
                                  db.ForeignKey('community_goal.id'),
                                  nullable=False)


class Exchange(common.LedgerModel):
    debit_currency_id = db.Column(db.BigInteger(unsigned=True),
                                  db.ForeignKey('currency.id'),
                                  nullable=False)
    debit_currency = db.relationship('Currency',
                                     backref='debit_exchanges',
                                     lazy='dynamic',
                                     primaryjoin="Exchange.debit_currency_id==Currency.id")
    credit_currency_id = db.Column(db.BigInteger(unsigned=True),
                                   db.ForeignKey('currency.id'),
                                   nullable=False)
    credit_currency = db.relationship('Currency',
                                      backref='credit_exchanges',
                                      lazy='dynamic',
                                      primaryjoin="Exchange.credit_currency_id==Currency.id")
    exchange_rate = db.Column(db.DECIMAL(precision=24, scale=4), nullable=False)
    balance = db.relationship('Balance', backref='exchanges', lazy='dynamic')
    balance_id = db.Column(db.BigInteger(unsigned=True),
                           db.ForeignKey('balance.id'),
                           nullable=False)

