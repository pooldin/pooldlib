"""
pooldlib.api.user
===============================

.. currentmodule:: pooldlib.api.user

"""
import re

from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError
from sqlalchemy.orm.attributes import manager_of_class

from stripe import (AuthenticationError as StripeAuthenticationError,
                    InvalidRequestError as StripeInvalidRequestError,
                    APIError as StripeAPIError,
                    APIConnectionError as StripeAPIConnectionError)

import pooldlib.log
from pooldlib.payment import StripeCustomer, StripeUser
from pooldlib.generators import alphanumeric_string
from pooldlib.exceptions import (InvalidPasswordError,
                                 EmailUnavailableError,
                                 UsernameUnavailableError,
                                 PreviousStripeAssociationError,
                                 ExternalAPIUsageError,
                                 ExternalAPIError,
                                 ExternalAPIUnavailableError)
from pooldlib.sqlalchemy import transaction_session
from pooldlib.postgresql import db
from pooldlib.postgresql import (User as UserModel,
                                 UserMeta as UserMetaModel)

logger = pooldlib.log.get_logger(None, logging_name=__name__)

USER_TABLE = manager_of_class(UserModel).mapper.mapped_table

numericRE = re.compile('\d')


def get_by_id(user_id):
    """Return a user from the database based on their long integer id.
    If no user is found `None` is returned.

    :param email: long integer ID of the target user.
    :type email: long

    :returns: :class:`pooldlib.postgresql.models.User` or `None`
    """
    query = UserModel.query.filter_by(id=user_id)
    query = query.filter_by(enabled=True)
    user = query.first()
    if not user:
        msg = 'No user found for requested user id.'
        logger.debug(msg, data=user_id)
    return user or None


def get_by_username(username):
    """Return a user from the database based on their associated username.
    If no user is found `None` is returned.

    :param username: Username to use in performing user lookup.
    :type username: string

    :returns: :class:`pooldlib.postgresql.models.User` or `None`
    """
    query = UserModel.query.filter_by(username=username, enabled=True)
    user = query.first()
    if not user:
        msg = 'No user found for requested username.'
        logger.debug(msg, data=username)
    return user or None


def get_by_email(email):
    """Return a user from the database based on their associated email address.
    If no user is found `None` is returned.

    :param email: Email address used to perform user lookup.
    :type email: string

    :returns: :class:`pooldlib.postgresql.models.User` or `None`
    """
    query = UserModel.query.filter_by(enabled=True)
    query = query.join(UserMetaModel)
    query = query.filter(UserMetaModel.key == 'email')
    query = query.filter(UserMetaModel.value == email.lower())
    user = query.first()
    if not user:
        msg = 'No user found for requested email address.'
        logger.debug(msg, data=email)
    return user or None


def get_balance(user, currency):
    """Retrieve balance for a specific currency type for
    the given user identifier.

    :param user: User for which to retrieve balance information.
    :type user: :class:`pooldlib.postgresql.models.User`
    :param currency: Limit results to those associated with ``currency``.
    :type currency: Either string or
                    :class:`pooldlib.postgresql.models.Currency`
    """
    raise NotImplementedError()


def associate_stripe_token(user, stripe_token, stripe_key, force=False):
    """Exchange a Stripe one-time use token for a customer id in Stripe's
    system. The poold user's stripe customer id will be stored as UserMeta data and
    accessible via ``User.stripe_customer_id``.  If the user is already
    associated with a different Stripe customer id an exception will be raised
    unless ``force=True``.

    Stripe Customer: A user who is utilizing stripe to pay *into* our system.

    :param user: User for which to associate the retrieved Strip user id.
    :type user: :class:`pooldlib.postgresql.models.User`
    :param stripe_token: The single use token returned by Stripe, usually in
                         response to a credit card authorization via stripe.js
    :type stripe_token: string
    :param force: If the target user is allready associated with a different
                  Strip user id, do not raise
                  ``PreviousStripeAssociationError`` and update the existing
                  record.
    :type force: boolean

    :raises: :class:`pooldlib.exceptions.PreviousStripeAssociationError`
             :class:`pooldlib.exceptions.ExternalAPIUsageError`
             :class:`pooldlib.exceptions.ExternalAPIError`
             :class:`pooldlib.exceptions.ExternalAPIUnavailableError`
    """
    try:
        stripe_customer = StripeCustomer(app_key=stripe_key)
        stripe_customer_id = stripe_customer.token_for_customer(stripe_token, user)
        previous_association = hasattr(user, 'stripe_customer_id') and user.stripe_customer_id != stripe_customer_id
        if previous_association and not force:
            msg = 'User has a previously associated stripe customer id and force was not set to True.'
            raise PreviousStripeAssociationError(msg)
    except (StripeAuthenticationError, StripeInvalidRequestError):
        # Errors caused by us
        msg = 'An error occurred in pooldlib while exchanging one time use token for Stripe user'
        raise ExternalAPIUsageError(msg)
    except StripeAPIError:
        # Errors caused by stripe
        msg = 'An error occurred with Stripe while exchanging one time use token for Stripe user'
        raise ExternalAPIError(msg)
    except StripeAPIConnectionError:
        # Errors caused by trucks getting caught in the tubes
        msg = 'An error occurred while connecting to the Stripe API.'
        raise ExternalAPIUnavailableError(msg)
    update(user, stripe_customer_id=stripe_customer_id)


