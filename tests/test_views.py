from __future__ import unicode_literals
import decimal
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from mock import patch

from . import TRANSFER_CREATED_TEST_DATA
from djstripe.models import Event, Transfer


class TestWebhook(TestCase):
    pass