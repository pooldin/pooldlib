from datetime import datetime

from sqlalchemy.databases import postgresql

from flask import request

from .. import db
from ..types import DateTimeTZ


def remote_ip():
    if not request:
        return

    ips = request.headers.getlist("X-Forwarded-For")

    if len(ips) > 0:
        return ips[0]

    if hasattr(request, 'remote_addr') and request.remote_addr:
        return request.remote_addr


class TrackTimeMixin(object):
    created = db.Column(DateTimeTZ, default=datetime.utcnow)
    modified = db.Column(DateTimeTZ,
                         default=datetime.utcnow,
                         onupdate=datetime.utcnow)


class TrackIPMixin(object):
    # For reasoning around the column length, consult stackoverflow.com:
    #   /questions/1076714/max-length-for-client-ip-address
    remote_ip = db.Column(postgresql.CIDR, default=remote_ip, onupdate=remote_ip)
