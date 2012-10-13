from uuid import uuid4 as uuid

from pooldlib.postgresql import db
from pooldlib.postgresql.types import UUID


class IDMixin(object):
    id = db.Column(db.BigInteger(unsigned=True), primary_key=True)


class UUIDMixin(object):
    id = db.Column(UUID, primary_key=True, default=uuid)
