"""
pooldlib.api.communication
===============================

.. currentmodule:: pooldlib.api.communication

"""
import os
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.Utils import formatdate
from email import charset

from pooldlib.exceptions import (SMTPConnectionNotInitilizedError,
                                 NoEmailRecipientsError,
                                 NoContentEmailError)
from pooldlib.postgresql import User as UserModel


class Email(object):
    """Plain text email sending facility for pooldlib.api. Sender can be updated by either
    setting the ``Email.sender`` which defaults to 'Poold Inc. <no-reply@poold.in>'.
    Prior to sending an email:

        - set recipients: ``Email.add_recipient`` or ``Email.add_recipients``
        - set message subject: ``Email.set_subject('subject string')``
        - set message content: ``Email.set_content('plain text email content')``
        - (optional) set sender: ``Email.sender = 'sender name <sender_email@example.com>'``
        - connect to SMTP server: ``Email.connect()``
        - if login to SMTP server is required: ``Email.login('username', 'password')``

    Preferably, after your email(s) have been sent you should call ``Email.disconnect()``.
    If for some reason you forget/neglect to, it will be called **when GC cleans up after you**.
    """

    def __init__(self, host, port, use_ssl=True, disclose_recipients=False, sender=None, local_hostname=None):
        """Initialize an instance of ``pooldlib.api.communication.Email.

        :param host: Addressable name of SMTP server to send email through.
        :type host: string
        :param port: Port on which to connect to SMTP server.
        :type port: int
        :param use_ssl: If true, connect to SMTP server via SSL connection.
                        Default: True
        :type use_ssl: boolean
        :param disclose_recipients: If true, make recipients visible to all
                                    recipients via 'To' header.
                                    Default: False
        :type disclose_recipients: boolean
        :param sender: Email address string to use as sender of generated email(s).
                       Should be of the form 'Sender Name <sender_email@example.com>'
        :type sender: string
        :param local_hostname: The FQDN of the host sending the email.  See smtplib.SMTP.
        :type local_hostname: string
        """
        self._recipients = list()
        if sender is None:
            sender = 'Poold Inc. <no-reply@poold.in>'
        self.sender = sender
        self.subject = None
        self.disclose_recipients = disclose_recipients
        self._recipients = list()
        self.msg_root = None
        self._host = host
        self._port = port
        self._local_hostname = local_hostname
        self._use_ssl = use_ssl
        self._connected = False
        self._logged_in = False
        charset.add_charset('utf-8', charset.QP, charset.QP)

        self.server = smtplib.SMTP(host=None,
                                   port=None,
                                   local_hostname=self._local_hostname)

    def __del__(self):
        self.disconnect()

    def connect(self):
        """Connect to SMTP server. This method must be called prior to ``Email.login``
        (if applicable) and ``Email.send``.

        :raises: :class:`socket.gaierror`
                 :class:`smtplib.SMTPHeloError`
        """
        self.server.connect(host=self._host,
                            port=self._port)
        self.server.ehlo()
        if self._use_ssl:
            self.server.starttls()
            self.server.ehlo()
        self._connected = True

    def disconnect(self):
        """Disconnect from SMTP server.

        :raises: :class:`socket.gaierror`
        """
        if self._connected:
            self.server.quit()
        self._connected = False
        self._logged_in = False

    def login(self, username, password):
        """Login to SMTP server.

        :param username: Username for SMTP server.
        :type username: string
        :param password: Password for SMTP server.
        :type password: string

        :raises: :class:`smtplib.SMTPException`
                 :class:`smtplib.SMTPHeloError`
                 :class:`smtplib.SMTPAuthenticationError`
        """
        if not self._connected:
            msg = 'Not currently connected to a SMTP server. This should have '\
                  'happened at initialization, something is wrong.'
            raise SMTPConnectionNotInitilizedError(msg)

        if not self._logged_in:
            self.server.login(username, password)
            self._logged_in = True

    @property
    def logged_in(self):
        return self._logged_in

    @property
    def recipients(self):
        return self._recipients

    @recipients.setter
    def recipients(self, recipients):
        self.add_recipients(recipients)

    def set_subject(self, subject):
        """Set the subject header for message.

        :param subject: The subject line to set as subject header for message.
        :type subject: string
        """
        self.subject = subject

    def add_recipient(self, recipient):
        """Add a recipients to the recipients list.  Recipient can be either email
        addresses as strings, or :class:`pooldlib.postgres.models.User`
        instances.  User object instances expected to have email addresses
        associated with them.

        :param recipient: Recipient to add to the recipient list.
        :type recipient: list of strings or :class:`pooldlib.postgres.models.User`
        """
        if not isinstance(recipient, basestring):
            user = recipient
            recipient = '%s ' % user.name if user.name is not None else ''
            recipient += '<%s>' % user.email
        self._recipients.append(recipient)\
            if recipient not in self._recipients\
            else None  # else required for correct python syntax

    def add_recipients(self, recipients):
        """Add multiple recipients.  Recipient can be either email
        addresses as strings, or :class:`pooldlib.postgres.models.User`
        instances.  User object instances expected to have email addresses
        associated with them.

        :param recipient: Recipient to add to the recipient list.
        :type recipient: list of strings or :class:`pooldlib.postgres.models.User`
        """
        for recipient in recipients:
            if isinstance(recipient, basestring):
                self._recipients.append(recipient)
            elif isinstance(recipient, UserModel):
                self.add_recipient(recipient)
            else:
                msg = 'Unknown recipients type %s. Recipients must be '\
                      'of type str or pooldlib.postgres.User'
                raise TypeError(msg)

    def send(self):
        """Send the email!

        :raises: :class:`smtplib.SMTPHeloError`
                 :class:`smtplib.SMTPRecipientRefused`
                 :class:`smtplib.SMTPSenderRefused`
                 :class:`smtplib.SMTPDataError`
                 :class:`pooldlib.exceptions.SMTPConnectionNotInitilizedError`
        """
        if not self._connected:
            msg = 'Not currently connected to a SMTP server. Please call '\
                  '``Email.connect prior to attempting to send email.'
            raise SMTPConnectionNotInitilizedError(msg)
        if not self.msg_root:
            msg = 'Please set content via ``set_content`` prior to calling ``send``.'
            raise NoContentEmailError(msg)
        if not self.recipients:
            msg = 'You must add one or more recipients to the message prior to '\
                  'calling send!'
            raise NoEmailRecipientsError(msg)

        self.msg_root['From'] = self.sender
        # We must explicitly set the 'Reply-To' header.
        self.msg_root.add_header('Reply-To', self.sender)
        self.msg_root['Subject'] = self.subject
        self.msg_root['Date'] = formatdate(localtime=False)

        if self.disclose_recipients:
            to_string = ', '.join(self.recipients)
            self.msg_root['To'] = to_string
        else:
            self.msg_root['To'] = self.sender

        self.server.sendmail(self.sender, self.recipients, self.msg_root.as_string())

    def set_content(self, content):
        """Set the plain text content for message.

        :param content: The content of the email.
        :type content: string
        """
        self.msg_root = MIMEText(content)


