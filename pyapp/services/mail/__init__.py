"""
Mail service
~~~~~~~~~~~~

    *Provides a simple service for sending email.*
    
"""
from __future__ import absolute_import

from pyapp.conf.helpers import NamedPluginFactory

from .backends.base import BaseEmailBackend


class MailBackendFactory(NamedPluginFactory):
    """
    Factory for creating instances of back-ends.
    """
    def create_instance(self, name=None, fail_silently=False):
        instance_type, kwargs = self.get_definition(name)
        return instance_type(**kwargs)

get_connection = MailBackendFactory('EMAIL_BACKENDS', BaseEmailBackend)


def send_mail(subject, message, from_email, recipient_list,
              auth_user=None, auth_password=None, fail_silently=False,
              connection=None, html_message=None):
    """
    Easy wrapper for sending a single message to a recipient list. All members
    of the recipient list will see the other recipients in the 'To' field.
    If auth_user is None, use the EMAIL_HOST_USER setting.
    If auth_password is None, use the EMAIL_HOST_PASSWORD setting.
    Note: The API for this method is frozen. New code wanting to extend the
    functionality should use the EmailMessage class directly.
    """
    connection = connection or get_connection(
        user=auth_user,
        password=auth_password,
        fail_silently = fail_silently,
    )
    mail = EmailMultiAlternatives(subject, message, from_email, recipient_list, connection=connection)
    if html_message:
        mail.attach_alternative(html_message, 'text/html')

    return mail.send()