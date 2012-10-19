"""
pooldlib.api.user
===============================

.. currentmodule:: pooldlib.api.user

"""
import re

from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError
from sqlalchemy.orm.attributes import manager_of_class

from pooldlib.generators import alphanumeric_string
from pooldlib.exceptions import (InvalidPasswordError,
                                 UnknownUserError,
                                 EmailUnavailableError,
                                 UsernameUnavailableError)
from pooldlib.sqlalchemy import transaction_session
from pooldlib.postgresql import db
from pooldlib.postgresql import (User as UserModel,
                                 UserMeta as UserMetaModel)


USER_TABLE = manager_of_class(UserModel).mapper.mapped_table

numericRE = re.compile('\d')


def get(user_id):
    """Return a user from the database based on either their
    username or associated email address. If no user is found
    ``NoneType`` is returned.

    :param user_id: Identifier for the user, either their associated
                    username, email address or id.
    :type user_id: :class:`pooldlib.postgresql.models.User`, string or long

    :returns: :class:`pooldlib.postgresql.models.User` or ``NoneType``
    """
    if user_id is None:
        return None

    if isinstance(user_id, UserModel):
        if not user_id.enabled:
            return None
        return user_id

    # If the identifier is an integer try lookup via integer user.id
    if isinstance(user_id, (int, long)):
        user = UserModel.query.filter_by(id=user_id)\
                              .filter_by(enabled=True)\
                              .first()
        return user or None

    # First, check if we have the username (we make no assumptions
    # about the construction of the username. Only consider enabled users.
    user = UserModel.query.filter_by(username=user_id, enabled=True).first()
    if user:
        return user

    # Now try an email lookup
    user = UserModel.query.join(UserMetaModel)\
                          .filter(UserMetaModel.key == 'email')\
                          .filter(UserMetaModel.value == user_id)\
                          .filter(UserModel.enabled == True)\
                          .first()

    return user or None


def get_balance(user, currency):
    """Retrieve balance for a specific currency type for
    the given user identifier.

    :param user: User for which to retrieve balance information.
    :type user: :class:`pooldlib.postgresql.models.User` or user identifier
                (username, id, etc).
    :param currency: Limit results to those associated with ``currency``.
    :type currency: Either string or :class:`pooldlib.postgresql.models.Currency`

    :raises: :class:`pooldlib.exceptions.UnknownUserError`
    """
    raise NotImplementedError()


def associate_stripe_token(user, stripe_token, force=False):
    """Exchange a Stripe one-time use token for a user id in Stripe's
    system. The user's stripe user id will be stored as UserMeta data and
    accessible via ``User.stripe_id``.  If the user is already associated
    with a different Stripe user id an exception will be raised unless
    ``force=True``.

    :param user: User for which to associate the retrieved Strip user id.
    :type user: :class:`pooldlib.postgresql.models.User` or user identifier
                (username, id, etc).
    :param stripe_token: The single use token returned by Stripe, usually in
                         response to a credit card authorization via stripe.js
    :type stripe_token: string
    :param force: If the target user is allready associated with a different
                  Strip user id, do not raise ``PreviousStripeAssociationError``
                  and update the existing record.
    :type force: boolean

    :raises: :class:`pooldlib.exceptions.UnknownUserError`
             :class:`pooldlib.exceptions.PreviousStripeAssociationError`
    """
    raise NotImplementedError()


def connections(user, as_organizer=True):
    """Return user-user connections for the given user. If ``as_organizer=True``,
    only return users who have participated in campaigns which the given user
    has organized.

    :param user: The target user for which to gather user-user connections.
    :type user: :class:`pooldlib.postgresql.models.User` or user identifier
                (username, id, etc).

    :raises: :class:`pooldlib.exceptions.UnknownUserError`

    :returns: list
    """
    raise NotImplementedError()


# TODO :: Enable pagination
def communities(user):
    """Return all communities associated with the given user identifier.

    :param user: User for which to return community connections.
    :type user: :class:`pooldlib.postgresql.models.User` or user identifier
                (username, id, etc).

    :raises: :class:`pooldlib.exceptions.UnknownUserError`
    """
    raise NotImplementedError()


# TODO :: Enable pagination
def transactions(user, party=None, currency=None):
    """Return all transactions associated with the given user identifier.

    :param user: User for which to return transaction data.
    :type user: :class:`pooldlib.postgresql.models.User` or user identifier
                (username, id, etc).
    :param party: If given, filter transactions to those associated with the
                  given ``party``.
    :type party: string
    :param currency: Limit results to those associated with ``currency``.
    :type currency: Either string or :class:`pooldlib.postgresql.models.Currency`

    :raises: :class:`pooldlib.exceptions.UnknownUserError`
    """
    raise NotImplementedError()


