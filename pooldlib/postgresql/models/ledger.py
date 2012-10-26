from pooldlib.postgresql import common, db
from pooldlib.postgresql.types import UUID


class InternalLedger(common.LedgerModel):
    __tablename__ = 'internal_ledger'

    record_id = db.Column(UUID)
    record_table = db.Column(db.Enum('transaction', 'exchange', 'transfer', name='record_table_enum'),
                             nullable=False,
                             index=True)
    party = db.Column(db.String(64), nullable=False, index=True)
    currency_id = db.Column(db.BigInteger(unsigned=True),
                            db.ForeignKey('currency.id'),
                            nullable=False)
    currency = db.relationship('Currency', backref='internal_ledger_entries', lazy='select')
    fee_id = db.Column(db.BigInteger(unsigned=True),
                       db.ForeignKey('fee.id'),
                       nullable=False)
    fee = db.relationship('Fee', backref='internal_ledger_entries', lazy='select')


class ExternalLedger(common.LedgerModel):
    __tablename__ = 'external_ledger'

    record_id = db.Column(UUID)
    record_table = db.Column(db.Enum('transaction', 'exchange', 'transfer', name='record_table_enum'),
                             nullable=False,
                             index=True)
    party = db.Column(db.String(255), nullable=False, index=True)
    external_reference_number = db.Column(db.String(255), nullable=False, index=True)
    currency_id = db.Column(db.BigInteger(unsigned=True),
                            db.ForeignKey('currency.id'),
                            nullable=False)
    currency = db.relationship('Currency', backref='external_ledger_entries', lazy='select')
    fee_id = db.Column(db.BigInteger(unsigned=True),
                       db.ForeignKey('fee.id'),
                       nullable=True)
    fee = db.relationship('Fee', backref='external_ledger_entries', lazy='select')


class CommunityGoalLedger(common.LedgerModel):
    __tablename__ = 'community_goal_ledger'

    community = db.relationship('Community', backref='goals_ledger', lazy='select')
    community_id = db.Column(db.BigInteger(unsigned=True),
                             db.ForeignKey('community.id'),
                             nullable=False)
    community_goal = db.relationship('CommunityGoal', backref='ledger', lazy='select')
    community_goal_id = db.Column(db.BigInteger(unsigned=True),
                                  db.ForeignKey('community_goal.id'),
                                  nullable=False)
    party_id = db.Column(db.BigInteger(unsigned=True))
    party_type = db.Column(db.Enum('user', 'community', name='community_goal_ledger_target_type_enum'),
                           nullable=False,
                           index=True)
