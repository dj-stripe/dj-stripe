from django.template import Template, Context
from django.test import TestCase


class TestDivisionTag(TestCase):

    def test_division_good(self):
        template = Template('{% load djstripe_tags %}{{ 3|djdiv:2 }}')
        context = Context({})
        rendered = template.render(context)
        self.assertEqual(rendered, "1.5")

    def test_division_bad(self):
        template = Template('{% load djstripe_tags %}{{ 3|djdiv:"bad" }}')
        context = Context({})
        rendered = template.render(context)
        self.assertEqual(rendered, "")
