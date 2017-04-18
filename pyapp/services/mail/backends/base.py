"""
Base class for mail backends
"""


class BaseEmailBackend(object):
    """
    Base class for mail backends.
    
    :py:meth:`BaseMailBackend.open` and :py:meth:`BaseMailBackend.close` can be either called directly
    to control connection to a server or via a context manager::
    
        with backend as connection:
            # Send a mail message
            pass
            
    """
    def __init__(self, fail_silently=False):
        self.fail_silently = fail_silently

    def __enter__(self):
        try:
            self.open()
        finally:
            self.close()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        """
        Open mail sending resource.
        
        This method should be overwritten by backend implementations to control opening
        of mail gateway resources.
        
        The default implementation does nothing.

        """
        pass

    def close(self):
        """
        Close mail sending resource.
        """
        pass

    def send_message(self, mail_messages):
        """
        Send one or more MailMessage objects and return the number of messages sent.
        
        :type mail_messages: list(pyapp.services.mail.MailMessage)
        :rtype: int
        
        """
        raise NotImplementedError('Subclass must implement the send_message method.')