# TODO :: Enable pagination
def transfers(user, xfer_to=None, xfer_from=None, currency=None):
    """
    :param user: User for which to return transfer data.
    :type user: :class:`pooldlib.postgresql.models.User` or user identifier
                (username, id, etc).
    :param xfer_to: If given, filter transfers to those in which the user transferred
                  **to** ``xfer_to``
    :type xfer_from: string identifier, :class:`pooldlib.postgresql.models.User`
                 or :class:`pooldlib.postgresql.models.Community`
    :param xfer_from: If given, filter transfers to those in which the user was the recipient
                  of a transfer **from** ``xfer_from``
    :type xfer_from: string identifier, :class:`pooldlib.postgresql.models.User`
                 or :class:`pooldlib.postgresql.models.Community`
    :param currency: Limit results to those associated with ``currency``.
    :type currency: Either string or :class:`pooldlib.postgresql.models.Currency`

    :raises: :class:`pooldlib.exceptions.UnknownUserError`
    """
    raise NotImplementedError()


def verify_password(user, password):
    """Verify that the givin password is the password associated with
    a given User data model instance. Returns True if the password given
    matches that of ``user``.

    :param user: User to use in password comparison.
    :type user: :class:`pooldlib.postgresql.models.User` or user identifier
                (username, id, etc).
    :param password: The password to verify against the stored
                     password for the user.
    :type password: string

    :returns: boolean

    :raises: :class:`pooldlib.exceptions.UnknownUserError`
    """
    user = get(user)
    if not user:
        raise UnknownUserError()
    return user.is_password(password)


def create(username, password, name=None, **kwargs):
    """Create and return a new instance of
    :class:`pooldlib.postgresql.models.User`. Any unspecified
    kwargs will be assumed to be metadata to be associated with
    the new user. All errors are bubbled up.

    :param username: The username of the new user.
    :type username: string
    :param password: The password for the new user.
    :type password: string
    :param name: The full name of the new user (optional).
    :type password: string
    :param kwargs: Metadata to associate with the new user.
    :type kwargs: kwarg dictionary

    :raises: :class:`pooldlib.exceptions.InvalidPasswordError`
             :class:`pooldlib.exceptions.UsernameUnavailableError`
             :class:`pooldlib.exceptions.EmailUnavailableError`

    :returns: :class:`pooldlib.postgresql.models.User`
    """
    validate_password(password, exception_on_invalid=True)

    if 'email' in kwargs:
        if email_exists(kwargs['email']):
            msg = 'The email address %s is already assigned to another user.' % kwargs['email']
            raise EmailUnavailableError(msg)

    u = UserModel()
    u.username = username
    u.password = password
    if name:
        u.name = name

    with transaction_session() as session:
        try:
            session.add(u)
            session.commit()
        except SQLAlchemyIntegrityError:
            msg = "Username %s already in use." % username
            raise UsernameUnavailableError(msg)

    if 'email' in kwargs:
        if email_exists(kwargs['email']):
            msg = 'The email address %s is already assigned to another user.' % kwargs['email']
            raise EmailUnavailableError(msg)

    meta = list()
    for (k, v) in kwargs.items():
        um = UserMetaModel()
        um.key = k
        um.value = v
        um.user = u
        meta.append(um)

    with transaction_session(auto_commit=True) as session:
        for um in meta:
            session.add(um)
    return u


def update(user, username=None, name=None, password=None, **kwargs):
    """Update properties of a specific User data model instance.  Any unspecified
    kwargs will be assumed to be metadata. Existing metadata will be updated
    to the newly supplied value, and any new metadata keys will be associated
    with the user. To reset a user's password, use
    :func:`pooldlib.api.user.reset_password`. To delete a user's metadata, pass ``None``
    as the value for the to be deleted key in the kwarg key-value pair.

    :param user: User for which to update ``User`` model data.
    :type user: :class:`pooldlib.postgresql.models.User` or user identifier
                (username, id, etc).
    :param username: New username to associate with `User` instance.
    :type username: string
    :param name: New name to associate with `User` data model instance.
    :type name: string
    :param kwargs: key-value pairs to associate with the `User` data model instance
                   as metadata.
    :type kwargs: kwarg dictionary

    :raises: :class:`pooldlib.exceptions.InvalidPasswordError`
             :class:`pooldlib.exceptions.UnknownUserError`

    :returns: :class:`pooldlib.postgresql.models.User`
    """
    user = get(user)
    if not user:
        raise UnknownUserError()
    if username:
        user.update_field('username', username)
    if name:
        user.update_field('name', name)
    if password:
        validate_password(password, exception_on_invalid=True)
        user.update_field('password', password)

    if 'email' in kwargs:
        if email_exists(kwargs['email'], user=user):
            msg = 'The email address %s is already assigned to another user.' % kwargs['email']
            raise EmailUnavailableError(msg)

    update_meta = [m for m in user.metadata if m.key in kwargs]
    create_meta = [(k, v) for (k, v) in kwargs.items() if not hasattr(user, k)]

    meta_delta = list()
    meta_remove = list()
    for m in update_meta:
        m.value = kwargs[m.key]
        if m.value is None:
            meta_remove.append(m)
        else:
            meta_delta.append(m)

    for (k, v) in create_meta:
        m = UserMetaModel()
        m.key = k
        m.value = v
        m.user = user
        meta_delta.append(m)

    with transaction_session() as session:
        session.add(user)  # Technically not needed, but gives the context content

        try:
            session.flush()
        except SQLAlchemyIntegrityError, e:
            if username is not None:
                msg = "Username %s already in use." % username
                raise UsernameUnavailableError(msg)
            raise e

        for m in meta_delta:
            session.add(m)
            session.flush()
        for m in meta_remove:
            session.delete(m)

        session.commit()

    return user


