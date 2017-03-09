import contextlib

from django.test import SimpleTestCase
import mock

from djstripe.signals import stripe_receiver, WEBHOOK_SIGNALS


@contextlib.contextmanager
def create_stripe_receiver(signal):
    """ Same logic as found in mock_django [0], but for the stripe receiver method.

     [0]: https://github.com/dcramer/mock-django/blob/master/mock_django/signals.py
    """
    receiver = mock.Mock()

    stripe_receiver(signal)(receiver)

    yield receiver

    if isinstance(signal, (list, tuple)):
        for s in signal:
            WEBHOOK_SIGNALS[s].disconnect(receiver)
    else:
        WEBHOOK_SIGNALS[signal].disconnect(receiver)


class TestStripeReceiver(SimpleTestCase):
    def test_single_signal(self):
        with create_stripe_receiver('account.updated') as receiver:
            WEBHOOK_SIGNALS['account.updated'].send(mock.Mock())
            WEBHOOK_SIGNALS['customer.updated'].send(mock.Mock())
            WEBHOOK_SIGNALS['customer.created'].send(mock.Mock())

            self.assertTrue(receiver.called)
            self.assertEqual(receiver.call_count, 1)

    def test_multiple_signals(self):
        with create_stripe_receiver(['account.updated', 'customer.updated']) as receiver:
            WEBHOOK_SIGNALS['account.updated'].send(mock.Mock())
            WEBHOOK_SIGNALS['customer.updated'].send(mock.Mock())
            WEBHOOK_SIGNALS['customer.created'].send(mock.Mock())

            self.assertTrue(receiver.called)
            self.assertEqual(receiver.call_count, 2)
