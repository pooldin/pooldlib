"""
pooldlib.exceptions
===============================

.. currentmodule:: pooldlib.exceptions

"""
class PooldlibError(Exception):
    """Base class for exceptions raised by pooldlib.
    """


##################################
### User API Related Exceptions
class UserAPIError(PooldlibError):
    """Base class for exceptions raise by the User API.
    """


class IllegalPasswordUpdateError(UserAPIError):
    """Raised when an illegal password reset attempt
    is made.
    """


class InvalidPasswordError(UserAPIError):
    """Raised when an attempt is made to set a user's password
    to one which doesn't conform to prescribed requirements.
    """


class UnknownUserError(UserAPIError):
    """Raised when an attempt to access an unknown user is made.
    """

class UsernameUnavailableError(UserAPIError):
    """Raised when an attempt is made to create a user with a username
    which already exists in the system.
    """

class EmailUnavailableError(UserAPIError):
    """Raised when an attempt is made to associate a user with an email
    address already paired with another user.
    """
##################################


##################################
### Community API Related Exceptions
class CommunityAPIError(PooldlibError):
    """Base class for exceptions raise by the Community API.
    """


class UnknownCommunityError(CommunityAPIError):
    """Raised when an attempt to access an unknown community is made.
    """


class UnknownCommunityGoalError(CommunityAPIError):
    """Raised when an attempt to access an unknown community goal is made.
    """


class InvalidUserRoleError(CommunityAPIError):
    """Raised when an attempt is made to associate a user with a community
    with an invalid role name.
    """


class DuplicateCommunityUserAssociationError(CommunityAPIError):
    """Raised when an attempt is made to associate a user with a community
    with an invalid role name.
    """


class UnknownCommunityAssociationError(CommunityAPIError):
    """Raised when an attempt is made to access an unknown user/community
    association.
    """


##################################
### Transaction API Related Exceptions
class TransactAPIError(PooldlibError):
    """Base class for errors encountered during operation of
    pooldlib.api.Transact calls."""


class InsufficentFundsTransferError(TransactAPIError):
    """An attempt was made to transfer too much currency from
    one balance to another."""


class InsufficentFundsTransactionError(TransactAPIError):
    """An attempt was made to execute a transaction with insufficient
    funds in the target balance."""
##################################