def associate_stripe_authorization_code(user, auth_code, stripe_key, force=False):
    """Exchange a Stripe Connect authorization code for stripe Connect user
    data. The user's stripe user_id, publishable_key, access_token, and the granted
    scope for the access_token will be stored in the user's profile with the following
    keys: stripe_user_id, stripe_user_token, stripe_user_public_key, strip_user_grant_scope.
    If the user is already associated with a different Stripe Connect user id an exception
    will be raised unless ``force=True``, in which all keys will be updated to values returned
    by the stripe connect api.

    The value of ``user.stripe_user_token`` *must* be used as the stripe API key when executing
    transactions on behalf of this user.

    Stripe Connect User: A user who is utilizing stripe to receive payments *from* our system.

    :param user: User for which to associate the retrieved Strip user id.
    :type user: :class:`pooldlib.postgresql.models.User`
    :param stripe_token: The single use token returned by Stripe, usually in
                         response to a credit card authorization via stripe.js
    :type stripe_token: string
    :param force: If the target user is allready associated with a different
                  Strip user id, do not raise
                  ``PreviousStripeAssociationError`` and update the existing
                  record.
    :type force: boolean

    :raises: :class:`pooldlib.exceptions.PreviousStripeAssociationError`
             :class:`pooldlib.exceptions.ExternalAPIUsageError`
             :class:`pooldlib.exceptions.ExternalAPIError`
             :class:`pooldlib.exceptions.ExternalAPIUnavailableError`
    """
    try:
        stripe_user = StripeUser(app_key=stripe_key)
        # Keys in user_data: public_key, access_token, scope, user_id
        user_data = stripe_user.process_authorization_code(auth_code, user)

        previous_association = hasattr(user, 'stripe_user_id') and user.stripe_user_id != user_data['user_id']
        if previous_association and not force:
            msg = 'User has a previously associated stripe user account and force was not set to True.'
            raise PreviousStripeAssociationError(msg)
    except (StripeAuthenticationError, StripeInvalidRequestError):
        # Errors caused by us
        msg = 'An error occurred in pooldlib while associating Stripe Connect account with user'
        raise ExternalAPIUsageError(msg)
    except StripeAPIError:
        # Errors caused by stripe
        msg = 'An error occurred with Stripe while associating Stripe Connect account with user'
        raise ExternalAPIError(msg)
    except StripeAPIConnectionError:
        # Errors caused by trucks getting caught in the tubes
        msg = 'An error occurred while connecting to the Stripe Connect API.'
        raise ExternalAPIUnavailableError(msg)

    update(user,
           stripe_user_id=user_data['user_id'],
           stripe_user_token=user_data['access_token'],
           stripe_user_public_key=user_data['public_key'],
           stripe_user_grant_scope=user_data['scope'])


def connections(user, as_organizer=True):
    """Return user-user connections for the given user. If
    ``as_organizer=True``, only return users who have participated in
    campaigns which the given user has organized.

    :param user: The target user for which to gather user-user connections.
    :type user: :class:`pooldlib.postgresql.models.User` or user identifier
                (username, id, etc).

    :returns: list
    """
    raise NotImplementedError()


# TODO :: Enable pagination
def communities(user):
    """Return all communities associated with the given user identifier.

    :param user: User for which to return community connections.
    :type user: :class:`pooldlib.postgresql.models.User`
    """
    raise NotImplementedError()


# TODO :: Enable pagination
def transactions(user, party=None, currency=None):
    """Return all transactions associated with the given user identifier.

    :param user: User for which to return transaction data.
    :type user: :class:`pooldlib.postgresql.models.User`
    :param party: If given, filter transactions to those associated with the
                  given ``party``.
    :type party: string
    :param currency: Limit results to those associated with ``currency``.
    :type currency: Either string or
                    :class:`pooldlib.postgresql.models.Currency`
    """
    raise NotImplementedError()


