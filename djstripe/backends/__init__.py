from django.core.exceptions import ImproperlyConfigured
from ..settings import DJSTRIPE_BACKEND

# Python 2.7 has an importlib with import_module; for older Pythons,
# Django's bundled copy provides it.
try:
    from importlib import import_module
except ImportError:
    from django.utils.importlib import import_module

def get_backend():
    """
    Return an instance of a dj-stripe backend.

    If the backend cannot be located (e.g., because no such module
    exists, or because the module does not contain a class of the
    appropriate name), ``django.core.exceptions.ImproperlyConfigured``
    is raised.
    
    """
    i = DJSTRIPE_BACKEND.rfind('.')
    module, attr = DJSTRIPE_BACKEND[:i], DJSTRIPE_BACKEND[i+1:]
    try:
        mod = import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured('Error loading dj-stripe backend %s: "%s"' % (module, e))
    try:
        backend_class = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define a dj-stripe backend named "%s"' % (module, attr))
    return backend_class()
