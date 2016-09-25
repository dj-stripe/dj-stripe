# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys

from django.core import serializers
from django.db import migrations
from django.db.migrations.operations.special import RunPython
from django.db.utils import IntegrityError
from django.utils import six
from stripe.error import InvalidRequestError
from tqdm import tqdm

from djstripe.exceptions import CustomerDoesNotExistLocallyException


def resync_subscriptions(apps, schema_editor):
    """
    Since subscription IDs were not previously stored, a direct migration will leave us
    with a bunch of orphaned objects. It was decided [here](https://github.com/kavdev/dj-stripe/issues/162)
    that a purge and re-sync would be the best option. No data that is currently available on stripe will
    be deleted. Anything stored locally will be purged.
    """

    # This is okay, since we're only doing a forward migration.
    from djstripe.models import Subscription

    import stripe
    stripe.api_version = "2016-03-07"

    if Subscription.objects.count():
        print("Purging subscriptions. Don't worry, all active subscriptions will be re-synced from stripe. Just in \
        case you didn't get the memo, we'll print out a json representation of each object for your records:")
        print(serializers.serialize("json", Subscription.objects.all()))
        Subscription.objects.all().delete()

        print("Re-syncing subscriptions. This may take a while.")

        for stripe_subscription in tqdm(iterable=Subscription.api_list(), desc="Sync", unit=" subscriptions"):
            try:
                Subscription.sync_from_stripe_data(stripe_subscription)
            except CustomerDoesNotExistLocallyException:
                tqdm.write("The customer for this subscription ({subscription_id}) does not exist locally (so we \
                won't sync the subscription). You'll want to figure out how that \
                happened.".format(subscription_id=stripe_subscription['id']))

        print("Subscription re-sync complete.")


def resync_invoiceitems(apps, schema_editor):
    """
    Since invoiceitem IDs were not previously stored (the ``stripe_id`` field held the id of the linked subsription),
    a direct migration will leave us with a bunch of orphaned objects. It was decided
    [here](https://github.com/kavdev/dj-stripe/issues/162) that a purge and re-sync would be the best option for
    subscriptions. That's being extended to InvoiceItems. No data that is currently available on stripe will be
    deleted. Anything stored locally will be purged.
    """

    # This is okay, since we're only doing a forward migration.
    from djstripe.models import InvoiceItem

    import stripe
    stripe.api_version = "2016-03-07"

    if InvoiceItem.objects.count():
        print("Purging invoiceitems. Don't worry, all invoiceitems will be re-synced from stripe. Just in case you \
        didn't get the memo, we'll print out a json representation of each object for your records:")
        print(serializers.serialize("json", InvoiceItem.objects.all()))
        InvoiceItem.objects.all().delete()

        print("Re-syncing invoiceitems. This may take a while.")

        for stripe_invoiceitem in tqdm(iterable=InvoiceItem.api_list(), desc="Sync", unit=" invoiceitems"):
            try:
                InvoiceItem.sync_from_stripe_data(stripe_invoiceitem)
            except CustomerDoesNotExistLocallyException:
                tqdm.write("The customer for this invoiceitem ({invoiceitem_id}) does not exist \
                locally (so we won't sync the invoiceitem). You'll want to figure out how that \
                happened.".format(invoiceitem_id=stripe_invoiceitem['id']))

        print("InvoiceItem re-sync complete.")


def sync_charges(apps, schema_editor):
    # This is okay, since we're only doing a forward migration.
    from djstripe.models import Charge

    import stripe
    stripe.api_version = "2016-03-07"

    if Charge.objects.count():
        print("syncing charges. This may take a while.")

        for charge in tqdm(Charge.objects.all(), desc="Sync", unit=" charges"):
            try:
                Charge.sync_from_stripe_data(charge.api_retrieve())
            except InvalidRequestError:
                tqdm.write("There was an error while syncing charge ({charge_id}).".format(charge_id=charge.stripe_id))

        print("Charge sync complete.")


def sync_invoices(apps, schema_editor):
    # This is okay, since we're only doing a forward migration.
    from djstripe.models import Invoice

    import stripe
    stripe.api_version = "2016-03-07"

    if Invoice.objects.count():
        print("syncing invoices. This may take a while.")

        for invoice in tqdm(iterable=Invoice.objects.all(), desc="Sync", unit=" invoices"):
            try:
                Invoice.sync_from_stripe_data(invoice.api_retrieve())
            except InvalidRequestError:
                tqdm.write("There was an error while syncing invoice \
                ({invoice_id}).".format(invoice_id=invoice.stripe_id))

        print("Invoice sync complete.")


def sync_transfers(apps, schema_editor):
    # This is okay, since we're only doing a forward migration.
    from djstripe.models import Transfer

    import stripe
    stripe.api_version = "2016-03-07"

    if Transfer.objects.count():
        print("syncing transfers. This may take a while.")

        for transfer in tqdm(iterable=Transfer.objects.all(), desc="Sync", unit=" transfers"):
            try:
                Transfer.sync_from_stripe_data(transfer)
            except InvalidRequestError:
                tqdm.write("There was an error while syncing transfer \
                ({transfer_id}).".format(transfer_id=transfer.stripe_id))

        print("Transfer sync complete.")


def sync_plans(apps, schema_editor):
    # This is okay, since we're only doing a forward migration.
    from djstripe.models import Plan

    import stripe
    stripe.api_version = "2016-03-07"

    if Plan.objects.count():
        print("syncing plans. This may take a while.")

        for plan in tqdm(iterable=Plan.objects.all(), desc="Sync", unit=" plans"):
            try:
                Plan.sync_from_stripe_data(plan)
            except InvalidRequestError:
                tqdm.write("There was an error while syncing plan ({plan_id}).".format(transfer_id=plan.stripe_id))

        print("Transfer sync complete.")


def sync_customers(apps, schema_editor):
    # This is okay, since we're only doing a forward migration.
    from djstripe.models import Customer

    import stripe
    stripe.api_version = "2016-03-07"

    if Customer.objects.count():
        print("syncing customers. This may take a while.")

        for customer in tqdm(Customer.objects.all(), desc="Sync", unit=" customers"):
            try:
                Customer.sync_from_stripe_data(customer.api_retrieve())
            except InvalidRequestError:
                tqdm.write("There was an error while syncing customer \
                ({customer_id}).".format(customer_id=customer.stripe_id))
            except IntegrityError:
                print(customer.api_retrieve())
                six.reraise(*sys.exc_info())

        print("Customer sync complete.")


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0011_charge_captured_update'),
    ]

    operations = [
        RunPython(resync_subscriptions),
        RunPython(resync_invoiceitems),
        RunPython(sync_charges),
        RunPython(sync_invoices),
        RunPython(sync_transfers),
        RunPython(sync_customers),
    ]
