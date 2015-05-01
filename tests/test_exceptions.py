"""
.. module:: dj-stripe.tests.test_exceptions
   :synopsis: dj-stripe Exception Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from django.test.testcases import TestCase

from djstripe.exceptions import SubscriptionCancellationFailure


class TestExceptions(TestCase):

    def _will_raise_subscription_cancellation_failure(self):
        raise SubscriptionCancellationFailure

    def test_raise_subscription_cancellation_failure(self):
        self.assertRaises(SubscriptionCancellationFailure, self._will_raise_subscription_cancellation_failure)
