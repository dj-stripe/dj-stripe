from django.utils.module_loading import import_by_path

from ..settings import DJSTRIPE_CUSTOMER_RELATED_MODEL_PLUGIN


def get_plugin():
    """
    Return an instance of a dj-stripe plugin.
    
    """
    mod = import_by_path(DJSTRIPE_CUSTOMER_RELATED_MODEL_PLUGIN)    
    return mod()
