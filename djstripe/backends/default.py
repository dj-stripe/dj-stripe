from django.core.exceptions import ImproperlyConfigured

from ..models import Customer
from ..settings import User
from ..sync import sync_plans
from ..sync import sync_customer

class DefaultBackend(object):


    ERROR_MSG = (
                    "The subscription_payment_required decorator requires the user"
                    "be authenticated before use. Please use django.contrib.auth's"
                    "login_required decorator."
                    "Please read the warning at"
                    "http://dj-stripe.readthedocs.org/en/latest/usage.html#ongoing-subscriptions"
                )


    def create_customer(self, request):                
        return Customer.get_or_create(related_model=request.user)

    def create_customer_from_related_model(self, related_model):
        return Customer.get_or_create(related_model=related_model)
    
    def get_email_from_related_model(self, related_model):
        return related_model.email

    def get_email_from_customer(self, customer):
        return customer.related_model.email
    
    def get_related_model(self, request):
        return request.user
        
    def get_customer(self, request):
        return request.user.customer

    def related_model_has_active_subscription(self, user):
        if user.is_anonymous():
            raise ImproperlyConfigured(self.ERROR_MSG)
    
        customer, created = self.create_customer_from_related_model(user)
        
        if created or not customer.has_active_subscription():
            return False
        return True

    def init_customers(self, *args, **options):        
        for user in User.objects.filter(customer__isnull=True):
            # use get_or_create in case of race conditions on large
            #      user bases
            Customer.get_or_create(related_model=user)
            print("Created customer for {0}".format(user.email))
        
    def sync_plans(self, *args, **options):
        sync_plans()
        
    def sync_customers(self, *args, **options):        
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
