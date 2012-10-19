from pooldlib.postgresql import db


class KeyValueMixin(object):
    key = db.Column(db.String(64), nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
