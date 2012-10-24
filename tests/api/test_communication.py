from uuid import uuid4 as uuid

from nose.tools import raises, assert_equal, assert_true, assert_false

from mock import Mock, MagicMock, patch, mock_open

from pooldlib.exceptions import SMTPConnectionNotInitilizedError, NoEmailRecipientsError
from pooldlib.api import communication as email

from tests.base import PooldLibPostgresBaseTest


class TestAddEmailRecipients(PooldLibPostgresBaseTest):

    def setUp(self):
        self.SMTP_patcher = patch('pooldlib.api.communication.smtplib')
        self.SMTP_patcher.start()
        self.email = email.Email(None, None)
        self.old_sender = self.email.sender
        self.addCleanup(self.SMTP_patcher.stop)

    def test_update_sender(self):
        assert_equal(self.old_sender, self.email.sender)
        self.email.sender = 'Test Sender <sender@example.com>'
        assert_equal('Test Sender <sender@example.com>', self.email.sender)


class TestLoginSMTP(PooldLibPostgresBaseTest):

    def setUp(self):
        self.SMTP_patcher = patch('pooldlib.api.communication.smtplib')
        self.SMTP_patcher.start()
        self.email = email.Email(None, None)
        self.addCleanup(self.SMTP_patcher.stop)

    def test_login(self):
        assert_true(self.email._connected)
        assert_false(self.email._logged_in)

        self.email.login('testuser', 'testpass')

        assert_true(self.email._logged_in)
        self.email.server.login.assert_called_once_with('testuser', 'testpass')
        assert_true(self.email._logged_in)

    @raises(SMTPConnectionNotInitilizedError)
    def test_login_not_connected(self):
        self.email._connected = False
        assert_false(self.email._connected)
        assert_false(self.email._logged_in)
        self.email.login('testuser', 'testpass')


class TestDisconnectSMTP(PooldLibPostgresBaseTest):

    def setUp(self):
        self.SMTP_patcher = patch('pooldlib.api.communication.smtplib')
        self.SMTP_patcher.start()
        self.email = email.Email(None, None)
        self.addCleanup(self.SMTP_patcher.stop)

    def test_simple_disconnect(self):
        self.email._logged_in = True
        assert_true(self.email._connected)
        assert_true(self.email._logged_in)

        self.email.disconnect()
        self.email.server.quit.assert_called_once_with()

        assert_false(self.email._connected)
        assert_false(self.email._logged_in)

    def test_disconnect_not_connected(self):
        self.email._connected = False
        assert_false(self.email._connected)
        assert_false(self.email._logged_in)

        self.email.disconnect()
        assert_equal(0, self.email.server.quit.call_count)

        assert_false(self.email._connected)
        assert_false(self.email._logged_in)


class TestSendEmail(PooldLibPostgresBaseTest):

    def setUp(self):
        self.SMTP_patcher = patch('pooldlib.api.communication.smtplib')
        self.SMTP_patcher.start()
        self.email = email.Email(None, None)
        self.addCleanup(self.SMTP_patcher.stop)

    @raises(NoEmailRecipientsError)
    def test_send_no_recipients(self):
        self.email.msg_root = 'Content'
        self.email.send()

    def test_send_with_recipients(self):
        self.email.msg_root = MagicMock()
        self.email.msg_root.as_string = Mock(return_value='Content')

        self.email.sender = sender = 'Test Sender <sender@example.com>'

        address_one = 'Test User One <test_user_one@example.com>'
        address_two = 'Test User Two <test_user_two@example.com>'

        to_string = '%s, %s' % (address_one, address_two)
        self.email.recipients = [address_one, address_two]
        self.email.send()

        self.email.server.sendmail.assert_called_once_with(sender, [address_one, address_two], 'Content')


