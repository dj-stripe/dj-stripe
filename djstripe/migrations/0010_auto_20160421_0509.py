# -*- coding: utf-8 -*-
"""
    Since subscription IDs were not previously stored, a direct migration will leave us
    with a bunch of orphaned objects. It was decided [here](https://github.com/pydanny/dj-stripe/issues/162)
    that a purge and re-sync would be the best option. No data that is not currently hosted on stripe will
    be deleted. Anything stored locally
"""

from __future__ import unicode_literals

from django.core import serializers
from django.db import migrations, models
from django.db.migrations.operations.special import RunPython
import django.core.validators
from tqdm import tqdm

import djstripe.fields
from djstripe.utils import simple_stripe_pagination_iterator


def resync_subscriptions(apps, schema_editor):
    from django.conf import settings
    import stripe
    stripe.api_version = "2015-07-28"

    Customer = apps.get_model('djstripe', 'Customer')
    Subscription = apps.get_model('djstripe', 'Subscription')

    print("Purging subscriptions. Don't worry, all active subscriptions will be re-synced from stripe. Just in case you didn't get the memo, we'll print out a json representation of each object for your records:")
    print(serializers.serialize("json", Subscription.objects.all()))
    Subscription.objects.all().delete()

    print("Re-syncing subscriptions. This could take a while.")

    for customer in tqdm(Customer.objects.all()):
        customer_stripe_subscriptions = customer.api_retrieve(api_key=settings.STRIPE_SECRET_KEY).subscriptions

        for stripe_subscription in simple_stripe_pagination_iterator(customer_stripe_subscriptions):
            Subscription.sync_from_stripe_data(stripe_subscription)


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0009_auto_20160104_0911'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subscription',
            name='plan',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='amount',
        ),
        migrations.AddField(
            model_name='subscription',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(default='dummy', max_length=50, unique=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='plan',
            name='statement_descriptor',
            field=djstripe.fields.StripeCharField(max_length=22, null=True, help_text='An arbitrary string to be displayed on your customer’s credit card statement. The statement description may not include <>"\' characters, and will appear on your customer’s statement in capital letters. Non-ASCII characters are automatically stripped. While most banks display this information consistently, some may display it incorrectly or not at all.'),
        ),
        migrations.AddField(
            model_name='subscription',
            name='description',
            field=djstripe.fields.StripeTextField(help_text='A description of this object.', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AddField(
            model_name='subscription',
            name='metadata',
            field=djstripe.fields.StripeJSONField(help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(null=True, help_text='The datetime this object was created in stripe.'),
        ),
        migrations.AddField(
            model_name='subscription',
            name='tax_percent',
            field=djstripe.fields.StripePercentField(validators=[django.core.validators.MinValueValidator(1.0), django.core.validators.MaxValueValidator(100.0)], decimal_places=2, max_digits=5, null=True, help_text='A positive decimal (with at most two decimal places) between 1 and 100. This represents the percentage of the subscription invoice subtotal that will be calculated and added as tax to the final amount each billing period.'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='amount',
            field=djstripe.fields.StripeCurrencyField(decimal_places=2, max_digits=7, help_text='Amount to be charged on the interval specified.'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='currency',
            field=djstripe.fields.StripeCharField(max_length=3, help_text='Three-letter ISO currency code representing the currency in which the charge was made.'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='interval',
            field=djstripe.fields.StripeCharField(max_length=5, choices=[('day', 'Day'), ('week', 'Week'), ('month', 'Month'), ('year', 'Year')], help_text='The frequency with which a subscription should be billed.'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='interval_count',
            field=djstripe.fields.StripeIntegerField(null=True, help_text='The number of intervals (specified in the interval property) between each subscription billing.'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='name',
            field=djstripe.fields.StripeTextField(help_text='Name of the plan, to be displayed on invoices and in the web interface.'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='trial_period_days',
            field=djstripe.fields.StripeIntegerField(null=True, help_text='Number of trial period days granted when subscribing a customer to this plan. Null if the plan has no trial period.'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='cancel_at_period_end',
            field=djstripe.fields.StripeBooleanField(default=False, help_text='If the subscription has been canceled with the ``at_period_end`` flag set to true, ``cancel_at_period_end`` on the subscription will be true. You can use this attribute to determine whether a subscription that has a status of active is scheduled to be canceled at the end of the current period.'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='canceled_at',
            field=djstripe.fields.StripeDateTimeField(null=True, help_text='If the subscription has been canceled, the date of that cancellation.'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='current_period_end',
            field=djstripe.fields.StripeDateTimeField(help_text='End of the current period for which the subscription has been invoiced. At the end of this period, a new invoice will be created.'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='current_period_start',
            field=djstripe.fields.StripeDateTimeField(help_text='Start of the current period for which the subscription has been invoiced.'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='customer',
            field=models.ForeignKey(help_text='The customer associated with this subscription.', to='djstripe.Customer', related_name='subscriptions'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='ended_at',
            field=djstripe.fields.StripeDateTimeField(null=True, help_text='If the subscription has ended (either because it was canceled or because the customer was switched to a subscription to a new plan), the date the subscription ended.'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='quantity',
            field=djstripe.fields.StripeIntegerField(help_text='The quantity applied to this subscription.'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='start',
            field=djstripe.fields.StripeDateTimeField(help_text='Date the subscription started.'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='status',
            field=djstripe.fields.StripeCharField(max_length=8, choices=[('trialing', 'Trialing'), ('active', 'Active'), ('past_due', 'Past Due'), ('canceled', 'Canceled'), ('unpaid', 'Unpaid')], help_text='The status of this subscription.'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='trial_end',
            field=djstripe.fields.StripeDateTimeField(null=True, help_text='If the subscription has a trial, the end of that trial.'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='trial_start',
            field=djstripe.fields.StripeDateTimeField(null=True, help_text='If the subscription has a trial, the beginning of that trial.'),
        ),
        RunPython(resync_subscriptions),
        migrations.AlterField(
            model_name='subscription',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, unique=True),
        ),
    ]