# TODO :: Enable pagination
def transfers(user, xfer_to=None, xfer_from=None, currency=None):
    """
    :param user: User for which to return transfer data.
    :type user: :class:`pooldlib.postgresql.models.User`
    :param xfer_to: If given, filter transfers to those in which the user
                    transferred **to** ``xfer_to``
    :type xfer_from: string identifier,
                     :class:`pooldlib.postgresql.models.User`
                 or :class:`pooldlib.postgresql.models.Community`
    :param xfer_from: If given, filter transfers to those in which the user
                      was the recipient of a transfer **from** ``xfer_from``
    :type xfer_from: string identifier,
                     :class:`pooldlib.postgresql.models.User`
                 or :class:`pooldlib.postgresql.models.Community`
    :param currency: Limit results to those associated with ``currency``.
    :type currency: Either string or
                    :class:`pooldlib.postgresql.models.Currency`
    """
    raise NotImplementedError()


def verify_password(user, password):
    """Verify that the givin password is the password associated with
    a given User data model instance. Returns True if the password given
    matches that of ``user``.

    :param user: User object to use in password comparison.
    :type user: :class:`pooldlib.postgresql.models.User`
    :param password: The password to verify against the stored
                     password for the user.
    :type password: string

    :returns: boolean
    """
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
            msg = 'The email address %s is already assigned to another user.'
            msg %= kwargs['email']
            raise EmailUnavailableError(msg)
        # Only store lower-case emails in the system
        kwargs['email'] = kwargs['email'].lower()

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
    """Update properties of a specific User data model instance.  Any
    unspecified keyword arguments will be assumed to be metadata. Existing
    metadata will be updated to the newly supplied value, and any new metadata
    keys will be associated with the user.
    :func:`pooldlib.api.user.reset_password` can be used to update
    a users password as well. To delete a user's metadata, pass ``None``
    as the value for the to be deleted key in the kwarg key-value pair.
    The ``name`` property of the User model can be cleared by passing
    an empty string ('') as the value for the name kwarg.

    :param user: User for which to update ``User`` model data.
    :type user: :class:`pooldlib.postgresql.models.User`
    :param username: New username to associate with `User` instance.
    :type username: string
    :param name: New name to associate with `User` data model instance.
    :type name: string
    :param kwargs: key-value pairs to associate with the `User` data model
                   instance as metadata.
    :type kwargs: kwarg dictionary

    :raises: :class:`pooldlib.exceptions.InvalidPasswordError`

    :returns: :class:`pooldlib.postgresql.models.User`
    """
    if username:
        user.update_field('username', username)
    if name is not None:
        name = None if name == '' else name
        user.update_field('name', name, nullable=True)
    if password:
        validate_password(password, exception_on_invalid=True)
        user.update_field('password', password)

    if 'email' in kwargs:
        if email_exists(kwargs['email'], user=user):
            msg = 'The email address %s is already assigned to another user.'
            msg %= kwargs['email']
            raise EmailUnavailableError(msg)
        kwargs['email'] = kwargs['email'].lower()

    update_meta = [m for m in user.metadata if m.key in kwargs]
    create_meta = [(k, v) for (k, v) in kwargs.items() if not hasattr(user, k)]

    meta_delta = list()
    meta_remove = list()
    for user_meta in update_meta:
        value = kwargs[user_meta.key]
        if value is None:
            meta_remove.append(user_meta)
        else:
            user_meta.value = value
            meta_delta.append(user_meta)

    for (k, v) in create_meta:
        m = UserMetaModel()
        m.key = k
        m.value = v
        m.user = user
        meta_delta.append(m)

    with transaction_session() as session:
        # Technically not needed, but gives the context content
        session.add(user)

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
    """Reset a user's password. The new password must conform to the user
    password requirements as defined in the doc string for
    :func:`pooldlib.api.user.validate_password`.


    :param user: User for which to update password.
    :type user: :class:`pooldlib.postgresql.models.User`
    :param password: The new password to associate with the user.
    :type password: string

    :raises: :class:`pooldlib.exceptions.InvalidPasswordError`

    :returns: :class:`pooldlib.postgresql.models.User`
    """
    validate_password(password, exception_on_invalid=True)

    user.update_field('password', password)
    with transaction_session(auto_commit=True) as session:
        session.add(user)

    return user


def reset_password(user):
    """Generate a new, random, password for a specific ``User`` data model
    instance.

    :param user: User for which to reset password.
    :type user: :class:`pooldlib.postgresql.models.User`

    :returns: The new password for the User data model instance as a ``string``
    """
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
    :type user: :class:`pooldlib.postgresql.models.User`
    """
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
    :param exception_on_invalid: When `True` will raise the perscribed
                                 exception if the password does not meet the
                                 perscribed restrictions.

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

    :param email: The email to check for existence.
    :type email: string
    :param user: If defined and email address is found, function will return
                 `True` if the email address is associated with ``user``.
    :type user: :class:`pooldlib.postgresql.models.User`

    :returns: `bool`
    """
    sql = """SELECT user_id
             FROM user_meta
             WHERE key = 'email'
                AND value = '%s';
          """
    ret = db.session.execute(sql % email.lower()).first()
    if ret and user is not None:
        return ret[0] != user.id
    return ret is not None
