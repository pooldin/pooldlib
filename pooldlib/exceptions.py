"""
pooldlib.exceptions
===============================

.. currentmodule:: pooldlib.exceptions

"""


class PooldlibError(Exception):
    """Base class for exceptions raised by pooldlib.
    """


class ConfigurationError(PooldlibError):
    """Raised when a undefined configuration attribute is accessed
    """


##################################
### Fee API Related Exceptions
class FeeAPIError(PooldlibError):
    """Base clase for Fee API related errors.
    """


class UnknownFeeError(PooldlibError):
    """Raised when a fee which doesn't exist in the system is referenced.
    """
##################################


##################################
### Communication API Related Exceptions
class CommunicationAPIError(PooldlibError):
    """Base class for exceptions raised by the Communication API.
    """


class SMTPConnectionNotInitilizedError(CommunicationAPIError):
    """Raised if an attempt is made to send an email before the associated
    smtplib.SMTP object has been initialized.
    """


class NoEmailRecipientsError(CommunicationAPIError):
    """Raised if an attempt is made to send an email prior to the sender address
    being set.
    """


class NoContentEmailError(CommunicationAPIError):
    """Raised if an attempt is made to send an email prior to it's content
    being set.
    """


class UserMobileNumberError(CommunicationAPIError):
    """Raised when an error with a user's mobile number is encountered while
    sending an SMS text message.
    """
##################################


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


class PreviousStripeAssociationError(UserAPIError):
    """Raised when an attempt is made to associate a stripe user with
    a poold user who is already associated with one.
    """


class StripeCustomerAccountError(UserAPIError):
    """Raised when a problem is encountered with regards to a
    stripe customer account.
    """


class StripeUserAccountError(UserAPIError):
    """Raised when a problem is encountered with regards to a
    stripe user account.
    """

class UserCreditCardDeclinedError(UserAPIError):
    """Raised when a transaction fails because a user's card
    was declined.
    """
##################################


##################################
### Campaign API Related Exceptions
class CampaignAPIError(PooldlibError):
    """Base class for exceptions raise by the Campaign API.
    """


class UnknownCampaignError(CampaignAPIError):
    """Raised when an attempt to access an unknown campaign is made.
    """


class UnknownCampaignGoalError(CampaignAPIError):
    """Raised when an attempt to access an unknown campaign goal is made.
    """


class InvalidUserRoleError(CampaignAPIError):
    """Raised when an attempt is made to associate a user with a campaign
    with an invalid role name.
    """


class InvalidGoalParticipationNameError(CampaignAPIError):
    """Raised when an attempt is made to associate a user with a campaign
    goal using an invalid participation name.
    """


class DuplicateCampaignUserAssociationError(CampaignAPIError):
    """Raised when an attempt is to create a duplicate user/campaign
    association.
    """


class DuplicateCampaignGoalUserAssociationError(CampaignAPIError):
    """Raised when an attempt is to create a duplicate user/campaign goal
    association.
    """


class UnknownCampaignAssociationError(CampaignAPIError):
    """Raised when an attempt is made to access an unknown user/campaign
    association.
    """


class UnknownCampaignGoalAssociationError(CampaignAPIError):
    """Raised when an attempt is made to access an unknown user/campaign-goal
    association.
    """


class CampaignConfigurationError(CampaignAPIError):
    """Raised when a problem is encountered with a campaign configuration.
    """


class PreviousUserContributionError(CampaignAPIError):
    """Raised when a CampaignAssociation is updated with a new pledge amount
    and there is a pledge already associated with the CampaignAssociation.
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


##################################
### Internal Exceptions
class InternalError(Exception):
    """Base class for internal errors.
    """


class GoWorkForBallmerError(InternalError):
    """Raised when you don't follow web standards.
    """
##################################


##################################
### Third Party API Exceptions
class ExternalServiceError(Exception):
    """Base class for errors related to external services.
    """


class ExternalAPIUsageError(ExternalServiceError):
    """Raised when an error occurs related to the usage of an external service
    when it is due to the miss use of the service.
    """


class ExternalAPIError(ExternalServiceError):
    """Raised when an error occurs related to the usage of an external service
    when it is due to an error caused by the external service.
    """


class ExternalAPIUnavailableError(ExternalServiceError):
    """Raised when an external service is unavailable.
    """
##################################
