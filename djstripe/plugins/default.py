from django.core.exceptions import ImproperlyConfigured

from ..models import Customer
from ..settings import User
from ..sync import sync_customer

class DefaultPlugin(object):


    ERROR_MSG = (
                    "The subscription_payment_required decorator requires the user"
                    "be authenticated before use. Please use django.contrib.auth's"
                    "login_required decorator."
                    "Please read the warning at"
                    "http://dj-stripe.readthedocs.org/en/latest/usage.html#ongoing-subscriptions"
                )


    def customer_related_model_list_display(self, obj):
        """
        admin.py list_display for Invoice
        
        """
        if hasattr(obj, 'USERNAME_FIELD'):
            # Using a Django 1.5 User model
            username = getattr(obj.customer.related_model, User.USERNAME_FIELD)
        else:
            # Using a pre-Django 1.5 User model
            username = obj.customer.related_model.username
        # In Django 1.5+ a User is not guaranteed to have an email field
        email = getattr(obj.customer.related_model, 'email', '')

        return "{0} <{1}>".format(
            username,
            email
        )

    def get_related_model_search_fields(self):
        """
        admin.py extra search_field for Charge, Event and Invoice 
        
        """
        
        if hasattr(User, 'USERNAME_FIELD'):
            # Using a Django 1.5 User model
            user_search_fields = [
                "customer__related_model__{0}".format(User.USERNAME_FIELD)
            ]

            try:
                # get_field_by_name throws FieldDoesNotExist if the field is not present on the model
                User._meta.get_field_by_name('email')
                user_search_fields + ["customer__related_model__email"]
            except FieldDoesNotExist:
                pass
        else:
            # Using a pre-Django 1.5 User model
            user_search_fields = [
                "customer__related_model__username",
                "customer__related_model__email"
            ]
        return user_search_fields    

    def create_customer(self, request):                
        """
        get_or_create a customer from a request.

        """
        return Customer.get_or_create(related_model=request.user)
    
    def get_related_model(self, request):
        return request.user
        
    def get_customer(self, request):
        return request.user.customer

    def related_model_has_active_subscription(self, related_model):
        """
        utils.py function used by decorators and mixins.
        
        """
        
        if related_model.is_anonymous():
            raise ImproperlyConfigured(self.ERROR_MSG)
    
        customer, created = Customer.get_or_create(related_model)
        
        if created or not customer.has_active_subscription():
            return False
        return True

