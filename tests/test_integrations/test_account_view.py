from django.conf import settings
from unittest.case import skip

# Only run tests if the local environment includes these items
if settings.STRIPE_PUBLIC_KEY and settings.STRIPE_SECRET_KEY:
    from django.contrib.auth import get_user_model
    from django.core.urlresolvers import reverse
    from django.test import TestCase

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    from djstripe.models import Customer

    class AccountEmailViewTests(TestCase):
        @skip
        def setUp(self):
            self.url = reverse("djstripe:account")
            self.user = get_user_model().objects.create_user(username="testuser",
                                                             email="test@example.com",
                                                             password="123")

        @skip
        def test_autocreate_customer(self):
            # raise Exception(settings.TEMPLATE_DIRS)

            self.assertEqual(Customer.objects.count(), 0)

            # simply visiting the page should generate a new customer record.
            self.assertTrue(self.client.login(username=self.user.email,
                                              password=self.user.password))
            r = self.client.get(self.url)
            print(r.content)
            self.assertEqual(Customer.objects.count(), 1)
