"""
dj-stripe Price model tests
"""
from django.test import TestCase

from djstripe.models import Price


class PriceTest(TestCase):
    def test_price_name(self):
        price = Price(id="price_xxxx", nickname="Price Test")
        assert str(price) == "Price Test"
        price.nickname = ""
        assert str(price) == "price_xxxx"
