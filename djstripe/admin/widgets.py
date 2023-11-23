"""
Django Administration interface custom widget definitions
"""

import json

from django.forms.widgets import Textarea


class CustomTextAreaWidget(Textarea):
    def format_value(self, value):
        """
        Return a value as it should appear when rendered in a template.
        """
        value = json.loads(value)
        value = json.dumps(value, indent=4)
        return super().format_value(value)
