"""
pooldlib.api.campaign
===============================

.. currentmodule:: pooldlib.api.campaign

"""
import pytz
from datetime import datetime

from sqlalchemy.exc import (DataError as SQLAlchemyDataError,
                            IntegrityError as SQLAlchemyIntegrityError)

from pooldlib.sqlalchemy import transaction_session
from pooldlib.postgresql import (Campaign as CampaignModel,
                                 Invitee as InviteeModel,
                                 CampaignGoal as CampaignGoalModel,
                                 CampaignMeta as CampaignMetaModel,
                                 CampaignGoalMeta as CampaignGoalMetaModel,
                                 CampaignAssociation as CampaignAssociationModel,
                                 CampaignGoalAssociation as CampaignGoalAssociationModel)
from pooldlib.api import balance as _balance
from pooldlib.exceptions import (InvalidUserRoleError,
                                 InvalidGoalParticipationNameError,
                                 UnknownCampaignAssociationError,
                                 DuplicateCampaignUserAssociationError,
                                 DuplicateCampaignGoalUserAssociationError)


# TODO :: Enable pagination
def campaigns(campaign_ids, filter_inactive=True):
    """Return all campaigns with ids in ``campaign_ids``. If ``filter_inactive``
    is `True`, return only those whos `start` and `endtime` make it currently active.
    If ``campaign_ids`` is `None`, return all campaigns.

    :param campaign_ids: List of campaign IDs to return. Pass `None` to return
                          **all** campaigns.
    :type campaign_id: list of type `long`.
    :param filter_inactive: Return campaigns only if they are currently active,
                            that is if the current datetime is not outside of
                            the campaign's start and end times. Default `False`.
    :type filter_inactive: boolean

    :returns: list of :class:`pooldlib.postgresql.models.Communitiy`
    """
    if campaign_ids and not isinstance(campaign_ids, (list, tuple)):
        campaign_ids = [campaign_ids]

    q = CampaignModel.query.filter_by(enabled=True)
    if campaign_ids:
        q = q.filter(CampaignModel.id.in_(campaign_ids))
    if filter_inactive:
        now = pytz.UTC.localize(datetime.utcnow())
        q = q.filter(CampaignModel.start <= now)\
             .filter(CampaignModel.end > now)
    campaign = q.all()
    return campaign


def get(campaign_id, filter_inactive=False):
    """Return a campaign from the database based on it's long integer id.
    If no campaign is found ``NoneType`` is returned.

    :param campaign_id: Identifier for the target campaign.
    :type campaign_id: :class:`pooldlib.postgresql.models.Campaign`, string or long
    :param filter_inactive: Return the campaign if it is currently active,
                            that is if the current datetime is not outside of
                            the campaign's start and end times. Default `False`.
    :type filter_inactive: boolean

    :returns: :class:`pooldlib.postgresql.models.User` or ``NoneType``
    """
    if campaign_id is None:
        return None

    if isinstance(campaign_id, CampaignModel):
        if not campaign_id.enabled:
            return None
        return campaign_id

    if not isinstance(campaign_id, (int, long)):
        raise TypeError('Campaign id must be of type long.')

    q = CampaignModel.query.filter_by(id=campaign_id)\
                           .filter_by(enabled=True)
    if filter_inactive:
        now = pytz.UTC.localize(datetime.utcnow())
        q = q.filter(CampaignModel.start <= now)\
             .filter(CampaignModel.end >= now)
    campaign = q.first()
    return campaign or None


def organizer(campaign):
    """Return the user whose association with the given campaign as
    it's organizer. If none is found, `None` is returned.

    :param campaign: Campaign for which to retrieve the organizer.
    :type campaign: :class:`pooldlib.postgresql.models.Campaign`

    :returns: :class:`pooldlib.postgresql.models.User` or None
    """
    org_association = CampaignAssociationModel.query.filter_by(campaign_id=campaign.id)\
                                                    .filter_by(role='organizer')\
                                                    .first()
    if org_association is None:
        return None
    return org_association.user


