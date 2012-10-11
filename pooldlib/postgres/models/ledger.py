from .. import common, db
from ..types import UUID


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
    currency = db.relationship('Currency', backref='internal_ledger_entries', lazy='dynamic')
    fee_id = db.Column(db.BigInteger(unsigned=True),
                       db.ForeignKey('fee.id'),
                       nullable=False)
    fee = db.relationship('Fee', backref='internal_ledger_entries', lazy='dynamic')


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
    currency = db.relationship('Currency', backref='external_ledger_entries', lazy='dynamic')
    fee_id = db.Column(db.BigInteger(unsigned=True),
                       db.ForeignKey('fee.id'),
                       nullable=False)
    fee = db.relationship('Fee', backref='external_ledger_entries', lazy='dynamic')
