from django.template import Template, Context
from django.test import TestCase


class TestHierarchy(TestCase):

    def test_unknow_hierarchy(self):
        template = Template('{% load djstripe_tags %}{{ "test999"|djstripe_plan_level }}')
        context = Context({})
        rendered = template.render(context)
        self.assertEqual(rendered, "-1")

    def test_correct_hierarchy(self):
        template = Template('{% load djstripe_tags %}{{ "test_deletion"|djstripe_plan_level }}')
        context = Context({})
        rendered = template.render(context)
        self.assertEqual(rendered, "2")
