from .. import common, db
from ..types import UUID


class Purchase(common.NameMixin, common.DescriptionMixin, common.Model):
    purchase_ledger_id = db.Column(UUID,
                                   db.ForeignKey('external_ledger.id'),
                                   nullable=False)
    purchase_ledger = db.relationship('ExternalLedger',
                                      backref='purchase',
                                      uselist=False,
                                      lazy='dynamic',
                                      primaryjoin='Purchase.purchase_ledger_id==ExternalLedger.id')
    fulfilled = db.Column(db.Boolean, default=False)
    refunded = db.Column(db.Boolean, default=False)
    refund_ledger_id = db.Column(UUID,
                                 db.ForeignKey('external_ledger.id'),
                                 nullable=False)
    refund_ledger = db.relationship('ExternalLedger',
                                    backref='refund',
                                    uselist=False,
                                    lazy='dynamic',
                                    primaryjoin='Purchase.refund_ledger_id==ExternalLedger.id')

    # These should be migrated to a hstore
    address_one = db.Column(db.String(255))
    address_two = db.Column(db.String(255))
    city = db.Column(db.String(255))
    state = db.Column(db.String(4))
    zip = db.Column(db.String(32))
    country = db.Column(db.String(255))
    email = db.Column(db.String(255), index=True)
