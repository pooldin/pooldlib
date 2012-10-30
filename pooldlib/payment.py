import stripe
from stripe import Customer
import pooldlib.log

logger = pooldlib.log.get_logger(None, logging_name=__name__)


def configure(config):
    stripe.api_key = config.STRIPE_SECRET_KEY


def exchange_stripe_token_for_user(token, user):
    """Create a user in Stipe's system using a one time use token
    as returned from `stripe.js`.

    :params token: The one time use token returned by stripe.js when
                          submitting payment details.
    :type token: string
    :param user: The user with which the new stripe user will be
                 associated.
    :type user: :class:`pooldlib.postgresql.models.User`

    :returns: string, the Customer ID returned by Stripe.

    :raises: stripe.AuthenticationError
             stripe.InvalidRequestError
             stripe.APIConnectionError
             stripe.APIError
    """
    kwargs = dict(card=token,
                  description='Poold user: %s' % user.id,
                  email=user.email)
    try:
        stripe_user = Customer.create(**kwargs)
        msg = 'New Stripe User Created'
        logger.transaction(msg, **kwargs)
    except stripe.AuthenticationError, e:
        # We were unable to authenticate with stripe, this
        # needs immediate attention.
        msg = 'Stripe Authentication Error: %s' % str(e)
        logger.error(msg)
        raise e
    except stripe.InvalidRequestError, e:
        # The given token was malformed or unknown by stripe
        msg = 'Stripe Invalid Request Error: %s' % str(e)
        logger.error(msg)
        raise e
    except stripe.APIConnectionError, e:
        # A connection error prevented us from creating the user
        msg = 'There was an error connecting to the Stripe API: %s' % str(e)
        logger.error(msg)
        raise e
    except stripe.APIError, e:
        # Something unknown went wrong when exchanging the token
        msg = 'An unknown error occurred while interacting with the Stripe API: %s' % str(e)
        logger.error(msg)
        raise e

    return stripe_user.id
