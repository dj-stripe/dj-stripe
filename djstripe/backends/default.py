from django.core.exceptions import ImproperlyConfigured

from ..models import Customer
from ..settings import User
from ..sync import sync_customer

class DefaultBackend(object):


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

    def get_related_model_search_fields_for_customer(self):
        """
        admin.py extra search_field for Customer
        
        """
        
        return ["related_model__username", "related_model__email"]

    def get_related_model_search_fields(self):
        """
        admin.py extra search_field for Charge, Event, Customer and Invoice 
        
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

    def create_customer_from_related_model(self, related_model):
        """
        get_or_create a customer from a related_model.

        """
        
        return Customer.get_or_create(related_model=related_model)
    
    def get_email_from_related_model(self, related_model):
        """
        Given a related_model, returns the email used for Stripe.

        """
        
        return related_model.email

    def get_email_from_customer(self, customer):
        """
        Given a customer, returns the email used for Stripe.

        """
        
        return customer.related_model.email
    
    def get_related_model(self, request):
        return request.user
        
    def get_customer(self, request):
        return request.user.customer

    def related_model_has_active_subscription(self, user):
        """
        utils.py function used by decorators and mixins.
        
        """
        
        if user.is_anonymous():
            raise ImproperlyConfigured(self.ERROR_MSG)
    
        customer, created = self.create_customer_from_related_model(user)
        
        if created or not customer.has_active_subscription():
            return False
        return True

    def init_customers(self, *args, **options):        
        """        
        Management function for creating customers for existing related models

        """
        
        for user in User.objects.filter(customer__isnull=True):
            # use get_or_create in case of race conditions on large
            #      user bases
            Customer.get_or_create(related_model=user)
            print("Created customer for {0}".format(user.email))
        
    def sync_customers(self, *args, **options):        
        """        
        Management function for syncing customers

        """
        
        qs = User.objects.exclude(customer__isnull=True)
        count = 0
        total = qs.count()
        for user in qs:
            count += 1
            perc = int(round(100 * (float(count) / float(total))))
            print("[{0}/{1} {2}%] Syncing {3} [{4}]").format(
                count, total, perc, user.username, user.pk
            ) 
            sync_customer(user)
