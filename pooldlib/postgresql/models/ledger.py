from pooldlib.postgresql import common, db
from pooldlib.postgresql.types import UUID


class InternalLedger(common.LedgerModel):
    __tablename__ = 'internal_ledger'

    record_id = db.Column(UUID)
    record_table = db.Column(db.Enum('transaction', 'exchange', 'transfer', name='record_table_enum'),
                             nullable=False,
                             index=True)
    party = db.Column(db.String(64), nullable=True, index=True)
    currency_id = db.Column(db.BigInteger(unsigned=True),
                            db.ForeignKey('currency.id'),
                            nullable=False)
    currency = db.relationship('Currency', backref='internal_ledger_entries', lazy='select')
    fee_id = db.Column(db.BigInteger(unsigned=True),
                       db.ForeignKey('fee.id'),
                       nullable=True)
    fee = db.relationship('Fee', backref='internal_ledger_entries', lazy='select')


class ExternalLedger(common.LedgerModel):
    __tablename__ = 'external_ledger'

    record_id = db.Column(UUID)
    record_table = db.Column(db.Enum('transaction', 'exchange', 'transfer', name='record_table_enum'),
                             nullable=False,
                             index=True)
    processor = db.Column(db.String(255), nullable=False, index=True)
    reference_number = db.Column(db.String(255), nullable=False, index=True)
    currency_id = db.Column(db.BigInteger(unsigned=True),
                            db.ForeignKey('currency.id'),
                            nullable=False)
    currency = db.relationship('Currency', backref='external_ledger_entries', lazy='select')
    fee_id = db.Column(db.BigInteger(unsigned=True),
                       db.ForeignKey('fee.id'),
                       nullable=True)
    fee = db.relationship('Fee', backref='external_ledger_entries', lazy='select')
    full_name = db.Column(db.String(255), nullable=True)


class CampaignGoalLedger(common.LedgerModel):
    __tablename__ = 'campaign_goal_ledger'

    campaign = db.relationship('Campaign', backref='goals_ledger', lazy='select')
    campaign_id = db.Column(db.BigInteger(unsigned=True),
                            db.ForeignKey('campaign.id'),
                            nullable=False)
    campaign_goal = db.relationship('CampaignGoal', backref='ledger', lazy='select')
    campaign_goal_id = db.Column(db.BigInteger(unsigned=True),
                                 db.ForeignKey('campaign_goal.id'),
                                 nullable=False)
    party_id = db.Column(db.BigInteger(unsigned=True))
    party_type = db.Column(db.Enum('user', 'campaign', name='campaign_goal_ledger_target_type_enum'),
                           nullable=False,
                           index=True)
