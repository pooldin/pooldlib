from datetime import datetime

from pooldlib.postgres import db
from pooldlib.postgres.types import DateTimeTZ


class LedgerMixin(object):
    created = db.Column(DateTimeTZ, default=datetime.utcnow)
    debit = db.Column(db.DECIMAL(precision=24, scale=4), nullable=False)
    credit = db.Column(db.DECIMAL(precision=24, scale=4), nullable=False)
