from datetime import datetime

from sqlalchemy.databases import postgresql

from pooldlib.postgresql import db
from pooldlib.postgresql.types import DateTimeTZ


class TrackTimeMixin(object):
    created = db.Column(DateTimeTZ, default=datetime.utcnow)
    modified = db.Column(DateTimeTZ,
                         default=datetime.utcnow,
                         onupdate=datetime.utcnow)


class TrackIPMixin(object):
    remote_ip = db.Column(postgresql.CIDR)
