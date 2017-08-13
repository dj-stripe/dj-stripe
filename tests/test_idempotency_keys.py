from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import timedelta

from django.test import TestCase
from django.utils.timezone import now

from djstripe.models import IdempotencyKey
from djstripe.settings import get_idempotency_key
from djstripe.utils import clear_expired_idempotency_keys


class IdempotencyKeyTest(TestCase):
    def test_generate_idempotency_key(self):
        key1 = get_idempotency_key("customer", "create:1", False)
        key2 = get_idempotency_key("customer", "create:1", False)
        self.assertTrue(key1 == key2)

        key3 = get_idempotency_key("customer", "create:2", False)
        self.assertTrue(key1 != key3)

        key4 = get_idempotency_key("charge", "create:1", False)
        self.assertTrue(key1 != key4)

        self.assertEqual(IdempotencyKey.objects.count(), 3)
        key1_obj = IdempotencyKey.objects.get(action="customer:create:1", livemode=False)
        self.assertFalse(key1_obj.is_expired)
        self.assertEqual(str(key1_obj), str(key1_obj.uuid))

    def test_clear_expired_idempotency_keys(self):
        expired_key = get_idempotency_key("customer", "create:1", False)
        expired_key_obj = IdempotencyKey.objects.get(uuid=expired_key)
        expired_key_obj.created = now() - timedelta(hours=25)
        expired_key_obj.save()

        valid_key = get_idempotency_key("customer", "create:2", False)

        self.assertEqual(IdempotencyKey.objects.count(), 2)

        clear_expired_idempotency_keys()

        self.assertEqual(IdempotencyKey.objects.count(), 1)
        self.assertEqual(str(IdempotencyKey.objects.get().uuid), valid_key)
