from stripe import api_key
from stripe.resource import convert_to_stripe_object


def convert_to_fake_stripe_object(response):
    return convert_to_stripe_object(resp=response, api_key=api_key, account="test_account")
