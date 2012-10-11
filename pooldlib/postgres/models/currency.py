from .. import common, db


class Currency(common.DisabledMixin, common.Model):
    title = db.Column(db.String(128))
    code = db.Column(db.String(4), index=True)
    number = db.Column(db.SmallInteger(unsigned=True), index=True)
    unit = db.Column(db.String(32))
    unit_plural = db.Column(db.String(32))
    sign = db.Column(db.String(1))

    @classmethod
    def get(cls, code):
        return cls.query.filter_by(code=code).first()

    def __repr__(self):
        return '<Currency %r>' % self.code or self.title
