"""
Default Settings
~~~~~~~~~~~~~~~~

.. auto
"""
from __future__ import unicode_literals

DEBUG = False
"""
Enable debug mode
"""


###############################################################################
# Extensions

EXT = []
"""
List of extensions currently in use. Will cause pyapp to import any checks,
load default_configuration etc that are supplied by any extension.

Should be a list of modules to import eg::

    EXT = (
        'pyapp_sqlalchemy',
        'my_custom_extension',
    )
    
"""


###############################################################################
# Logging

LOGGING = {}
"""
Logging configuration.

The following configuration is applied by default::

    LOGGING = {
        'formatters': {
            'default': {
                'format': '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'stream': 'ext://sys.stderr',
            },
        },
        'root': {
            # 'level' : 'INFO',  # Set from command line arg parser.
            'handlers': ['console'],
        }
    }

"""


###############################################################################
# Checks

CHECK_LOCATIONS = []
"""
Locations to import to ensure checks are registered.
"""


###############################################################################
# Email

EMAIL_BACKENDS = {
    'default': ('pyapp.services.mail.backends.smtp.SmtpBackend', {}),
}
"""
Email Server backends.

The default configuration is to use a local SMTP server::

    EMAIL_BACKENDS = {
        'default': ('pyapp.services.mail.backends.smtp.SmtpBackend', {
            'host': 'localhost',
            'port': 25
        })
    }
"""

DEFAULT_FROM_EMAIL = 'admin@localhost'
"""
The default from email address.
"""
