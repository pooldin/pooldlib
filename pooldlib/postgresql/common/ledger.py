from datetime import datetime

from pooldlib.postgresql import db
from pooldlib.postgresql.types import DateTimeTZ


class LedgerMixin(object):
    created = db.Column(DateTimeTZ, default=datetime.utcnow)
    debit = db.Column(db.DECIMAL(precision=24, scale=4), nullable=True)
    credit = db.Column(db.DECIMAL(precision=24, scale=4), nullable=True)
