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

LOAD_PKG_RESOURCES_EXT = True
"""
Load extensions from pkg_resources entry points.

This allows for extensions to become available simply by installing them.

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
