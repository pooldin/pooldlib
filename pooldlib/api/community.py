"""
pooldlib.api.community
===============================

.. currentmodule:: pooldlib.api.community

"""
import pytz
from datetime import datetime

from sqlalchemy.exc import DataError as SQLAlchemyDataError

from pooldlib.sqlalchemy import transaction_session
from pooldlib.postgresql import (Community as CommunityModel,
                                 CommunityGoal as CommunityGoalModel,
                                 CommunityGoalMeta as CommunityGoalMetaModel,
                                 CommunityAssociation as CommunityAssociationModel)
from pooldlib.api import user
from pooldlib.exceptions import (UnknownUserError,
                                 UnknownCommunityError,
                                 InvalidUserRoleError)


# TODO :: Enable pagination
def communities(community_ids, filter_inactive=True):
    """Return all communities with ids in ``community_ids``. If ``filter_inactive``
    is `True`, return only those whos `start` and `endtime` make it currently active.
    If ``community_ids`` is `None`, return all communities.

    :param community_ids: List of community IDs to return. Pass `None`` to return
                          **all** communities.
    :type community_id: list of ``long``s.
    :param filter_inactive: Return communities only if they are currently active,
                            that is if the current datetime is not outside of
                            the community's start and end times. Default `False`.
    :type filter_inactive: boolean

    :returns: list of :class:`pooldlib.postgresql.models.Communitiy`
    """
    if community_ids and not isinstance(community_ids, (list, tuple)):
        community_ids = [community_ids]

    q = CommunityModel.query.filter_by(enabled=True)
    if community_ids:
        q = q.filter(CommunityModel.id.in_(community_ids))
    if filter_inactive:
        now = pytz.UTC.localize(datetime.utcnow())
        q = q.filter(CommunityModel.start <= now)\
             .filter(CommunityModel.end > now)
    community = q.all()
    return community


def get(community_id, filter_inactive=False):
    """Return a community from the database based on it's long integer id.
    If no community is found ``NoneType`` is returned.

    :param community_id: Identifier for the target community.
    :type user_id: :class:`pooldlib.postgresql.models.User`, string or long
    :param filter_inactive: Return the community if it is currently active,
                            that is if the current datetime is not outside of
                            the community's start and end times. Default `False`.
    :type filter_inactive: boolean

    :raises: ArgumentError

    :returns: :class:`pooldlib.postgresql.models.User` or ``NoneType``
    """
    if isinstance(community_id, CommunityModel):
        if not community_id.enabled:
            return None
        return community_id

    if not isinstance(community_id, (int, long)):
        raise TypeError('Community id must be of type long.')

    q = CommunityModel.query.filter_by(id=community_id)\
                            .filter_by(enabled=True)
    if filter_inactive:
        now = pytz.UTC.localize(datetime.utcnow())
        q = q.filter(CommunityModel.start <= now)\
             .filter(CommunityModel.end >= now)
    community = q.first()
    return community or None


def create(organizer, name, description, start=None, end=None):
    """Create and return a new instance of
    :class:`pooldlib.postgresql.models.Community`.

    :param origanizer: The user to be classified as the community's
                       organizing member.
    :type origanizer: :class:`pooldlib.postgresql.models.User`, string or long
    :param name: The name of the community
    :type name: string
    :param descriptin: The descriptin of the community
    :type descriptin: string

    :raises: :class:`pooldlib.exceptions.UnknownUserError`

    :returns: :class:`pooldlib.postgresql.models.Community`
    """
    organizer = user.get(organizer)
    if not organizer:
        raise UnknownUserError()

    c = CommunityModel()
    c.name = name
    c.description = description
    c.start = start or pytz.UTC.localize(datetime.utcnow())
    c.end = end

    with transaction_session() as session:
        session.add(c)
        session.commit()

    associate_user(c, organizer, 'organizer')
    return c


def update(community, name=None, descriptin=None):
    """
    """
    pass


def disable(community):
    """
    """
    pass


def associate_user(community, community_user, role):
    """Associate a user with a community filling a specified role.

    :param community: The community with which to associate the user.
    :type community: long or :class:`pooldlib.postgresql.models.Community`
    :param community_user: The user for which to create the association.
    :type community_user: long, string (username or email) or
                          :class:`pooldlib.postgresql.models.User`
    :param role: The role to assign the user (either `organizer` or `participant`)
    :type role: string

    :raises: :class:`pooldlib.exceptions.UnknownUserError`
             :class:`pooldlib.exceptions.UnknownCommunityError`
             :class:`pooldlib.exceptions.InvalidUserRoleError`

    :return: :class:`pooldlib.postgresql.models.CommunityAssociation`
    """
    community = get(community)
    if community is None:
        raise UnknownCommunityError()
    community_user = user.get(community_user)
    if not community_user:
        raise UnknownUserError()
    ca = CommunityAssociationModel()
    ca.enabled = True
    ca.community = community
    ca.user = community_user
    ca.role = role

    with transaction_session() as session:
        session.add(ca)
        try:
            session.commit()
        except SQLAlchemyDataError:
            raise InvalidUserRoleError()
    return ca


def associate_users(community, users, role):
    """
    """


def disassociate_users(community, users):
    """
    """
    pass


def update_user_role(community, user, role):
    """
    """
    pass


# TODO :: Enable pagination
def transfers(community, direction, goal, currency=None, other_party=None):
    """
    """
    pass


def goal(community, goal_id):
    """
    """
    pass


# TODO :: Enable pagination
def goals(community):
    """
    """
    pass


def add_goal(community, name, descriptin, **kwargs):
    """
    """
    pass


def update_goal(community, goal, name=None, descriptin=None, **kwargs):
    """
    """
    pass