def create(organizer, name, description, start=None, end=None, **kwargs):
    """Create and return a new instance of
    :class:`pooldlib.postgresql.models.Campaign`.

    :param origanizer: The user to be classified as the campaign's organizing
                       member.
    :type origanizer: :class:`pooldlib.postgresql.models.User`
    :param name: The name of the campaign
    :type name: string
    :param description: The description of the campaign
    :type description: string
    :param start: Active start datetime for the campaign in UTC, defaults
                  to `datetime.utcnow`
    :type start: :class:`datetime.datetime`
    :param end: Active end datetime for the campaign in UTC, optional
    :type end: :class:`datetime.datetime` or `None`
    :param kwargs: Metadata to associate with the new campaign.
    :type kwargs: kwarg dictionary

    :returns: :class:`pooldlib.postgresql.models.Campaign`
    """
    campaign = CampaignModel()
    campaign.name = name
    campaign.description = description
    campaign.start = start or pytz.UTC.localize(datetime.utcnow())
    campaign.end = end

    with transaction_session() as session:
        session.add(campaign)
        session.commit()

    meta = list()
    for (k, v) in kwargs.items():
        cm = CampaignMetaModel()
        cm.key = k
        cm.value = v
        cm.campaign_id = campaign.id
        meta.append(cm)

    with transaction_session(auto_commit=True) as session:
        for cm in meta:
            session.add(cm)

    associate_user(campaign, organizer, 'organizer', 'participating')
    return campaign


def update(campaign, name=None, description=None, **kwargs):
    """Update name and description of a specified campaign.

    :param campaign: Campaign to update.
    :type campaign: :class:`pooldlib.postgresql.models.Campaign`
    :param name: If specified, the new name for the campaign.
    :type name: string
    :param name: If specified, the new description for the campaign.
    :type name: string
    :param kwargs: key-value pairs to associate with the `User` data model
                   instance as metadata.
    :type kwargs: kwarg dictionary

    :returns: :class:`pooldlib.postgresql.models.Campaign`
    """
    if name is not None:
        campaign.name = name
    if description is not None:
        campaign.description = description

    # TODO :: This is really inefficient, fix it. <brian@poold.in>
    # TODO :: This methodology is mirrored in the user API as well.
    update_meta = [m for m in campaign.metadata if m.key in kwargs]
    create_meta = [(k, v) for (k, v) in kwargs.items() if not hasattr(campaign, k)]

    meta_delta = list()
    meta_remove = list()
    for campaign_meta in update_meta:
        value = kwargs[campaign_meta.key]
        if value is None:
            meta_remove.append(campaign_meta)
        else:
            campaign_meta.value = value
            meta_delta.append(campaign_meta)

    for (k, v) in create_meta:
        m = CampaignMetaModel()
        m.key = k
        m.value = v
        m.campaign_id = campaign.id
        meta_delta.append(m)

    with transaction_session() as session:
        session.add(campaign)
        session.commit()

        for m in meta_delta:
            session.add(m)
            session.flush()
        for m in meta_remove:
            session.delete(m)

        session.commit()

    return campaign


def disable(campaign):
    """Disable a specified campaign. This will prevent it from being returned
    by calls to :func:`pooldlib.api.campaign.get` and
    :func:`pooldlib.api.campaign.campaigns`

    :param campaign: The campaign to disable.
    :type campaign: :class:`pooldlib.postgresql.models.Campaign`
    """
    campaign.enabled = False
    with transaction_session() as session:
        session.add(campaign)
        session.commit()


def balances(campaign):
    """Retrieve all balances for a campaign.

    :param campaign: Campaign for which to retrieve balances.
    :type campaign: :class:`pooldlib.postgresql.models.Campaign`

    :returns: list of :class:`pooldlib.postgresql.models.Balance` objects
    """
    return campaign.balances


