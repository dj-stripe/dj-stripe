from .backends import get_backend



def related_model_has_active_subscription(related_model):
    """
    Helper function to check if a related model has an active subscription.
    Throws ImproperlyConfigured if user.is_anonymous == True.
    """
    
    backend = get_backend()
    return backend.related_model_has_active_subscription(related_model)