class HTMLEmail(Email):
    """Emails sending facility for pooldlib.api. Sender can be updated by either
    setting the ``Email.sender`` which defaults to 'Poold Inc. <no-reply@poold.in>'.
    Prior to sending an email:

        - set recipients: ``Email.add_recipient`` or ``Email.add_recipients``
        - set message subject: ``Email.set_subject('subject string')``
        - set message content: ``Email.set_content('html content', 'plain text alternative')``
        - (optional) set sender: ``Email.sender = 'sender name <sender_email@example.com>'``
        - connect to SMTP server: ``Email.connect()``
        - if login to SMTP server is required: ``Email.login('username', 'password')``
    """

    def __init__(self, host, port, sender=None, local_hostname=None):
        """Initialize an instance of ``pooldlib.api.communication.Email.

        :param host: Addressable name of SMTP server to send email through.
        :type host: string
        :param port: Port on which to connect to SMTP server.
        :type port: int
        :param use_ssl: If true, connect to SMTP server via SSL connection.
                        Default: True
        :type use_ssl: boolean
        :param disclose_recipients: If true, make recipients visible to all
                                    recipients via 'To' header.
                                    Default: False
        :type disclose_recipients: boolean
        :param sender: Email address string to use as sender of generated email(s).
                       Should be of the form 'Sender Name <sender_email@example.com>'
        :type sender: string
        :param local_hostname: The FQDN of the host sending the email.  See smtplib.SMTP.
        :type local_hostname: string
        """
        super(HTMLEmail, self).__init__(host, port, sender=sender, local_hostname=local_hostname)
        self.msg_root = MIMEMultipart('mixed')
        self.msg_root.preamble = 'This is a multi-part message in MIME format.'

        self.msg_related = MIMEMultipart('related')
        self.msg_root.attach(self.msg_related)

        self.msg_alternative = MIMEMultipart('alternative')
        self.msg_related.attach(self.msg_alternative)

    def set_content(self, html, text):
        """Set the email content. You **must** provide both HTML and plain text
        versions of the email to comply with standards.  If you don't want to,
        you should consider quitting your job and going to work for Microsoft.

        :param html: The html version of the email to be sent. Any styling needed
                     for the email should be embedded in the HTML. Images can
                     be included via ``Email.attach_img``.
        :type html: string
        :param text: The plain text version of the email to be sent.
        :type text: string

        :raises: :class:`pooldlib.exceptions.GoWorkForBallmerError`
        """
        # For the curious, some email clients are too daft to pay attention to
        # content-type, and instead display the last alternative they
        # understand. I.e. if 'Content-Type: text/plain' is the last MIME added
        # to a 'Content-Type: multipart/related', those shitty apps (gmail is
        # one...) will display the FUCKING PLAIN TEXT.
        # NOTE :: A metric fuck-ton of time was waisted figuring the above out.
        # NOTE :: Learn from my pain. <brian@poold.in>
        # NOTE :: http://www.violato.net/blog/others/110-gmail-email-formatting-issue-with-multipartalternative-mime-entry
        if not text:
            from pooldlib.exceptions import GoWorkForBalmerError
            msg = "You were warned!"
            raise GoWorkForBalmerError(msg)
        text = MIMEText(text.encode('utf8'), _subtype='plain', _charset='utf-8')
        self.msg_alternative.attach(text)

        html = MIMEText(html.encode('utf8'), _subtype='html', _charset='utf-8')
        self.msg_alternative.attach(html)

    def attach_img(self, image, content_id):
        """Attach an image to be used in conjunction with the html alternative
        version of email. The image will be accessible via e.g.
        ``<img src="cid:content_id">``.

        :param image: File pointer, file path, or image binary to be attached
                      to the email.
        :param type: string, file pointer returned by ``open(fpath, 'rb')``
                     or binary image data.
        :param content_id: Content id for image as it will be reference from
                           within related HTML document.
        :type content_id: string
        """
        content_id = content_id.strip('<').strip('>')
        if hasattr(image, 'read'):
            image = image.read()
        if isinstance(image, basestring) and os.path.isfile(image):
            with open(image, 'rb') as fp:
                image = fp.read()

        msg_image = MIMEImage(image)
        msg_image.add_header('Content-ID', '<%s>' % content_id)
        msg_image.add_header('Content-Disposition', 'inline')
        self.msg_related.attach(msg_image)
