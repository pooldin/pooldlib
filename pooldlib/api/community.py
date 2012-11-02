"""
pooldlib.api.community
===============================

.. currentmodule:: pooldlib.api.community

"""
import pytz
from datetime import datetime

from sqlalchemy.exc import (DataError as SQLAlchemyDataError,
                            IntegrityError as SQLAlchemyIntegrityError)

from pooldlib.sqlalchemy import transaction_session
from pooldlib.postgresql import (Community as CommunityModel,
                                 CommunityGoal as CommunityGoalModel,
                                 CommunityGoalMeta as CommunityGoalMetaModel,
                                 CommunityAssociation as CommunityAssociationModel,
                                 CommunityGoalAssociation as CommunityGoalAssociationModel)
from pooldlib.api import balance as _balance
from pooldlib.exceptions import (InvalidUserRoleError,
                                 InvalidGoalParticipationNameError,
                                 UnknownCommunityAssociationError,
                                 DuplicateCommunityUserAssociationError,
                                 DuplicateCommunityGoalUserAssociationError)


# TODO :: Enable pagination
def communities(community_ids, filter_inactive=True):
    """Return all communities with ids in ``community_ids``. If ``filter_inactive``
    is `True`, return only those whos `start` and `endtime` make it currently active.
    If ``community_ids`` is `None`, return all communities.

    :param community_ids: List of community IDs to return. Pass `None` to return
                          **all** communities.
    :type community_id: list of type `long`.
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
    :type community_id: :class:`pooldlib.postgresql.models.Community`, string or long
    :param filter_inactive: Return the community if it is currently active,
                            that is if the current datetime is not outside of
                            the community's start and end times. Default `False`.
    :type filter_inactive: boolean

    :returns: :class:`pooldlib.postgresql.models.User` or ``NoneType``
    """
    if community_id is None:
        return None

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


def organizer(community):
    """Return the user whose association with the given community as
    it's organizer. If none is found, `None` is returned.

    :param community: Community for which to retrieve the organizer.
    :type community: :class:`pooldlib.postgresql.models.Community`

    :returns: :class:`pooldlib.postgresql.models.User` or None
    """
    org_association = CommunityAssociationModel.query.filter_by(community_id=community.id)\
                                                     .filter_by(role='organizer')\
                                                     .first()
    if org_association is None:
        return None
    return org_association.user


def create(organizer, name, description, start=None, end=None):
    """Create and return a new instance of
    :class:`pooldlib.postgresql.models.Community`.

    :param origanizer: The user to be classified as the community's organizing
                       member.
    :type origanizer: :class:`pooldlib.postgresql.models.User`
    :param name: The name of the community
    :type name: string
    :param description: The description of the community
    :type description: string
    :param start: Active start datetime for the community in UTC, defaults
                  to `datetime.utcnow`
    :type start: :class:`datetime.datetime`
    :param end: Active end datetime for the community in UTC, optional
    :type end: :class:`datetime.datetime` or `None`

    :returns: :class:`pooldlib.postgresql.models.Community`
    """
    community = CommunityModel()
    community.name = name
    community.description = description
    community.start = start or pytz.UTC.localize(datetime.utcnow())
    community.end = end

    with transaction_session() as session:
        session.add(community)
        session.commit()

    associate_user(community, organizer, 'organizer', 'participating')
    return community


def update(community, name=None, description=None):
    """Update name and description of a specified community.

    :param community: Community to update.
    :type community: :class:`pooldlib.postgresql.models.Community`
    :param name: If specified, the new name for the community.
    :type name: string
    :param name: If specified, the new description for the community.
    :type name: string

    :returns: :class:`pooldlib.postgresql.models.Community`
    """
    if name is not None:
        community.name = name
    if description is not None:
        community.description = description

    with transaction_session() as session:
        session.add(community)
        session.commit()
    return community


def disable(community):
    """Disable a specified community. This will prevent it from being returned
    by calls to :func:`pooldlib.api.community.get` and
    :func:`pooldlib.api.community.communities`

    :param community: The community to disable.
    :type community: :class:`pooldlib.postgresql.models.Community`
    """
    community.enabled = False
    with transaction_session() as session:
        session.add(community)
        session.commit()


def balances(community):
    """Retrieve all balances for a community.

    :param community: Community for which to retrieve balances.
    :type community: :class:`pooldlib.postgresql.models.Community`

    :returns: list of :class:`pooldlib.postgresql.models.Balance` objects
    """
    return community.balances


