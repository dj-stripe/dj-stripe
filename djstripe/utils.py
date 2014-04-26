from django.core.exceptions import ImproperlyConfigured
from .models import Customer
from .backends import get_backend

ERROR_MSG = (
                "The subscription_payment_required decorator requires the user"
                "be authenticated before use. Please use django.contrib.auth's"
                "login_required decorator."
                "Please read the warning at"
                "http://dj-stripe.readthedocs.org/en/latest/usage.html#ongoing-subscriptions"
            )


def user_has_active_subscription(user):
    """
    Helper function to check if a user has an active subscription.
    Throws improperlyConfigured if user.is_anonymous == True.
    """
    if user.is_anonymous():
        raise ImproperlyConfigured(ERROR_MSG)
    
    backend = get_backend()    
    customer, created = backend.create_customer_from_user(user)
        
    if created or not customer.has_active_subscription():
        return False
    return True
