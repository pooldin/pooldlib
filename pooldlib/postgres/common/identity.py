from .. import db
from ..types import UUID


class IDMixin(object):
    id = db.Column(db.BigInteger(unsigned=True), primary_key=True)


class UUIDMixin(object):
    id = db.Column(UUID, primary_key=True)
