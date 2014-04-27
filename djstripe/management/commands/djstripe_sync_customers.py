from __future__ import unicode_literals

from django.core.management.base import BaseCommand
from django.db.models import get_model
from django.conf import settings

from djstripe.sync import sync_customer
from djstripe.settings import DJSTRIPE_RELATED_MODEL_NAME_FIELD
from djstripe.settings import DJSTRIPE_CUSTOMER_RELATED_MODEL, User

if User is not DJSTRIPE_CUSTOMER_RELATED_MODEL:
    app_label, model_name = DJSTRIPE_CUSTOMER_RELATED_MODEL.split('.')
    RELATED_MODEL = get_model(app_label, model_name)
else:
    RELATED_MODEL = User

class Command(BaseCommand):

    help = "Sync customer data with stripe"

    def handle(self, *args, **options):
        qs = RELATED_MODEL.objects.exclude(customer__isnull=True)
        count = 0
        total = qs.count()
        for related_model in qs:
            count += 1
            perc = int(round(100 * (float(count) / float(total))))
            print("[{0}/{1} {2}%] Syncing {3} [{4}]").format(
                count, total, perc, getattr(related_model, DJSTRIPE_RELATED_MODEL_NAME_FIELD, ''), related_model.pk
            ) 
            sync_customer(related_model)