def balance(campaign, currency, get_or_create=False, for_update=False):
    """Return a campaigns balance for ``currency``, if ``get_or_create=True``, if
    an existing balance isn't found, one will be created and returned.

    :param campaign: Campaign for which to retrieve balance.
    :type campaign: :class:`pooldlib.postgresql.models.Campaign`
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
                     type='campaign',
                     campaign_id=campaign.id)
    if not b and get_or_create:
        b = _balance.create_for_campaign(campaign, currency)

    if isinstance(b, (tuple, list)):
        b = b[0]
    return b or None


def add_invites(campaign, emails):
    invites = list()
    for email in emails:
        i = add_invite(campaign, email)
        if i is not None:
            invites.append(i)
    return invites


def add_invite(campaign, email):
    from pooldlib.api import user
    usr = user.get_by_email(email)

    q = InviteeModel.query.filter_by(campaign_id=campaign.id)
    if usr is not None:
        q = q.filter_by(user_id=usr.id)
    else:
        q = q.filter_by(email=email)
    existing_invite = q.first()
    if existing_invite is not None:
        return None

    invite = InviteeModel()
    invite.email = email
    invite.campaign_id = campaign.id
    if usr is not None:
        invite.user_id = usr.id

    with transaction_session() as session:
        session.add(invite)
        session.commit()
    return invite


def associate_user(campaign, user, role, goal_participation, pledge=None):
    """Associate a user with a campaign filling a specified role.

    :param campaign: The campaign with which to associate the user.
    :type campaign: :class:`pooldlib.postgresql.models.Campaign`
    :param user: The user for which to create the association.
    :type user: :class:`pooldlib.postgresql.models.User`
    :param role: The role to assign the user (either `organizer` or `participant`)
    :type role: string
    :param goal_participation: The participation description for the campaign goals.
                               One of `participating`, `nonparticipating`, `opted-in` or `opted-out`
                               (See :func:`pooldlib.api.campaign.associate_user_with_goal`)
    :type goal_participation: string

    :raises: :class:`pooldlib.exceptions.InvalidUserRoleError`
             :class:`pooldlib.exceptions.DuplicateCampaignUserAssociationError`

    :return: :class:`pooldlib.postgresql.models.CampaignAssociation`
    """
    # NOTE :: We intentionally associate the user with all existing goals, not just
    # NOTE :: active ones. Date stamps can distinguish users who joined prior to goal
    # NOTE :: becoming inactive.
    campaign_goals = goals(campaign, filter_inactive=False)
    ca = CampaignAssociationModel()
    ca.enabled = True
    ca.campaign = campaign
    ca.user = user
    ca.role = role
    goal_pledge = None
    if pledge is not None:
        ca.pledge = pledge
        if campaign_goals:
            goal_pledge = pledge / len(campaign_goals)
    for goal in campaign_goals:
        associate_user_with_goal(goal, user, goal_participation, pledge=goal_pledge)

    # Check to see if this user was invited and mark them as accepted
    update_invitee = None
    for invitee in campaign.invitees:
        if invitee.user == user or invitee.email == user.email:
            invitee.accepted = pytz.UTC.localize(datetime.utcnow())
            invitee.user = user
            update_invitee = invitee

    with transaction_session() as session:
        session.add(ca)
        if update_invitee is not None:
            session.add(update_invitee)
        try:
            session.commit()
        except SQLAlchemyDataError:
            raise InvalidUserRoleError()
        except SQLAlchemyIntegrityError:
            raise DuplicateCampaignUserAssociationError()
    return ca


def get_associations(campaign, user=None):
    """Retrieve all :class:`pooldlib.postgresql.models.CampaignAssociation`
    objects associated with the specified campaign. If ``user`` is not `None`,
    return only the association corresponding to that specific user.

    :param campaign: The campaign for which to retrieve associations.
    :type campaign: :class:`pooldlib.postgresql.models.Campaign`
    :param user: The user for which to retrieve the association.
    :type user: :class:`pooldlib.postgresql.models.User`

    :return: list of :class:`pooldlib.postgresql.models.CampaignAssociation`
    """
    q = CampaignAssociationModel.query.filter_by(enabled=True)\
                                      .filter(CampaignAssociationModel.campaign_id == campaign.id)
    if user is not None:
        q = q.filter(CampaignAssociationModel.user_id == user.id)

    return q.all()


def update_user_association(campaign, user, role):
    """Update an existing User/Campaign association to change the
    specified user's role in the campaign.

    :param campaign: The campaign to which the user is associated.
    :type campaign: :class:`pooldlib.postgresql.models.Campaign`
    :param user: The user for which to update a campaign association.
    :type user: :class:`pooldlib.postgresql.models.User`
    :param role: The role to assign the user (either `organizer` or `participant`)
    :type role: string

    :raises: :class:`pooldlib.exceptions.InvalidUserRoleError`
             :class:`pooldlib.exceptions.UnknownCampaignAssociationError`

    :return: :class:`pooldlib.postgresql.models.CampaignAssociation`
    """
    ca = get_associations(campaign, user=user)
    if not ca:
        msg = "User %s is not associated with campaign %s. Please create "\
              "one with campaign.associate_user()."
        raise UnknownCampaignAssociationError(msg)
    ca = ca[0]
    if ca.update_field('role', role):
        with transaction_session() as session:
            try:
                session.commit()
            except SQLAlchemyIntegrityError:
                raise InvalidUserRoleError()


def disassociate_user(campaign, user):
    """Remove the association between a User and a Campaign.

    :param campaign: The campaign to which the user is associated.
    :type campaign: :class:`pooldlib.postgresql.models.Campaign`
    :param user: The user for which to remove a campaign association.
    :type user: :class:`pooldlib.postgresql.models.User`

    :raises: :class:`pooldlib.exceptions.UnknownCampaignAssociationError`

    :return: :class:`pooldlib.postgresql.models.CampaignAssociation`
    """
    ca = get_associations(campaign, user=user)
    if not ca:
        msg = "User %s is not associated with campaign %s. Please create "\
              "one with campaign.associate_user()."
        raise UnknownCampaignAssociationError(msg)
    ca = ca[0]
    with transaction_session() as session:
        session.delete(ca)
        session.commit()


# TODO :: Enable pagination
def transfers(campaign, direction, goal, currency=None, other_party=None):
    """
    """
    pass


# TODO :: Enable pagination
def goals(campaign, goal_ids=None, filter_inactive=True):
    """Return all goals associated with a campaign. If ``goal_ids`` is specified,
    return only those goal objects. If ``filter_inactive`` is `True`, return only
    those whose `start` and `endtime` make it currently active.

    :param campaign: The campaign for which to retrieve goals.
    :type campaign_id: :class:`pooldlib.postgresql.models.Campaign`
    :param goal_ids: List of goal ids.
    :type goal_ids: list of longs.
    :param filter_inactive: Return goals only if they are currently active,
                            that is if the current datetime is not outside of
                            the campaign's start and end times. Default `False`.
    :type filter_inactive: boolean

    :returns: list of :class:`pooldlib.postgresql.models.Communitiy`
    """
    if goal_ids and not isinstance(goal_ids, (list, tuple)):
        goal_ids = [goal_ids]

    q = CampaignGoalModel.query.filter_by(enabled=True)\
                               .filter_by(campaign_id=campaign.id)
    if goal_ids:
        q = q.filter(CampaignGoalModel.id.in_(goal_ids))
    if filter_inactive:
        now = pytz.UTC.localize(datetime.utcnow())
        q = q.filter(CampaignGoalModel.start <= now)\
             .filter(CampaignGoalModel.end > now)
    goals = q.all()
    return goals


def goal(goal_id, campaign=None, filter_inactive=False):
    """Return a goal from the database based on it's long integer id.
    If no campaign is found ``NoneType`` is returned.

    :param goal_id: Identifier for the target campaign goal.
    :type goal_id: long
    :param campaign: The campaign goal to which the desired goal belongs.
    :type campaign: :class:`pooldlib.postgresql.models.Campaign`
    :param filter_inactive: If `True`, only return goal if it's start and
                            end times indicate that it is currently active.
    """
    if goal_id is None:
        return None

    q = CampaignGoalModel.query.filter_by(id=goal_id)\
                               .filter_by(enabled=True)
    if campaign is not None:
        q = q.filter_by(campaign=campaign)

    if filter_inactive:
        now = pytz.UTC.localize(datetime.utcnow())
        q = q.filter(CampaignGoalModel.start <= now)\
             .filter(CampaignGoalModel.end >= now)
    goal = q.first()
    return goal or None


def add_goal(campaign, name, description, type, predecessor=None, start=None, end=None, **kwargs):
    """Add a goal to an existing campaign. ``name`` and ``description``
    are required.  Any key-value pair will be assumed to be metadata to be
    added to the goal instance.

    :param campaign: The campaign goal which the add a new goal.
    :type campaign: :class:`pooldlib.postgresql.models.Campaign`
    :param name: The name of the newly created campaign goal.
    :type name: string
    :param description: The description of the newly created campaign goal.
    :type description: string
    :param type: The type of goal to add (fund-raiser, project or group-purchase)
    :type type: string
    :param start: Active start datetime for the campaign in UTC, defaults to `datetime.utcnow`
    :type start: :class:`datetime.datetime`
    :param end: Active end datetime for the campaign in UTC, optional
    :type end: :class:`datetime.datetime` or `None`
    :param kwargs: Keyword arguments consisting of key-value pairs to be added to the
                   newly created goal as metadata.
    :type kwargs: unspecified keyword arguments to the function.

    :returns: :class:`pooldlib.postgresql.models.CommunitiyGoal`
    """
    goal = CampaignGoalModel()
    goal.name = name
    goal.description = description
    goal.start = start or pytz.UTC.localize(datetime.utcnow())
    goal.end = end
    goal.type = type
    if predecessor is not None:
        goal.predecessor = predecessor
    campaign.goals.append(goal)

    with transaction_session() as session:
        session.add(goal)
        session.commit()

    meta = list()
    for (k, v) in kwargs.items():
        goal_meta = CampaignGoalMetaModel()
        goal_meta.key = k
        goal_meta.value = v
        goal_meta.campaign_goal = goal
        meta.append(goal_meta)

    with transaction_session(auto_commit=True) as session:
        for goal_meta in meta:
            session.add(goal_meta)
    return goal


def update_goal(update_goal, name=None, predecessor=None, description=None, start=None, end=None, **kwargs):
    """Update an existing goal for a campaign. Only ``goal`` is required. All
    given goal properties will be updated. Any unspecified keyword arguments will
    be used to update the goal's metadata. To delete metadata for a campaign goal,
    pass ``None`` as the value for the to be deleted key in the kwarg key-value pair.

    :param update_goal: Identifier for the target campaign.
    :type update_goal: :class:`pooldlib.postgresql.models.Goal`
    :param name: The name of the newly created campaign goal.
    :type name: string
    :param description: The description of the newly created campaign goal.
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
    if predecessor is not None:
        goal.predecessor_id = predecessor.id

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
        goal_meta = CampaignGoalMetaModel()
        goal_meta.key = k
        goal_meta.value = v
        goal_meta.campaign_goal = update_goal
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
    """Disable a specific instance of the CampaignGoal data model. This will prevent
    the user from being returned by calls to :func:`pooldlib.api.user.get`
    and any further updates to the user being allowed.

    :param user: User which to disable.
    :type user: :class:`pooldlib.postgresql.models.User` or user identifier
    """
    disable_goal.update_field('enabled', False)
    with transaction_session(auto_commit=True) as session:
        session.add(disable_goal)


