from twilio.rest import TwilioRestClient as _TwilioRestClient

from pooldlib.exceptions import UserMobileNumberError

import pooldlib.log

logger = pooldlib.log.get_logger(None, logging_name=__name__)


class SMSClient(object):

    def __init__(self, send_number, account_sid, auth_token):
        self.send_number = send_number
        self.account_sid = account_sid
        self.auth_token = auth_token
        self._client = _TwilioRestClient(account_sid, auth_token)

    def send(self, user, message):
        if user.mobile_number is None:
            msg = 'Attempted to send SMS text message to user who does '\
                  'not have an associated mobile number'
            raise UserMobileNumberError(msg)
        to = user.mobile_number
        if len(to) == 11:
            to = '+%s' % to
        elif len(to) == 10:
            to = '+1%s' % to
        elif len(to) != 12:
            msg = 'Attempted to send SMS text message to malformed mobile number.'
            data = dict(user=str(user),
                        mobile_number=user.mobile_number)
            logger.error(msg, data=data, message=message)
            raise UserMobileNumberError(msg)

        self._client.sms.messages.create(to=to,
                                         from_=self.send_number,
                                         body=message)