def balance(community, currency, get_or_create=False, for_update=False):
    """Return a communities balance for ``currency``, if ``get_or_create=True``, if
    an existing balance isn't found, one will be created and returned.

    :param community: Community for which to retrieve balance.
    :type community: :class:`pooldlib.postgresql.models.Community`
    :param currency: Currenty type of the balance to retrieve
    :type currency::class: `pooldlib.postgresql.models.Currency`
    :param get_or_create: If `True` and an existing balance is not found
                          one will be created for ``currency``.
    :type get_or_create: boolean
    :param for_update: If `True`, the ``SELECT FOR UPDATE`` directive will be
                       used when retrieving the target balance.
    :type for_update: boolean

    :returns: :class:`pooldlib.postgresql.models.Balance`
    """
    b = _balance.get(for_update=for_update,
                     currency_id=currency.id,
                     type='community',
                     community_id=community.id)
    if not b and get_or_create:
        b = _balance.create_for_community(community, currency)

    if isinstance(b, (tuple, list)):
        b = b[0]
    return b or None


def associate_user(community, user, role, goal_participation):
    """Associate a user with a community filling a specified role.

    :param community: The community with which to associate the user.
    :type community: :class:`pooldlib.postgresql.models.Community`
    :param user: The user for which to create the association.
    :type user: :class:`pooldlib.postgresql.models.User`
    :param role: The role to assign the user (either `organizer` or `participant`)
    :type role: string
    :param goal_participation: The participation description for the communities goals.
                               One of `participating`, `nonparticipating`, `opted-in` or `opted-out`
                               (See :func:`pooldlib.api.community.associate_user_with_goal`)
    :type goal_participation: string

    :raises: :class:`pooldlib.exceptions.InvalidUserRoleError`
             :class:`pooldlib.exceptions.DuplicateCommunityUserAssociationError`

    :return: :class:`pooldlib.postgresql.models.CommunityAssociation`
    """
    # NOTE :: We intentionally associate the user with all existing goals, not just
    # NOTE :: active ones. Date stamps can distinguish users who joined prior to goal
    # NOTE :: becoming inactive.
    community_goals = goals(community, filter_inactive=False)
    ca = CommunityAssociationModel()
    ca.enabled = True
    ca.community = community
    ca.user = user
    ca.role = role
    for goal in community_goals:
        associate_user_with_goal(goal, user, goal_participation)

    with transaction_session() as session:
        session.add(ca)
        try:
            session.commit()
        except SQLAlchemyDataError:
            raise InvalidUserRoleError()
        except SQLAlchemyIntegrityError:
            raise DuplicateCommunityUserAssociationError()
    return ca


def get_associations(community, user=None):
    """Retrieve all :class:`pooldlib.postgresql.models.CommunityAssociation`
    objects associated with the specified community. If ``user`` is not `None`,
    return only the association corresponding to that specific user.

    :param community: The community for which to retrieve associations.
    :type community: :class:`pooldlib.postgresql.models.Community`
    :param user: The user for which to retrieve the association.
    :type user: :class:`pooldlib.postgresql.models.User`

    :return: list of :class:`pooldlib.postgresql.models.CommunityAssociation`
    """
    q = CommunityAssociationModel.query.filter_by(enabled=True)\
                                       .filter(CommunityAssociationModel.community_id == community.id)
    if user is not None:
        q = q.filter(CommunityAssociationModel.user_id == user.id)

    return q.all()


def update_user_association(community, user, role):
    """Update an existing User/Community association to change the
    specified user's role in the community.

    :param community: The community to which the user is associated.
    :type community: :class:`pooldlib.postgresql.models.Community`
    :param user: The user for which to update a community association.
    :type user: :class:`pooldlib.postgresql.models.User`
    :param role: The role to assign the user (either `organizer` or `participant`)
    :type role: string

    :raises: :class:`pooldlib.exceptions.InvalidUserRoleError`
             :class:`pooldlib.exceptions.UnknownCommunityAssociationError`

    :return: :class:`pooldlib.postgresql.models.CommunityAssociation`
    """
    ca = get_associations(community, user=user)
    if not ca:
        msg = "User %s is not associated with community %s. Please create "\
              "one with community.associate_user()."
        raise UnknownCommunityAssociationError(msg)
    ca = ca[0]
    if ca.update_field('role', role):
        with transaction_session() as session:
            try:
                session.commit()
            except SQLAlchemyIntegrityError:
                raise InvalidUserRoleError()


