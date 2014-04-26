from ...models import Customer
from ...settings import User
from ...sync import sync_plans
from ...sync import sync_customer

class DefaultBackend(object):

    def create_customer(self, request):        
        return Customer.get_or_create(user=request.user)

    def create_customer_from_user(self, user):   
        return Customer.get_or_create(user=user)
        
    def get_customer(self, request):
        return request.user.customer

    def init_customers(self, *args, **options):
        
        for user in User.objects.filter(customer__isnull=True):
            # use get_or_create in case of race conditions on large
            #      user bases
            Customer.get_or_create(user=user)
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
