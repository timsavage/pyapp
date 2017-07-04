# -*- coding: utf-8 -*-
"""
######################################
PyApp - A python application framework
######################################

*Let us handle the boring stuff!*

"""
from __future__ import unicode_literals

import logging
import os

from pkg_resources import get_distribution, DistributionNotFound

# Declare name spaces
__import__('pkg_resources').declare_namespace('pyapp.ext')

# Configure a default null handler for logging.
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Get installed version
try:
    _dist = get_distribution('pyApp')
    # Normalise case for Windows systems
    dist_loc = os.path.normcase(_dist.location)
    here = os.path.normcase(__file__)
    if not here.startswith(os.path.join(dist_loc, 'pyApp')):
        # not installed, but there is another version that *is*
        raise DistributionNotFound
except DistributionNotFound:
    __version__ = 'Please install pyApp via a package.'
else:
    __version__ = _dist.version

__author__ = 'Tim Savage <tim@savage.company>'
