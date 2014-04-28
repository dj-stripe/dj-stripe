from __future__ import unicode_literals

from django.core.management.base import BaseCommand
from django.db.models import get_model

from djstripe.settings import DJSTRIPE_RELATED_MODEL_BILLING_EMAIL_FIELD
from djstripe.settings import DJSTRIPE_CUSTOMER_RELATED_MODEL, User
from djstripe.models import Customer

if User is not DJSTRIPE_CUSTOMER_RELATED_MODEL:
    app_label, model_name = DJSTRIPE_CUSTOMER_RELATED_MODEL.split('.')
    RELATED_MODEL = get_model(app_label, model_name)
else:
    RELATED_MODEL = User

class Command(BaseCommand):

    help = "Create customer objects for existing users that don't have one"

    def handle(self, *args, **options):
        for related_model in RELATED_MODEL.objects.filter(customer__isnull=True):
            # use get_or_create in case of race conditions on large
            #      user bases
            
            # Customer.get_or_create takes a user and not a related_model, so we use        
            #      Customer.objects.get_or_create
            
            Customer.objects.get_or_create(related_model=related_model)
            print("Created customer for {0}".format(getattr(related_model, DJSTRIPE_RELATED_MODEL_BILLING_EMAIL_FIELD, '')))
