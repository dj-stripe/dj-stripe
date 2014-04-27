from .plugins import get_plugin



def related_model_has_active_subscription(related_model):
    """
    Helper function to check if a related model has an active subscription.
    """
    
    plugin = get_plugin()
    return plugin.related_model_has_active_subscription(related_model)

