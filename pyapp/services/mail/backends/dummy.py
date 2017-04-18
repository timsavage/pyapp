"""
Dummy mail backend
~~~~~~~~~~~~~~~~~~

A mail backend that pretends ignores email sending.

"""
from __future__ import absolute_import

from .base import BaseEmailBackend


class EmailBackend(BaseEmailBackend):
    """
    Dummy backend
    """
    def send_message(self, mail_messages):
        return len(list(mail_messages))
