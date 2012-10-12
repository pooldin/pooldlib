from datetime import datetime

from sqlalchemy.databases import postgresql

from pooldlib.postgres import db
from pooldlib.postgres.types import DateTimeTZ


class TrackTimeMixin(object):
    created = db.Column(DateTimeTZ, default=datetime.utcnow)
    modified = db.Column(DateTimeTZ,
                         default=datetime.utcnow,
                         onupdate=datetime.utcnow)


class TrackIPMixin(object):
    remote_ip = db.Column(postgresql.CIDR)
