# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone

import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('djstripe', '0009_auto_20160501_1838'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, unique=True),
        ),

        migrations.AlterField(
            model_name='event',
            name='customer',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                null=True,
                to='djstripe.Customer',
                help_text='In the event that there is a related customer, this will point to that Customer record'),
        ),
        migrations.AlterField(
            model_name='event',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(
                help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. \
                Otherwise, this field indicates whether this record comes from Stripe test mode or live mode \
                operation.', default=False),
        ),
        migrations.AlterField(
            model_name='event',
            name='processed',
            field=models.BooleanField(
                help_text='If validity is performed, webhook event processor(s) may run to take further action on \
                the event. Once these have run, this is set to True.', default=False),
        ),
        migrations.AlterField(
            model_name='event',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='type',
            field=djstripe.fields.StripeCharField(max_length=250, help_text="Stripe's event description code"),
        ),
        migrations.AlterField(
            model_name='event',
            name='valid',
            field=models.NullBooleanField(
                help_text='Tri-state bool. Null == validity not yet confirmed. Otherwise, this field indicates that \
                this event was checked via stripe api and found to be either authentic (valid=True) or in-authentic \
                (possibly malicious)'),
        ),
        migrations.AlterField(
            model_name='event',
            name='webhook_message',
            field=djstripe.fields.StripeJSONField(
                help_text='data received at webhook. data should be considered to be garbage until validity check is \
                run and valid flag is set'),
        ),

        migrations.AlterField(
            model_name='invoice',
            name='attempt_count',
            field=djstripe.fields.StripeIntegerField(
                help_text='Number of payment attempts made for this invoice, from the perspective of the payment \
                retry schedule. Any payment attempt counts as the first attempt, and subsequently only automatic \
                retries increment the attempt count. In other words, manual payment attempts after the first attempt \
                do not affect the retry schedule.', default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='attempted',
            field=djstripe.fields.StripeBooleanField(
                help_text='Whether or not an attempt has been made to pay the invoice. An invoice is not attempted \
                until 1 hour after the ``invoice.created`` webhook, for example, so you might not want to display \
                that invoice as unpaid to your users.', default=False),
        ),

        # Original format is a charge stripe id.... renaming it and creating a new field.
        # The sync in the next migration will take care of filling the charge field.
        migrations.RenameField(
            model_name='invoice',
            old_name='charge',
            new_name='charge_stripe_id'
        ),
        migrations.AlterField(
            model_name='invoice',
            name='charge_stripe_id',
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='charge',
            field=models.OneToOneField(to='djstripe.Charge', on_delete=django.db.models.deletion.CASCADE, related_name='invoice', null=True,
                                       help_text='The latest charge generated for this invoice, if any.'),
        ),

        migrations.AlterField(
            model_name='invoice',
            name='closed',
            field=djstripe.fields.StripeBooleanField(
                help_text="Whether or not the invoice is still trying to collect payment. An invoice is closed if \
                it's either paid or it has been marked closed. A closed invoice will no longer attempt to collect \
                payment.", default=False),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='customer',
            field=models.ForeignKey(related_name='invoices', on_delete=django.db.models.deletion.CASCADE, to='djstripe.Customer',
                                    help_text='The customer associated with this invoice.'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='date',
            field=djstripe.fields.StripeDateTimeField(help_text='The date on the invoice.'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='paid',
            field=djstripe.fields.StripeBooleanField(help_text='The time at which payment will next be attempted.',
                                                     default=False),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='period_end',
            field=djstripe.fields.StripeDateTimeField(
                help_text='End of the usage period during which invoice items were added to this invoice.'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='period_start',
            field=djstripe.fields.StripeDateTimeField(
                help_text='Start of the usage period during which invoice items were added to this invoice.'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='subtotal',
            field=djstripe.fields.StripeCurrencyField(
                max_digits=7,
                help_text='Only set for upcoming invoices that preview prorations. \
                The time used to calculate prorations.',
                decimal_places=2),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='total',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2,
                                                      verbose_name='Total after discount.'),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='amount',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, help_text='Amount invoiced.', decimal_places=2),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='currency',
            field=djstripe.fields.StripeCharField(max_length=3, help_text='Three-letter ISO currency code.'),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='invoice',
            field=models.ForeignKey(related_name='invoiceitems', on_delete=django.db.models.deletion.CASCADE, to='djstripe.Invoice',
                                    help_text='The invoice to which this invoiceitem is attached.'),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='period_end',
            field=djstripe.fields.StripeDateTimeField(
                help_text="Might be the date when this invoiceitem's invoice was sent."),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='period_start',
            field=djstripe.fields.StripeDateTimeField(
                help_text='Might be the date when this invoiceitem was added to the invoice'),
        ),

        # Original format is a charge stripe id.... renaming it and creating a new field.
        # The sync in the next migration will take care of filling the charge field.
        migrations.RenameField(
            model_name='invoiceitem',
            old_name="plan",
            new_name="plan_stripe_id",
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='plan_stripe_id',
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='plan',
            field=models.ForeignKey(
                related_name='invoiceitems',
                on_delete=django.db.models.deletion.CASCADE,
                null=True,
                to='djstripe.Plan',
                help_text='If the invoice item is a proration, the plan of the subscription for which the \
                proration was computed.'),
        ),

        migrations.AlterField(
            model_name='invoiceitem',
            name='proration',
            field=djstripe.fields.StripeBooleanField(
                help_text='Whether or not the invoice item was created automatically as a proration adjustment when \
                the customer switched plans.', default=False),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='quantity',
            field=djstripe.fields.StripeIntegerField(
                help_text='If the invoice item is a proration, the quantity of the subscription for which the \
                proration was computed.', null=True),
        ),

        # InvoiceItems stripe_id was the subscription stripe_id... what
        migrations.RenameField(
            model_name='invoiceitem',
            old_name='stripe_id',
            new_name='subscription_stripe_id'
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='subscription_stripe_id',
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, default="unknown", unique=False),
        ),

        migrations.AlterField(
            model_name='plan',
            name='amount',
            field=djstripe.fields.StripeCurrencyField(
                max_digits=7,
                help_text='Amount to be charged on the interval specified.',
                decimal_places=2),
        ),
        migrations.AlterField(
            model_name='plan',
            name='currency',
            field=djstripe.fields.StripeCharField(max_length=3, help_text='Three-letter ISO currency code'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='interval',
            field=djstripe.fields.StripeCharField(
                choices=[('day', 'Day'), ('week', 'Week'), ('month', 'Month'), ('year', 'Year')],
                max_length=5,
                help_text='The frequency with which a subscription should be billed.'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='interval_count',
            field=djstripe.fields.StripeIntegerField(
                help_text='The number of intervals (specified in the interval property) between each \
                subscription billing.', null=True),
        ),
        migrations.AlterField(
            model_name='plan',
            name='name',
            field=djstripe.fields.StripeTextField(
                help_text='Name of the plan, to be displayed on invoices and in the web interface.'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='plan',
            name='trial_period_days',
            field=djstripe.fields.StripeIntegerField(
                help_text='Number of trial period days granted when subscribing a customer to this plan. \
                Null if the plan has no trial period.', null=True),
        ),

        migrations.AlterField(
            model_name='subscription',
            name='cancel_at_period_end',
            field=djstripe.fields.StripeBooleanField(
                help_text='If the subscription has been canceled with the ``at_period_end`` flag set to true, \
                ``cancel_at_period_end`` on the subscription will be true. You can use this attribute to determine \
                whether a subscription that has a status of active is scheduled to be canceled at the end of the \
                current period.', default=False),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='canceled_at',
            field=djstripe.fields.StripeDateTimeField(
                help_text='If the subscription has been canceled, the date of that cancellation. \
                If the subscription was canceled with ``cancel_at_period_end``, canceled_at will still reflect the \
                date of the initial cancellation request, not the end of the subscription period when the \
                subscription is automatically moved to a canceled state.', null=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='current_period_end',
            field=djstripe.fields.StripeDateTimeField(
                help_text='End of the current period for which the subscription has been invoiced. At the end of \
                this period, a new invoice will be created.', default=datetime.datetime(2100, 1, 1, 0, 0,
                                                                                        tzinfo=timezone.utc)),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='subscription',
            name='current_period_start',
            field=djstripe.fields.StripeDateTimeField(
                help_text='Start of the current period for which the subscription has been invoiced.',
                default=datetime.datetime(2100, 1, 1, 0, 0, tzinfo=timezone.utc)),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='subscription',
            name='customer',
            field=models.ForeignKey(related_name='subscriptions', on_delete=django.db.models.deletion.CASCADE, default=1, to='djstripe.Customer',
                                    help_text='The customer associated with this subscription.'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='subscription',
            name='ended_at',
            field=djstripe.fields.StripeDateTimeField(
                help_text='If the subscription has ended (either because it was canceled or because the customer \
                was switched to a subscription to a new plan), the date the subscription ended.', null=True),
        ),

        # Original format is a charge stripe id.... renaming it and creating a new field.
        #  The sync in the next migration will take care of filling the charge field.
        migrations.RenameField(
            model_name='subscription',
            old_name="plan",
            new_name="plan_stripe_id",
        ),
        migrations.AlterField(
            model_name='subscription',
            name='plan_stripe_id',
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='plan',
            field=models.ForeignKey(related_name='subscriptions', on_delete=django.db.models.deletion.CASCADE, default=1, to='djstripe.Plan',
                                    help_text='The plan associated with this subscription.'),
            preserve_default=False,
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
            field=djstripe.fields.StripeCharField(
                choices=[('trialing', 'Trialing'), ('active', 'Active'), ('past_due', 'Past Due'),
                         ('canceled', 'Canceled'), ('unpaid', 'Unpaid')],
                max_length=8, help_text='The status of this subscription.'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='trial_end',
            field=djstripe.fields.StripeDateTimeField(
                help_text='If the subscription has a trial, the end of that trial.', null=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='trial_start',
            field=djstripe.fields.StripeDateTimeField(
                help_text='If the subscription has a trial, the beginning of that trial.', null=True),
        ),

        migrations.AlterField(
            model_name='transfer',
            name='adjustment_count',
            field=djstripe.fields.StripeIntegerField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='adjustment_fees',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, default=None, decimal_places=2, null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='adjustment_gross',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, default=None, decimal_places=2, null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='amount',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, help_text='The amount transferred',
                                                      decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='charge_count',
            field=djstripe.fields.StripeIntegerField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='charge_fees',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, default=None, decimal_places=2, null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='charge_gross',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, default=None, decimal_places=2, null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='collected_fee_count',
            field=djstripe.fields.StripeIntegerField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='collected_fee_gross',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, default=None, decimal_places=2, null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='date',
            field=djstripe.fields.StripeDateTimeField(
                help_text="Date the transfer is scheduled to arrive in the bank. \
                This doesn't factor in delays like weekends or bank holidays."),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='net',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, default=None, decimal_places=2, null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='refund_count',
            field=djstripe.fields.StripeIntegerField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='refund_fees',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, default=None, decimal_places=2, null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='refund_gross',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, default=None, decimal_places=2, null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='status',
            field=djstripe.fields.StripeCharField(
                choices=[('paid', 'Paid'), ('pending', 'Pending'), ('in_transit', 'In Transit'),
                         ('canceled', 'Canceled'), ('failed', 'Failed')],
                max_length=10,
                help_text='The current status of the transfer. A transfer will be pending until it is submitted to \
                the bank, at which point it becomes in_transit. It will then change to paid if the transaction goes \
                through. If it does not go through successfully, its status will change to failed or canceled.'),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='validation_count',
            field=djstripe.fields.StripeIntegerField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='validation_fees',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, default=None, decimal_places=2, null=True),
        ),

        migrations.AlterField(
            model_name='charge',
            name='amount',
            field=djstripe.fields.StripeCurrencyField(help_text='Amount charged.', max_digits=7, default=0,
                                                      decimal_places=2),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='charge',
            name='amount_refunded',
            field=djstripe.fields.StripeCurrencyField(
                help_text='Amount refunded (can be less than the amount attribute on the charge if a partial refund \
                was issued).', max_digits=7, default=0, decimal_places=2),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='charge',
            name='customer',
            field=models.ForeignKey(related_name='charges', on_delete=django.db.models.deletion.CASCADE, to='djstripe.Customer',
                                    help_text='The customer associated with this charge.'),
        ),
        migrations.AlterField(
            model_name='charge',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True),
        ),
        migrations.AlterField(
            model_name='charge',
            name='disputed',
            field=djstripe.fields.StripeBooleanField(help_text='Whether or not this charge is disputed.',
                                                     default=False),
        ),
        migrations.AlterField(
            model_name='charge',
            name='fee',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2, null=True),
        ),
        migrations.AlterField(
            model_name='charge',
            name='paid',
            field=djstripe.fields.StripeBooleanField(
                help_text='True if the charge succeeded, or was successfully authorized for later capture, \
                False otherwise.', default=False),
        ),
        migrations.AlterField(
            model_name='charge',
            name='refunded',
            field=djstripe.fields.StripeBooleanField(
                help_text='Whether or not the charge has been fully refunded. If the charge is only partially \
                refunded, this attribute will still be false.', default=False),
        ),
        migrations.AlterField(
            model_name='charge',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='charge',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.',
                                                      null=True),
        ),
    ]