class TestAddEmailRecipients(PooldLibPostgresBaseTest):

    def setUp(self):
        self.SMTP_patcher = patch('pooldlib.api.communication.smtplib')
        self.SMTP_patcher.start()
        self.email = email.Email(None, None)
        self.addCleanup(self.SMTP_patcher.stop)

        self.username_a = uuid().hex
        self.name_a = '%s %s' % (self.username_a[:16], self.username_a[16:])
        self.email_a = '%s@example.com' % self.username_a
        self.user_a = self.create_user(self.username_a, self.name_a, self.email_a)

        self.username_b = uuid().hex
        self.name_b = '%s %s' % (self.username_b[:16], self.username_b[16:])
        self.email_b = '%s@example.com' % self.username_b
        self.user_b = self.create_user(self.username_b, self.name_b, self.email_b)

    def test_simple_add(self):
        assert_true(not self.email.recipients)
        address = 'Test User <test_user@example.com>'
        self.email.add_recipient(address)
        assert_equal([address], self.email.recipients)

    def test_add_with_user(self):
        assert_true(not self.email.recipients)
        self.email.add_recipient(self.user_a)
        address = '%s <%s>' % (self.user_a.name, self.user_a.email)
        assert_equal([address], self.email.recipients)

    def test_simple_add_multiple(self):
        assert_true(not self.email.recipients)
        address_one = 'Test User One <test_user_one@example.com>'
        address_two = 'Test User Two <test_user_two@example.com>'
        self.email.add_recipients([address_one, address_two])
        assert_equal([address_one, address_two], self.email.recipients)

    def test_add_multiple_with_users(self):
        assert_true(not self.email.recipients)
        self.email.add_recipients([self.user_a, self.user_b])
        address_one = '%s <%s>' % (self.user_a.name, self.user_a.email)
        address_two = '%s <%s>' % (self.user_b.name, self.user_b.email)
        assert_equal([address_one, address_two], self.email.recipients)

    def test_simple_add_multiple_via_setter(self):
        assert_true(not self.email.recipients)
        address_one = 'Test User One <test_user_one@example.com>'
        address_two = 'Test User Two <test_user_two@example.com>'
        self.email.recipients = [address_one, address_two]
        assert_equal([address_one, address_two], self.email.recipients)

    def test_add_multiple_with_users_via_setter(self):
        assert_true(not self.email.recipients)
        self.email.recipients = [self.user_a, self.user_b]
        address_one = '%s <%s>' % (self.user_a.name, self.user_a.email)
        address_two = '%s <%s>' % (self.user_b.name, self.user_b.email)
        assert_equal([address_one, address_two], self.email.recipients)


class TestSetHTMLContent(PooldLibPostgresBaseTest):

    def setUp(self):
        self.SMTP_patcher = patch('pooldlib.api.communication.smtplib')
        self.SMTP_patcher.start()
        self.email = email.HTMLEmail(None, None)
        self.addCleanup(self.SMTP_patcher.stop)

        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.user_email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.user_email)

        self.email.add_recipient(self.user)

    @patch('pooldlib.api.communication.MIMEText', autospec=True)
    def test_simple_set(self, mock_MIMEText):
        mock_message = Mock()
        self.email.msg_alternative = mock_message
        body = 'Test body content.'
        self.email.set_content(body, body)
        assert_equal(2, mock_MIMEText.call_count)
        mock_MIMEText.assert_any_call(body, _subtype='plain', _charset='utf-8')
        mock_MIMEText.assert_any_call(body, _subtype='html', _charset='utf-8')

        assert_equal(2, mock_message.attach.call_count)


