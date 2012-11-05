from pooldlib.postgresql import common, db
from pooldlib.postgresql.types import UUID


class Transfer(common.LedgerModel):
    record_id = db.Column(UUID, unique=False, index=True)
    balance = db.relationship('Balance', backref='transfers', lazy='select')
    balance_id = db.Column(db.BigInteger(unsigned=True),
                           db.ForeignKey('balance.id'),
                           nullable=False)


class Transaction(common.LedgerModel):
    balance = db.relationship('Balance', backref='transactions', lazy='select')
    balance_id = db.Column(db.BigInteger(unsigned=True),
                           db.ForeignKey('balance.id'),
                           nullable=False)
    community_goal = db.relationship('CommunityGoal', backref='purchased_goals', lazy='select')
    community_goal_id = db.Column(db.BigInteger(unsigned=True),
                                  db.ForeignKey('community_goal.id'),
                                  nullable=True)


class Exchange(common.LedgerModel):
    debit_currency_id = db.Column(db.BigInteger(unsigned=True),
                                  db.ForeignKey('currency.id'),
                                  nullable=False)
    debit_currency = db.relationship('Currency',
                                     backref='debit_exchanges',
                                     lazy='select',
                                     primaryjoin="Exchange.debit_currency_id==Currency.id")
    credit_currency_id = db.Column(db.BigInteger(unsigned=True),
                                   db.ForeignKey('currency.id'),
                                   nullable=False)
    credit_currency = db.relationship('Currency',
                                      backref='credit_exchanges',
                                      lazy='select',
                                      primaryjoin="Exchange.credit_currency_id==Currency.id")
    exchange_rate = db.Column(db.DECIMAL(precision=24, scale=4), nullable=False)
    balance = db.relationship('Balance', backref='exchanges', lazy='select')
    balance_id = db.Column(db.BigInteger(unsigned=True),
                           db.ForeignKey('balance.id'),
                           nullable=False)
