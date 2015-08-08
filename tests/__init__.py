from django.conf import settings
from stripe.resource import convert_to_stripe_object


def convert_to_fake_stripe_object(response):
    return convert_to_stripe_object(resp=response, api_key=settings.STRIPE_SECRET_KEY, account="test_account")
