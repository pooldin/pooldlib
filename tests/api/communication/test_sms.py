import os
from uuid import uuid4 as uuid

from pooldlib import config, DIR
from pooldlib.api.communication import SMSClient

from tests import tag
from tests.base import PooldLibPostgresBaseTest


class TestSendSMSMessage(PooldLibPostgresBaseTest):
    # These are functional test which depend on the stripe api.
    # To run all stripe api related tests run: $ make tests-stripe
    # To run all tests which utilize external services run: $ make
    def setUp(self):
        super(TestSendSMSMessage, self).setUp()

        try:
            config_path = os.path.join(os.path.dirname(DIR), '.env')
            config.update_with_file(config_path)
        except:
            pass

        self.client = SMSClient('+' + str(config.TWILIO_SMS_SENDING_NUMBER),
                                config.TWILIO_ACCOUNT_SID,
                                config.TWILIO_AUTH_TOKEN)

        self.username = uuid().hex.lower()
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)

    @tag('external', 'twilio')
    def test_send_ten_digit_number(self):
        self.create_user_meta(self.user, mobile_number='+12064846196')
        self.client.send(self.user, "It's a test sms message!")
