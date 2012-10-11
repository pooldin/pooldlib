from datetime import datetime

from sqlalchemy.ext.hybrid import hybrid_property

from .. import db
from ..types import DateTimeTZ


class EnabledMixin(object):
    enabled = db.Column(db.Boolean, nullable=False, default=True)


class DisabledMixin(object):
    enabled = db.Column(db.Boolean, nullable=False, default=False)


class VerifiedMixin(object):
    verified = db.Column(db.Boolean, nullable=False, default=False)


class ActiveMixin(EnabledMixin):
    start = db.Column(DateTimeTZ, index=True)
    end = db.Column(DateTimeTZ, index=True)

    @hybrid_property
    def status(self):
        if not self.enabled:
            return 'disabled'

        now = datetime.utcnow()

        if self.active_start and self.active_start > now:
            return 'pending'

        if self.active_end and self.active_end < now:
            return 'finished'

        return 'live'

    @hybrid_property
    def is_live(self):
        return self.status == 'live'

    @hybrid_property
    def is_disabled(self):
        return self.status == 'disabled'

    @hybrid_property
    def is_pending(self):
        return self.status == 'pending'

    @hybrid_property
    def is_finished(self):
        return self.status == 'finished'

    @classmethod
    def filter_live(cls, now=None):
        if now is None:
            now = datetime.utcnow()

        query = cls.filter_by(enabled=True)
        query = query.filter(cls.active_start < now)
        query = query.filter(cls.active_end > now)
        return query.order_by(cls.active_start, cls.active_end)

    @classmethod
    def filter_finished(cls, now=None):
        if now is None:
            now = datetime.utcnow()

        query = cls.query.filter(cls.active_start < now)
        query = query.filter(cls.active_end < now)
        return query.order_by(cls.active_end.desc(), cls.active_start)

    @classmethod
    def first_live(cls, *args, **kw):
        return cls.filter_live(*args, **kw).first()

    @classmethod
    def first_finished(cls, *args, **kw):
        return cls.filter_finished(*args, **kw).first()
