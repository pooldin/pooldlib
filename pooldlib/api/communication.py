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
    """Emails sending facility for pooldlib.api. Sender can be updated by either
    setting the ``Email.sender`` property directly or using the ``Email.update_sender``
    method. ``Email.sender`` defaults to 'Poold Inc. <no-reply@poold.in>'.
    """

    def __init__(self, host, port, use_ssl=True, disclose_recipients=False, sender=None, local_hostname=None):
        self._recipients = list()
        if sender is None:
            sender = 'Poold Inc. <no-reply@poold.in>'
        self.sender = sender
        self.subject = None
        self.disclose_recipients = disclose_recipients
        self._recipients = list()
        self.msg_root = None
        self.server = smtplib.SMTP(host=host,
                                   port=port,
                                   local_hostname=local_hostname)
        self.server.ehlo()
        if use_ssl:
            self.server.starttls()
            self.server.ehlo()
        self._connected = True
        self._logged_in = False
        charset.add_charset('utf-8', charset.QP, charset.QP)

    def __del__(self):
        self.disconnect()

    def disconnect(self):
        if self._connected:
            self.server.quit()
        self._connected = False
        self._logged_in = False

    def login(self, username, password):
        if not self._connected:
            msg = 'Not currently connected to a SMTP server. This should have '\
                  'happened at initialization, something is wrong.'
            raise SMTPConnectionNotInitilizedError(msg)

        if not self._logged_in:
            self.server.login(username, password)
            self._logged_in = True

    @property
    def recipients(self):
        return self._recipients

    @recipients.setter
    def recipients(self, recipients):
        self.add_recipients(recipients)

    def set_subject(self, subject):
        self.subject = subject

    def add_recipient(self, recipient):
        """Add a recipients to the recipients list
        """
        if not isinstance(recipient, str):
            user = recipient
            recipient = '%s ' % user.name if user.name is not None else ''
            recipient += '<%s>' % user.email
        self._recipients.append(recipient)\
            if recipient not in self._recipients\
            else None  # else required for correct python syntax

    def add_recipients(self, recipients):
        """Set recipient list directly.  Recipient can be either email
        addresses as strings, or :class:`pooldlib.postgres.models.User`
        instances.  User object instances expected to have email addresses
        associated with them.

        :param recipient: Recipient to add to the recipient list.
        :type recipient: list of strings or :class:`pooldlib.postgres.models.User`
        """
        for recipient in recipients:
            if isinstance(recipient, str):
                self._recipients.append(recipient)
            elif isinstance(recipient, UserModel):
                self.add_recipient(recipient)
            else:
                msg = 'Unknown recipients type %s. Recipients must be '\
                      'of type str or pooldlib.postgres.User'
                raise TypeError(msg)

    def send(self):
        if not self.msg_root:
            msg = 'Please set content via ``set_content`` prior to calling ``send``.'
            raise NoContentEmailError(msg)
        if not self.recipients:
            msg = 'You must add one or more recipients to the message prior to '\
                  'calling send!'
            raise NoEmailRecipientsError(msg)
        self.msg_root['From'] = self.sender
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
        self.msg_root = MIMEText(content)


class HTMLEmail(Email):

    def __init__(self, host, port, sender=None, local_hostname=None):
        super(HTMLEmail, self).__init__(host, port, sender=sender, local_hostname=local_hostname)
        self.msg_root = MIMEMultipart('mixed')
        self.msg_root.preamble = 'This is a multi-part message in MIME format.'
        #self.msg_root = MIMEMultipart('related')

        self.msg_related = MIMEMultipart('related')
        self.msg_root.attach(self.msg_related)

        self.msg_alternative = MIMEMultipart('alternative')
        self.msg_related.attach(self.msg_alternative)
        #self.msg_root.attach(self.msg_alternative)

    def set_content(self, html, text):
        # For the curious, some email clients are too daft to pay attention to
        # content-type, and instead display the last alternative they
        # understand. I.e. if 'Content-Type: text/plain' is the last MIME added
        # to a 'Content-Type: multipart/related', those shitty apps (gmail is
        # one...) will display the FUCKING PLAIN TEXT.
        # NOTE :: A metric fuck-ton of time was waisted figuring the above out.
        # NOTE :: Learn from my pain. <brian@poold.in>
        # NOTE :: http://www.violato.net/blog/others/110-gmail-email-formatting-issue-with-multipartalternative-mime-entry
        text = MIMEText(str.encode(text, 'utf8'), _subtype='plain', _charset='utf-8')
        self.msg_alternative.attach(text)

        html = MIMEText(str.encode(html, 'utf8'), _subtype='html', _charset='utf-8')
        self.msg_alternative.attach(html)

    def attach_img(self, image, content_id):
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
