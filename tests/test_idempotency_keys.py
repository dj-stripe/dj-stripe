from datetime import timedelta

from django.test import TestCase
from django.utils.timezone import now

from djstripe.models import IdempotencyKey
from djstripe.settings import djstripe_settings
from djstripe.utils import clear_expired_idempotency_keys


class IdempotencyKeyTest(TestCase):
    def test_generate_idempotency_key(self):
        key1 = djstripe_settings.create_idempotency_key("customer", "create:1", False)
        key2 = djstripe_settings.create_idempotency_key("customer", "create:2", False)
        self.assertTrue(key1 != key2)

        self.assertEqual(IdempotencyKey.objects.count(), 2)
        key1_obj = IdempotencyKey.objects.get(
            action="customer:create:1:", livemode=False
        )
        self.assertFalse(key1_obj.is_expired)
        self.assertEqual(str(key1_obj), str(key1_obj.uuid))

    def test_clear_expired_idempotency_keys(self):
        expired_key = djstripe_settings.create_idempotency_key(
            "customer", "create:1", False
        )
        expired_key_obj = IdempotencyKey.objects.get(uuid=expired_key)
        expired_key_obj.created = now() - timedelta(hours=25)
        expired_key_obj.save()

        valid_key = djstripe_settings.create_idempotency_key(
            "customer", "create:2", False
        )

        self.assertEqual(IdempotencyKey.objects.count(), 2)

        clear_expired_idempotency_keys()

        self.assertEqual(IdempotencyKey.objects.count(), 1)
        self.assertEqual(str(IdempotencyKey.objects.get().uuid), valid_key)

    def test_update_action_field(self):
        """Test for the update_action_field staticmethod of the
        IdempotencyKey class."""
        stripe_obj = {"id": "fakefakefake_0001"}
        # create idempotency key
        uuid = djstripe_settings.create_idempotency_key("customer", "create", False)
        key_obj = IdempotencyKey.objects.get(uuid=uuid)
        action = key_obj.action

        # Invoke update_action_field()
        IdempotencyKey.update_action_field(uuid, stripe_obj)

        key_obj.refresh_from_db()

        # assert action got updated with the id of the json passed
        assert key_obj.action == f"{action}{stripe_obj['id']}"
