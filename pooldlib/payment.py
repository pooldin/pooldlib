import json

import stripe
from stripe import Customer as _Customer

import pooldlib.log

logger = pooldlib.log.get_logger(None, logging_name=__name__)

__all__ = ('StripeCustomer', 'StripeUser')


class _StripeObject(object):

    def __init__(self, api_key):
        self.api_key = api_key

    def _handle_error(self, error, user, params, raise_errors=True):
        meta = dict(user=str(user),
                    request_args=params)
        data = dict(error=type(error).__name__,
                    message=error.message)
        if isinstance(error, stripe.AuthenticationError):
            # We were unable to authenticate with stripe, this
            # needs immediate attention.
            msg = 'Stripe Authentication Error.'
            logger.error(msg, data=data, **meta)
        elif isinstance(error, stripe.InvalidRequestError):
            # The given token was malformed or unknown by stripe
            msg = 'Stripe Invalid Request Error.'
            logger.error(msg, data=data, **meta)
        elif isinstance(error, stripe.APIConnectionError):
            # A connection error prevented us from creating the user
            msg = 'There was an error connecting to the Stripe API.'
            logger.error(msg, data=data, **meta)
        elif isinstance(error, stripe.APIError):
            # Something unknown went wrong with the api exchanging the token
            msg = 'An unknown error occurred while interacting with the Stripe API.'
            logger.error(msg, data=data, **meta)
        else:
            # Something just plain went wrong...
            msg = 'An unknown error with the Stripe module.'
            logger.error(msg, data=data, **meta)

        if raise_errors:
            raise error


class StripeCustomer(_StripeObject):
    """A `StripeCustomer` is defined to be the credit card user stripe
    system. When a user supplies us a credit card details stipe in return
    gives us a one time use token.  This token is then used to create/retrieve
    a `stripe.Customer` from Stripe.
    """

    def token_for_customer(self, token, user):
        """Create a user in Stipe's system using a one time use token
        as returned from `stripe.js`. This function does not alter the user
        object in any way.

        :params token: The one time use token returned by stripe.js when
                            submitting payment details.
        :type token: string
        :param user: The user with which the new stripe customer will be
                    associated, used only for error logging.
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
            stripe_user = _Customer.create(api_key=self.api_key, **kwargs)
            msg = 'New Stripe Customer Created'
            logger.transaction(msg, **kwargs)
        except stripe.StripeError, e:
            self._handle_error(e, user, kwargs)
        except Exception, e:  # Catch any other error and log, then re-raise
            msg = 'An unknown error occurred while creating a new Stripe Customer.'
            data = dict(error_type=type(e).__class__,
                        error_message=e.message)
            logger.error(msg, data=data, **kwargs)
            raise

        return stripe_user.id


class StripeUser(_StripeObject):

    def __init__(self, *args, **kwargs):
        super(StripeUser, self).__init__(*args, **kwargs)
        self.client = StripeConnectRequestor(self.api_key)

    def process_authorization_code(self, auth_code, user):
        """Exchange the authorization_code returned by Stripe Connect for an
        account access_token. This access token will be used as the ``stripe.api_key``
        for any charges made on behalf of this user with Stripe.

        See: https://stripe.com/docs/connect/oauth#token-request

        :param auth_code: The authorization code returned by Stripe's OAuth
                          process, posted to the Redirect URL for our Stripe
                          Application.
        :type auth_code: string
        :param user: The user with which the new stripe user will be
                    associated, used only for error logging.
        :type user: :class:`pooldlib.postgresql.models.User`

        :returns: dict, keys: public_key,
                              access_token,
                              scope,
                              user_id

        :raises: stripe.AuthenticationError
                 stripe.InvalidRequestError
                 stripe.APIConnectionError
                 stripe.APIError
        """
        data = dict(code=auth_code,
                    grant_type='authorization_code')
        try:
            response, api_key = self.client.request('POST', '/oauth/token', params=data)
        except stripe.StripeError, e:
            self._handle_error(e, user, data)
        except Exception, e:  # Catch any other error and log, then re-raise
            msg = 'An unexpected error occurred while retrieving access token for user'
            data = dict(error=type(e).__name__,
                        message=e.message)
            meta = dict(user=str(user))
            logger.error(msg, data=data, **meta)
            raise

        ret = dict(public_key=response['stripe_publishable_key'],
                   access_token=response['access_token'],
                   scope=response['scope'],
                   user_id=response['stripe_user_id'])
        return ret


class StripeConnectRequestor(stripe.APIRequestor):
    """A subclass of :class:`stripe.APIRequestor` to facilitate making
    requests to Stripe Connect endpoints.  All requests are made using SSL.
    """
    api_base = 'https://connect.stripe.com'

    @classmethod
    def api_url(cls, url=''):
        return '%s%s' % (cls.api_base, url)

    def _handle_api_error(self, rbody, rcode, resp):
        # We've got to do some jiggery-pokery with the response
        # so that the super-method can handle errors thrown by
        # the stripe connect endpoints.
        new_resp = {'error': {
            'message': resp['error_description'],
            'code': resp['error'],
            'param': json.dumps(resp)}  # Do this just in case we get more info than described by the docs
        }
        super(StripeConnectRequestor, self).handle_api_error(rbody, rcode, new_resp)

    handle_api_error = _handle_api_error