def associate_user_with_goal(campaign_goal, user, participation, pledge=None):
    """Associate given user with ``campaign_goal``. The association will be described by
    ``participation``, which can be one of 'opted-in', 'opted-out', 'participating',
    'nonparticipating'. The values 'participating' and 'nonparticipating' should only be used
    for default participation descriptions.  If a use opts to change their participation, use
    appropriate descriptor of 'opted-in' or 'opted-out'. These rules should be followed precisely
    for reporting purposes.

    :raises: :class:`pooldlib.exceptions.InvalidGoalParticipationNameError`
             :class:`pooldlib.exceptions.DuplicateCampaignGoalUserAssociationError`
    """
    cga = CampaignGoalAssociationModel()
    cga.campaign_id = campaign_goal.campaign.id
    cga.campaign_goal = campaign_goal
    cga.user = user
    cga.participation = participation
    cga.pledge = pledge

    with transaction_session() as session:
        session.add(cga)
        try:
            session.commit()
        except SQLAlchemyDataError:
            raise InvalidGoalParticipationNameError()
        except SQLAlchemyIntegrityError:
            raise DuplicateCampaignGoalUserAssociationError()
    return cga


def update_user_goal_association(campaign_goal, user, participation):
    """Update a given user's association with ``campaign_goal``. The association will be
    described by ``participation``, which can be one of 'opted-in' and 'opted-out', 'participating',
    'nonparticipating'. The values 'participating' and 'nonparticipating' should only be used
    for default participation descriptions.  If a use opts to change their participation, use
    appropriate descriptor of 'opted-in' or 'opted-out'. These rules should be followed precisely
    for reporting purposes.

    :raises: :class:`pooldlib.exceptions.InvalidGoalParticipationNameError`
    """
    cga = CampaignGoalAssociationModel.query.filter_by(campaign=campaign_goal.campaign)\
                                            .filter_by(campaign_goal=campaign_goal)\
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