def set_password(user, password):
    """Reset a user's password. The new password must conform to the user password
    requirements as defined in the doc string for :func:`pooldlib.api.user.validate_password`.


    :param user: User for which to update password.
    :type user: :class:`pooldlib.postgresql.models.User` or user identifier
                (username, id, etc).
    :param password: The new password to associate with the user.
    :type password: string

    :raises: :class:`pooldlib.exceptions.InvalidPasswordError`
             :class:`pooldlib.exceptions.UnknownUserError`

    :returns: :class:`pooldlib.postgresql.models.User`
    """
    validate_password(password, exception_on_invalid=True)
    user = get(user)
    if not user:
        raise UnknownUserError()

    user.update_field('password', password)
    with transaction_session(auto_commit=True) as session:
        session.add(user)

    return user


def reset_password(user):
    """Generate a new, random, password for a specific ``User`` data model instance.

    :param user: User for which to reset password.
    :type user: :class:`pooldlib.postgresql.models.User` or user identifier
                (username, id, etc).

    :returns: The new password for the User data model instance as a ``string``
    """
    user = get(user)
    if not user:
        raise UnknownUserError()

    newpass = alphanumeric_string(alpha_count=8, number_count=2)
    user.password = newpass
    with transaction_session(auto_commit=True) as session:
        session.add(user)
    return newpass


def disable(user):
    """Disable a specific instance of the User data model. This will prevent
    the user from being returned by calls to :func:`pooldlib.api.user.get`
    and any further updates to the user being allowed.

    :param user: User which to disable.
    :type user: :class:`pooldlib.postgresql.models.User` or user identifier

    :raises: :class:`pooldlib.exceptions.UnknownUserError`
    """
    user = get(user)
    if not user:
        raise UnknownUserError()
    user.update_field('enabled', False)
    with transaction_session(auto_commit=True) as session:
        session.add(user)


def validate_password(password, exception_on_invalid=False):
    """Confirm that the given password adheres to the following restrictions,
    which are shamelessly stolen from github:

        - Passwords must be at least 7 characters in length.
        - Passwords must contain at least one numeric character.

    :param password: The password to validate.
    :type password: string
    :param exception_on_invalid: When `True` will raise the perscribed exception
                                 if the password does not meet the perscribed restrictions.

    :raises: :class:`pooldlib.exceptions.InvalidPasswordError`

    :returns: `None`
    """
    msg = None
    valid = True
    if len(password) < 7:
        msg = 'Password must be at least 7 characters in length.'
        valid = False
    elif not numericRE.search(password):
        msg = 'Password must contain at least one numeric character.'
        valid = False

    if not valid and exception_on_invalid:
        raise InvalidPasswordError(msg)
    return valid


def username_exists(username):
    """Checks whether a username exists. Returns true if the username exists or
    false if the username does not exist.

    :param username: The username to check for existence.
    :type username: string

    :returns: `bool`
    """
    query = UserModel.query
    query = query.filter_by(username=username, enabled=True)
    return query.count() > 0


def email_exists(email, user=None):
    """Checks whether an email exists. Returns True if the email exists or
    False if the email does not exist.

    Optionally, if ``user`` is defined, will return False if it is associated
    with given user.

    :param username: The username to check for existence.
    :type username: string

    :returns: `bool`
    """
    sql = """SELECT user_id
             FROM user_meta
             WHERE key = 'email'
                AND value = '%s';
          """
    ret = db.session.execute(sql % email).first()
    if ret and user is not None:
        user = get(user)
        return ret[0] != user.id
    return ret is not None
