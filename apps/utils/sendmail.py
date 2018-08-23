#!/usr/bin/env python
# vim:fileencoding=utf-8

from email.mime.text import MIMEText
from email.header import Header
import smtplib
import time
import urllib
import urllib2

mail_server = "mail.boluolc.com"
mail_port = 25
mail_user = "service@boluolc.com"
mail_passwd = "boluo123"

class baseSendEmail(object):

    server = mail_server
    port = mail_port
    user = mail_user
    passwd = mail_passwd

    def __init__(self, content=None, send_email_list=None,
                 server=None, mail_from=None, subject=None, send_limit=True):

        self.send_email_list = send_email_list
        self.content = content
        self.send_limit = send_limit
        self.mail_from = mail_from or mail_user
        self.subject = subject

    def get_content(self):
        raise NotImplementedError("You must define a get_content method on %s"
                                  % self.__class__.__name__)

    def get_emails_to(self):
        raise NotImplementedError("You must define a get_emails_to method on %s"
                                  % self.__class__.__name__)

    def is_alerted(self):
        raise NotImplementedError("You must define a is_alerted method on %s"
                                  % self.__class__.__name__)

    def send(self):
        if self.send_limit:
            if not self.send_email_list:
                self.send_email_list = self.get_emails_to()
            if not self.content:
               self.content = self.get_content()
            self._send()
        else:
            self.send_fail_info()

    def _send(self):
        msg = MIMEText(self.content,'html','utf-8')
        msg['Subject'] = Header(self.subject, 'utf-8')
        msg['From'] = self.mail_from
        msg['date'] = time.strftime('%a, %d %b %Y %H:%M:%S %z')
        self.send_email_list = list(set(self.send_email_list))
        smtp=smtplib.SMTP()
        smtp.connect(self.server, self.port)
        smtp.ehlo()
        smtp.starttls()
        smtp.login(self.user, self.passwd)
        for mail_to in self.send_email_list:
            msg['To'] = mail_to
            smtp.sendmail(self.mail_from, mail_to, msg.as_string())
        smtp.quit()
        return 'success'

    def send_fail_info(self):
        raise NotImplementedError("You must define a send_fail_info method on %s"
                                  % self.__class__.__name__)