def disassociate_user(community, user):
    """Remove the association between a User and a Community.

    :param community: The community to which the user is associated.
    :type community: :class:`pooldlib.postgresql.models.Community`
    :param user: The user for which to remove a community association.
    :type user: :class:`pooldlib.postgresql.models.User`

    :raises: :class:`pooldlib.exceptions.UnknownCommunityAssociationError`

    :return: :class:`pooldlib.postgresql.models.CommunityAssociation`
    """
    ca = get_associations(community, user=user)
    if not ca:
        msg = "User %s is not associated with community %s. Please create "\
              "one with community.associate_user()."
        raise UnknownCommunityAssociationError(msg)
    ca = ca[0]
    with transaction_session() as session:
        session.delete(ca)
        session.commit()


# TODO :: Enable pagination
def transfers(community, direction, goal, currency=None, other_party=None):
    """
    """
    pass


# TODO :: Enable pagination
def goals(community, goal_ids=None, filter_inactive=True):
    """Return all goals associated with a community. If ``goal_ids`` is specified,
    return only those goal objects. If ``filter_inactive`` is `True`, return only
    those whose `start` and `endtime` make it currently active.

    :param community: The community for which to retrieve goals.
    :type community_id: :class:`pooldlib.postgresql.models.Community`
    :param goal_ids: List of goal ids.
    :type goal_ids: list of longs.
    :param filter_inactive: Return goals only if they are currently active,
                            that is if the current datetime is not outside of
                            the community's start and end times. Default `False`.
    :type filter_inactive: boolean

    :returns: list of :class:`pooldlib.postgresql.models.Communitiy`
    """
    if goal_ids and not isinstance(goal_ids, (list, tuple)):
        goal_ids = [goal_ids]

    q = CommunityGoalModel.query.filter_by(enabled=True)\
                                .filter_by(community_id=community.id)
    if goal_ids:
        q = q.filter(CommunityGoalModel.id.in_(goal_ids))
    if filter_inactive:
        now = pytz.UTC.localize(datetime.utcnow())
        q = q.filter(CommunityGoalModel.start <= now)\
             .filter(CommunityGoalModel.end > now)
    goals = q.all()
    return goals


def goal(goal_id, community=None, filter_inactive=False):
    """Return a goal from the database based on it's long integer id.
    If no community is found ``NoneType`` is returned.

    :param goal_id: Identifier for the target community goal.
    :type goal_id: long
    :param community: The community goal to which the desired goal belongs.
    :type community: :class:`pooldlib.postgresql.models.Community`
    :param filter_inactive: If `True`, only return goal if it's start and
                            end times indicate that it is currently active.
    """
    if goal_id is None:
        return None

    q = CommunityGoalModel.query.filter_by(id=goal_id)\
                                .filter_by(enabled=True)
    if community is not None:
        q = q.filter_by(community=community)

    if filter_inactive:
        now = pytz.UTC.localize(datetime.utcnow())
        q = q.filter(CommunityGoalModel.start <= now)\
             .filter(CommunityGoalModel.end >= now)
    goal = q.first()
    return goal or None


def add_goal(community, name, description, type, start=None, end=None, **kwargs):
    """Add a goal to an existing community. ``name`` and ``description``
    are required.  Any key-value pair will be assumed to be metadata to be
    added to the goal instance.

    :param community: The community goal which the add a new goal.
    :type community: :class:`pooldlib.postgresql.models.Community`
    :param name: The name of the newly created community goal.
    :type name: string
    :param description: The description of the newly created community goal.
    :type description: string
    :param type: The type of goal to add (fund-raiser, project or group-purchase)
    :type type: string
    :param start: Active start datetime for the community in UTC, defaults to `datetime.utcnow`
    :type start: :class:`datetime.datetime`
    :param end: Active end datetime for the community in UTC, optional
    :type end: :class:`datetime.datetime` or `None`
    :param kwargs: Keyword arguments consisting of key-value pairs to be added to the
                   newly created goal as metadata.
    :type kwargs: unspecified keyword arguments to the function.

    :returns: :class:`pooldlib.postgresql.models.CommunitiyGoal`
    """
    goal = CommunityGoalModel()
    goal.name = name
    goal.description = description
    goal.start = start or pytz.UTC.localize(datetime.utcnow())
    goal.end = end
    goal.type = type
    community.goals.append(goal)

    with transaction_session() as session:
        session.add(goal)
        session.commit()

    meta = list()
    for (k, v) in kwargs.items():
        goal_meta = CommunityGoalMetaModel()
        goal_meta.key = k
        goal_meta.value = v
        goal_meta.community_goal = goal
        meta.append(goal_meta)

    with transaction_session(auto_commit=True) as session:
        for goal_meta in meta:
            session.add(goal_meta)
    return goal