class TestAttachImage(PooldLibPostgresBaseTest):

    def setUp(self):
        self.SMTP_patcher = patch('pooldlib.api.communication.smtplib')
        self.SMTP_patcher.start()
        self.email = email.HTMLEmail(None, None)
        self.addCleanup(self.SMTP_patcher.stop)

        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.user_email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.user_email)

        self.email.add_recipient(self.user)

    @patch('pooldlib.api.communication.MIMEImage', autospec=True)
    def test_attach_image_fp(self, mock_MIMEImage):
        mock_image_msg = Mock()
        mock_MIMEImage.return_value = mock_image_msg
        mock_message = Mock()
        self.email.msg_related = mock_message
        mock_fp = Mock()
        mock_data = mock_fp.read()
        self.email.attach_img(mock_fp, 'test_img')

        assert_equal(1, mock_MIMEImage.call_count)

        mock_MIMEImage.assert_called_once_with(mock_data)
        assert_equal(2, mock_image_msg.add_header.call_count)
        mock_image_msg.add_header.assert_any_calls('Content-ID', '<test_img>')
        mock_image_msg.add_header.assert_any_calls('Content-Disposition', 'inline')

        mock_message.attach.assert_called_once_with(mock_image_msg)

    @patch('pooldlib.api.communication.MIMEImage', autospec=True)
    def test_attach_image_fp_img_id_strip(self, mock_MIMEImage):
        mock_image_msg = Mock()
        mock_MIMEImage.return_value = mock_image_msg

        mock_message = Mock()
        self.email.msg_related = mock_message

        mock_fp = Mock()
        mock_data = mock_fp.read()

        self.email.attach_img(mock_fp, '<test_img>')

        assert_equal(1, mock_MIMEImage.call_count)

        mock_MIMEImage.assert_called_once_with(mock_data)
        assert_equal(2, mock_image_msg.add_header.call_count)
        mock_image_msg.add_header.assert_any_calls('Content-ID', '<test_img>')
        mock_image_msg.add_header.assert_any_calls('Content-Disposition', 'inline')

        mock_message.attach.assert_called_once_with(mock_image_msg)

    @patch('pooldlib.api.communication.MIMEImage', autospec=True)
    @patch('pooldlib.api.communication.os', autospec=True)
    def test_attach_image_data(self, mock_os, mock_MIMEImage):
        mock_image_msg = Mock()
        mock_MIMEImage.return_value = mock_image_msg

        mock_message = Mock()
        self.email.msg_related = mock_message

        mock_img_data = Mock(spec=dict)

        self.email.attach_img(mock_img_data, 'test_img')

        assert_equal(1, mock_MIMEImage.call_count)
        mock_MIMEImage.assert_called_once_with(mock_img_data)

        assert_equal(0, mock_os.path.isfile.call_count)
        assert_equal(2, mock_image_msg.add_header.call_count)
        mock_image_msg.add_header.assert_any_calls('Content-ID', '<test_img>')
        mock_image_msg.add_header.assert_any_calls('Content-Disposition', 'inline')

        mock_message.attach.assert_called_once_with(mock_image_msg)

    @patch('pooldlib.api.communication.MIMEImage', autospec=True)
    @patch('pooldlib.api.communication.os', autospec=True)
    def test_attach_image_fpath(self, mock_os, mock_MIMEImage):
        mock_os.path.isfile.return_value = True

        mock_image_msg = Mock()
        mock_MIMEImage.return_value = mock_image_msg

        mock_message = Mock()
        self.email.msg_related = mock_message

        mock_img_fpath = '/im/a/little/tea/pot.png'

        mock_img_data = Mock()
        mock_open_inst = mock_open(read_data=mock_img_data)
        with patch('__builtin__.open', mock_open_inst):
            self.email.attach_img(mock_img_fpath, 'test_img')

        mock_os.path.isfile.assert_called_once_with(mock_img_fpath)
        mock_open_inst.assert_called_once_with(mock_img_fpath, 'rb')

        assert_equal(1, mock_MIMEImage.call_count)
        mock_MIMEImage.assert_called_once_with(mock_img_data)
        assert_equal(2, mock_image_msg.add_header.call_count)
        mock_image_msg.add_header.assert_any_calls('Content-ID', '<test_img>')
        mock_image_msg.add_header.assert_any_calls('Content-Disposition', 'inline')

        mock_message.attach.assert_called_once_with(mock_image_msg)
