import datetime

from django.test import TestCase
from django.utils import timezone

from ..models import convert_tstamp


class TestTimestampConversion(TestCase):
    
    def test_conversion_without_field_name(self):
        stamp = convert_tstamp(1365567407)
        self.assertEquals(
            stamp,
            datetime.datetime(2013, 4, 10, 4, 16, 47, tzinfo=timezone.utc)
        )
    
    def test_conversion_with_field_name(self):
        stamp = convert_tstamp({"my_date": 1365567407}, "my_date")
        self.assertEquals(
            stamp,
            datetime.datetime(2013, 4, 10, 4, 16, 47, tzinfo=timezone.utc)
        )
    
    def test_conversion_with_invalid_field_name(self):
        stamp = convert_tstamp({"my_date": 1365567407}, "foo")
        self.assertEquals(
            stamp,
            None
        )