def update_goal(update_goal, name=None, description=None, start=None, end=None, **kwargs):
    """Update an existing goal for a community. Only ``goal`` is required. All
    given goal properties will be updated. Any unspecified keyword arguments will
    be used to update the goal's metadata. To delete metadata for a community goal,
    pass ``None`` as the value for the to be deleted key in the kwarg key-value pair.

    :param update_goal: Identifier for the target community.
    :type update_goal: :class:`pooldlib.postgresql.models.Goal`
    :param name: The name of the newly created community goal.
    :type name: string
    :param description: The description of the newly created community goal.
    :type name: string
    :param kwargs: Keyword arguments consisting of key-value pairs to be added to the
                   newly created goal as metadata.
    :type kwargs: unspecified keyword arguments to the function.
    """
    if name is not None:
        update_goal.name = name
    if description is not None:
        update_goal.description = description
    if start is not None:
        update_goal.start = start
    if end is not None:
        update_goal.end = end

    update_meta = [m for m in update_goal.metadata if m.key in kwargs]
    create_meta = [(k, v) for (k, v) in kwargs.items() if not hasattr(update_goal, k)]

    meta_delta = list()
    meta_remove = list()
    for goal_meta in update_meta:
        value = kwargs[m.key]
        if value is None:
            meta_remove.append(goal_meta)
        else:
            goal_meta.value = value
            meta_delta.append(goal_meta)

    for (k, v) in create_meta:
        goal_meta = CommunityGoalMetaModel()
        goal_meta.key = k
        goal_meta.value = v
        goal_meta.community_goal = update_goal
        meta_delta.append(goal_meta)

    with transaction_session() as session:
        session.add(update_goal)  # Technically not needed
        session.flush()

        for goal_meta in meta_delta:
            session.add(goal_meta)
        for goal_meta in meta_remove:
            session.delete(goal_meta)

        session.commit()

    return update_goal


def disable_goal(disable_goal):
    """Disable a specific instance of the CommunityGoal data model. This will prevent
    the user from being returned by calls to :func:`pooldlib.api.user.get`
    and any further updates to the user being allowed.

    :param user: User which to disable.
    :type user: :class:`pooldlib.postgresql.models.User` or user identifier
    """
    disable_goal.update_field('enabled', False)
    with transaction_session(auto_commit=True) as session:
        session.add(disable_goal)


def associate_user_with_goal(community_goal, user, participation):
    """Associate given user with ``community_goal``. The association will be described by
    ``participation``, which can be one of 'opted-in', 'opted-out', 'participating',
    'nonparticipating'. The values 'participating' and 'nonparticipating' should only be used
    for default participation descriptions.  If a use opts to change their participation, use
    appropriate descriptor of 'opted-in' or 'opted-out'. These rules should be followed precisely
    for reporting purposes.

    :raises: :class:`pooldlib.exceptions.InvalidGoalParticipationNameError`
             :class:`pooldlib.exceptions.DuplicateCommunityGoalUserAssociationError`
    """
    cga = CommunityGoalAssociationModel()
    cga.community_id = community_goal.community.id
    cga.community_goal = community_goal
    cga.user = user
    cga.participation = participation

    with transaction_session() as session:
        session.add(cga)
        try:
            session.commit()
        except SQLAlchemyDataError:
            raise InvalidGoalParticipationNameError()
        except SQLAlchemyIntegrityError:
            raise DuplicateCommunityGoalUserAssociationError()
    return cga


def update_user_goal_association(community_goal, user, participation):
    """Update a given user's association with ``community_goal``. The association will be
    described by ``participation``, which can be one of 'opted-in' and 'opted-out', 'participating',
    'nonparticipating'. The values 'participating' and 'nonparticipating' should only be used
    for default participation descriptions.  If a use opts to change their participation, use
    appropriate descriptor of 'opted-in' or 'opted-out'. These rules should be followed precisely
    for reporting purposes.

    :raises: :class:`pooldlib.exceptions.InvalidGoalParticipationNameError`
    """
    cga = CommunityGoalAssociationModel.query.filter_by(community=community_goal.community)\
                                             .filter_by(community_goal=community_goal)\
                                             .filter_by(user=user)\
                                             .first()

    if cga.update_field(participation=participation):
        with transaction_session() as session:
            session.add(cga)
            try:
                session.commit()
            except SQLAlchemyDataError:
                raise InvalidGoalParticipationNameError()
    return cga
