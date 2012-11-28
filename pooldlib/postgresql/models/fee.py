from decimal import Decimal

from pooldlib.postgresql import db, common


class Fee(common.ConfigurationModel):
    fractional_pct = db.Column(db.DECIMAL(precision=5, scale=4),
                               nullable=False,
                               default=0)
    flat = db.Column(db.DECIMAL(precision=8, scale=4),
                     nullable=False,
                     default=0)

    @property
    def percentage(self):
        return self.fractional_pct * Decimal('100.0000')
