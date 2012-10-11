from .. import db


class KeyValueMixin(object):
    key = db.Column(db.String(64), nullable=False)
    value = db.Column(db.Text, nullable=False)
