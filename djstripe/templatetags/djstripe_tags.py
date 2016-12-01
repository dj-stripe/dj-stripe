# -*- coding: utf-8 -*-
"""
.. module:: djstripe.templatetags.djstripe_tags.

   :synopsis: dj-stripe - Custom tags to be used in templates.

.. moduleauthor:: @kavdev, @pydanny, @chrissmejia, @audreyr
"""
from __future__ import division

from django.template import Library
from .. import settings as djstripe_settings

register = Library()


@register.filter
def djdiv(value, arg):
    """
    Divide the value by the arg, using Python 3-style division that returns floats.

    If bad values are passed in, return the empty string.
    """
    try:
        return value / arg
    except (ValueError, TypeError):
        try:
            return value / arg
        except Exception:
            return ''


division.is_safe = False


@register.filter(name='djstripe_plan_level')
def djstripe_plan_level(name):
    """
    Add support to levels over plans, then you can have different kind of plans with the level same access.

    Use: {{ <plan_name>|djstripe_plan_level }}

    Note: Custom settings setup is needed, please see the documentation for details.
    """
    level = -1
    hierarchy_dict = djstripe_settings.PLAN_HIERARCHY

    for config_level in hierarchy_dict.values():
        if name in config_level["plans"]:
            level = config_level["level"]

    return level
