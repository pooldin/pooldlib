from pooldlib.postgres import db
from pooldlib.postgres.types import UUID


class IDMixin(object):
    id = db.Column(db.BigInteger(unsigned=True), primary_key=True)


class UUIDMixin(object):
    id = db.Column(UUID, primary_key=True)
