"""
.. module:: dj-stripe.tests.test_context_processors
   :synopsis: dj-stripe Context Processor Tests.

   NOTE: This file will be removed along with the deprecated context_processor.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from unittest2 import TestCase as AssertWarnsEnabledTestCase


class TestDeprecationWarning(AssertWarnsEnabledTestCase):
    """
    Tests the deprecation warning set in the context_processors file.
    See https://docs.python.org/3.4/library/warnings.html#testing-warnings
    """

    def test_deprecation(self):
        with self.assertWarns(DeprecationWarning):
            from djstripe.context_processors import djstripe_settings
            djstripe_settings(None)
