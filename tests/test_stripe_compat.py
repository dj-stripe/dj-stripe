from unittest import TestCase
from stripe import StripeObject
import djstripe._stripe_compat


class TestStripeObjectCompat(TestCase):
    def test_stripe_object_dict_compatibility(self):
        # Verify the mapping-style methods are present on the StripeObject class
        for method_name in ("get", "items", "keys", "values", "pop", "setdefault"):
            self.assertTrue(
                hasattr(StripeObject, method_name),
                f"StripeObject should have method {method_name}",
            )
            self.assertTrue(
                callable(getattr(StripeObject, method_name)),
                f"StripeObject.{method_name} should be callable",
            )

        # Construct a StripeObject using construct_from to test instance behavior
        obj = StripeObject.construct_from({"id": "test_id", "foo": "bar"}, "test_key")

        # Test .get()
        self.assertEqual(obj.get("foo"), "bar")
        self.assertEqual(obj.get("id"), "test_id")
        self.assertEqual(obj.get("nonexistent"), None)
        self.assertEqual(obj.get("nonexistent", "default"), "default")

        # Test .keys()
        self.assertIn("foo", obj.keys())
        self.assertIn("id", obj.keys())

        # Test .values()
        self.assertIn("bar", obj.values())
        self.assertIn("test_id", obj.values())

        # Test .items()
        items = dict(obj.items())
        self.assertEqual(items["foo"], "bar")
        self.assertEqual(items["id"], "test_id")

        # Test .setdefault()
        self.assertEqual(obj.setdefault("foo", "new_val"), "bar")  # existing key
        self.assertEqual(obj.setdefault("new_key", "new_val"), "new_val")  # new key
        self.assertEqual(obj.get("new_key"), "new_val")

        # Test .pop()
        self.assertEqual(obj.pop("foo"), "bar")
        self.assertNotIn("foo", obj.keys())
        self.assertEqual(obj.pop("nonexistent", "default_pop"), "default_pop")
        with self.assertRaises(KeyError):
            obj.pop("nonexistent")
