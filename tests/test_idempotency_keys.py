from django.test import TestCase

from djstripe.models import IdempotencyKey
from djstripe.settings import get_idempotency_key


class IdempotencyKeyTest(TestCase):
    def test_generate_idempotency_key(self):
        key1 = get_idempotency_key("customer", "create:1", False)
        key2 = get_idempotency_key("customer", "create:1", False)
        self.assertTrue(key1 == key2)

        key3 = get_idempotency_key("customer", "create:2", False)
        self.assertTrue(key1 != key3)

        key4 = get_idempotency_key("charge", "create:1", False)
        self.assertTrue(key1 != key4)

        self.assertEquals(IdempotencyKey.objects.count(), 3)
        key1_obj = IdempotencyKey.objects.get(action="customer:create:1", livemode=False)
        self.assertFalse(key1_obj.is_expired)
        self.assertEquals(str(key1_obj), str(key1_obj.uuid))
