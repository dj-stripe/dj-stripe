import os
import sys

docs_dir, _ = os.path.split(__file__)
sys.path.append(os.path.dirname(docs_dir))

SECRET_KEY = "."
INSTALLED_APPS = ["djstripe"]

# Do not remove the code below. See note in docs/index.md.
setup = None
import django  # noqa
from django.apps import apps  # noqa
from django.conf import settings  # noqa

if not apps.ready and not settings.configured:
    django.setup()
