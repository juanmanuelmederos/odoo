# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" OpenERP core library."""

#----------------------------------------------------------
# Running mode flags (gevent, prefork)
#----------------------------------------------------------
# Is the server running with gevent.
import sys
evented = False
if sys.modules.get("gevent") is not None:
    evented = True

# Is the server running in pefork mode (e.g. behind Gunicorn).
# If this is True, the processes have to communicate some events,
# e.g. database update or cache invalidation. Each process has also
# its own copy of the data structure and we don't need to care about
# locks between threads.
multi_process = False

#----------------------------------------------------------
# libc UTC hack
#----------------------------------------------------------
# Make sure the OpenERP server runs in UTC. This is especially necessary
# under Windows as under Linux it seems the real import of time is
# sufficiently deferred so that setting the TZ environment variable
# in openerp.cli.server was working.
import os
os.environ['TZ'] = 'UTC' # Set the timezone...
import time              # ... *then* import time.
del os
del time

#----------------------------------------------------------
# Shortcuts
#----------------------------------------------------------
# The hard-coded super-user id (a.k.a. administrator, or root user).
SUPERUSER_ID = 1

def registry(database_name=None):
    """
    Return the model registry for the given database, or the database mentioned
    on the current thread. If the registry does not exist yet, it is created on
    the fly.
    """
    if database_name is None:
        import threading
        database_name = threading.currentThread().dbname
    return modules.registry.RegistryManager.get(database_name)

#----------------------------------------------------------
# Configuration
#----------------------------------------------------------
# the default limit for CSV fields in the module is 128KiB, which is not
# quite sufficient to import images to store in attachment. 500MiB is a
# bit overkill, but better safe than sorry I guess
import csv
csv.field_size_limit(500 * 1024 * 1024)

#----------------------------------------------------------
# Imports
#----------------------------------------------------------
from . import addons
from . import conf
from . import loglevels
from . import modules
from . import netsvc
from . import osv
from . import pooler
from . import release
from . import report
from . import service
from . import sql_db
from . import tools
from . import workflow

#----------------------------------------------------------
# Model classes, fields, api decorators, and translations
#----------------------------------------------------------
from . import models
from . import fields
from . import api
from .tools.translate import _

#----------------------------------------------------------
# Other imports, which may require stuff from above
#----------------------------------------------------------
from . import cli
from . import http
