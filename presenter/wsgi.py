"""
WSGI config for gdn-service project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

activate_this = 'bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

from server import app as application