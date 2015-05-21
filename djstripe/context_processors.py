# -*- coding: utf-8 -*-
"""
.. module:: djstripe.context_processors
   :synopsis: dj-stripe Context Processors.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

import warnings


def djstripe_settings(request):
    warnings.warn("This context processor is deprecated. It will be removed in dj-stripe 1.0.", DeprecationWarning)
    return None
