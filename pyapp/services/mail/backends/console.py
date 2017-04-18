"""
Mail backend Console
~~~~~~~~~~~~~~~~~~~~

A mail backend that echos the sent message to the console.

"""
from __future__ import absolute_import

import sys

from .base import BaseEmailBackend


class EmailBackend(BaseEmailBackend):
    """
    Console backend
    """
    def __init__(self, stream=sys.stdout, **kwargs):
        super(EmailBackend, self).__init__(**kwargs)
        self.stream = stream

    def write_message(self, message):
        pass

    def send_message(self, mail_messages):
        if not mail_messages:
            return

        msg_count = 0
        try:
            for message in mail_messages:
                self.write_message(message)
                self.stream.flush()
                msg_count += 1

        except Exception:
            if not self.fail_silently:
                raise
        return msg_count
