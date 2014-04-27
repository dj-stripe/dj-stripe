from django.utils.module_loading import import_by_path

from ..settings import DJSTRIPE_BACKEND


def get_backend():
    """
    Return an instance of a dj-stripe backend.
    
    """
    mod = import_by_path(DJSTRIPE_BACKEND)    
    return mod()
