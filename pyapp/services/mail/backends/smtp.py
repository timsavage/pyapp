"""
Mail backend SMTP
~~~~~~~~~~~~~~~~~

SMTP mail backend.

"""
from __future__ import absolute_import

import smtplib
import socket
import ssl

from .base import BaseMailBackend


class SmtpBackend(BaseMailBackend):
    """
    SMTP mail backend.
    
    """
    def __init__(self, host='localhost', port=smtplib.SMTP_PORT, username='', password='',
                 use_tls=False, fail_silently=False, use_ssl=False, timeout=None,
                 ssl_keyfile=None, ssl_certfile=None):
        super(SmtpBackend, self).__init__(fail_silently)

        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.ssl_keyfile = ssl_keyfile
        self.ssl_certfile = ssl_certfile
        if self.use_ssl and self.use_tls:
            raise ValueError("use_tls/use_ssl are mutually exclusive, only set one of those settings to True.")

        self.connection = None

    @property
    def connection_class(self):
        """
        :rtype: smtplib.SMTP | smtplib.SMTP_SSL
        """
        return smtplib.SMTP_SSL if self.use_ssl else smtplib.SMTP

    def open(self):
        """
        Open connection to SMTP server
        """
        if self.connection:
            # Nothing to do if the connection is already open.
            return False

        # If local_hostname is not specified, socket.getfqdn() gets used.
        # For performance, we use the cached FQDN for local_hostname.
        connection_params = {}
        if self.timeout is not None:
            connection_params['timeout'] = self.timeout
        if self.use_ssl:
            connection_params.update({
                'keyfile': self.ssl_keyfile,
                'certfile': self.ssl_certfile,
            })

        try:
            self.connection = self.connection_class(self.host, self.port, **connection_params)
            if self.use_tls:
                self.connection.starttls(keyfile=self.ssl_keyfile, certfile=self.ssl_certfile)
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True

        except (smtplib.SMTPException, socket.error):
            if not self.fail_silently:
                raise

    def close(self):
        """
        Close connection to SMTP server.
        """
        if self.connection is None:
            return

        try:
            try:
                self.connection.quit()

            except (ssl.SSLError, smtplib.SMTPServerDisconnected):
                # This happens when calling quit() on a TLS connection
                # sometimes, or when the connection was already disconnected
                # by the server.
                self.connection.close()

            except smtplib.SMTPException:
                if self.fail_silently:
                    return
                raise

        finally:
            self.connection = None

    def send_message(self, mail_messages):
        if not mail_messages:
            return

