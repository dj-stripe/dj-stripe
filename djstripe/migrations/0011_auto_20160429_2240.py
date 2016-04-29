# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0010_auto_20160421_0509'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transfer',
            name='event',
        ),
        migrations.AddField(
            model_name='transfer',
            name='amount_reversed',
            field=djstripe.fields.StripeCurrencyField(null=True, decimal_places=2, help_text='The amount reversed (can be less than the amount attribute on the transfer if a partial reversal was issued).', max_digits=7),
        ),
        migrations.AddField(
            model_name='transfer',
            name='application_fee',
            field=djstripe.fields.StripeTextField(null=True, help_text="Might be the ID of an application fee object. The Stripe API docs don't provide any information."),
        ),
        migrations.AddField(
            model_name='transfer',
            name='currency',
            field=djstripe.fields.StripeCharField(max_length=3, help_text='Three-letter ISO currency code', default='usd'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transfer',
            name='destination',
            field=djstripe.fields.StripeIdField(max_length=50, help_text='ID of the bank account, card, or Stripe account the transfer was sent to.', default='unknown'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transfer',
            name='destination_payment',
            field=djstripe.fields.StripeIdField(null=True, max_length=50, help_text='If the destination is a Stripe account, this will be the ID of the payment that the destination account received for the transfer.'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='destination_type',
            field=djstripe.fields.StripeCharField(max_length=14, choices=[('card', 'Card'), ('bank_account', 'Bank Account'), ('stripe_account', 'Stripe Account')], help_text='The type of the transfer destination.', default='unknown'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transfer',
            name='failure_code',
            field=djstripe.fields.StripeCharField(null=True, max_length=23, choices=[('insufficient_funds', 'Insufficient Funds'), ('account_closed', 'Account Closed'), ('no_account', 'No Account'), ('invalid_account_number', 'Invalid Account Number'), ('debit_not_authorized', 'Debit Not Authorized'), ('bank_ownership_changed', 'Bank Ownership Changed'), ('account_frozen', 'Account Frozen'), ('could_not_process', 'Could Not Process'), ('bank_account_restricted', 'Bank Account Restricted'), ('invalid_currency', 'Invalid Currency')], help_text='Error code explaining reason for transfer failure if available. See https://stripe.com/docs/api/python#transfer_failures.'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='failure_message',
            field=djstripe.fields.StripeTextField(null=True, help_text='Message to user further explaining reason for transfer failure if available.'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='fee_details',
            field=djstripe.fields.StripeJSONField(null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='reversals',
            field=djstripe.fields.StripeJSONField(default={}, help_text='A list of reversals that have been applied to the transfer.'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transfer',
            name='reversed',
            field=djstripe.fields.StripeBooleanField(default=False, help_text='Whether or not the transfer has been fully reversed. If the transfer is only partially reversed, this attribute will still be false.'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='source_transaction',
            field=djstripe.fields.StripeIdField(null=True, max_length=50, help_text='ID of the charge (or other transaction) that was used to fund the transfer. If null, the transfer was funded from the available balance.'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='statement_descriptor',
            field=djstripe.fields.StripeCharField(null=True, max_length=22, help_text='An arbitrary string to be displayed on your customer’s credit card statement. The statement description may not include <>"\' characters, and will appear on your customer’s statement in capital letters. Non-ASCII characters are automatically stripped. While most banks display this information consistently, some may display it incorrectly or not at all.'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='currency',
            field=djstripe.fields.StripeCharField(max_length=3, help_text='Three-letter ISO currency code'),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='adjustment_count',
            field=djstripe.fields.StripeIntegerField(null=True, default=None),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='adjustment_fees',
            field=djstripe.fields.StripeCurrencyField(null=True, default=None, decimal_places=2, max_digits=7),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='adjustment_gross',
            field=djstripe.fields.StripeCurrencyField(null=True, default=None, decimal_places=2, max_digits=7),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='amount',
            field=djstripe.fields.StripeCurrencyField(decimal_places=2, help_text='The amount transferred', max_digits=7),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='charge_count',
            field=djstripe.fields.StripeIntegerField(null=True, default=None),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='charge_fees',
            field=djstripe.fields.StripeCurrencyField(null=True, default=None, decimal_places=2, max_digits=7),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='charge_gross',
            field=djstripe.fields.StripeCurrencyField(null=True, default=None, decimal_places=2, max_digits=7),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='collected_fee_count',
            field=djstripe.fields.StripeIntegerField(null=True, default=None),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='collected_fee_gross',
            field=djstripe.fields.StripeCurrencyField(null=True, default=None, decimal_places=2, max_digits=7),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='date',
            field=djstripe.fields.StripeDateTimeField(help_text='Date the transfer is scheduled to arrive in the bank. This doesn’t factor in delays like weekends or bank holidays.'),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='net',
            field=djstripe.fields.StripeCurrencyField(null=True, default=None, decimal_places=2, max_digits=7),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='refund_count',
            field=djstripe.fields.StripeIntegerField(null=True, default=None),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='refund_fees',
            field=djstripe.fields.StripeCurrencyField(null=True, default=None, decimal_places=2, max_digits=7),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='refund_gross',
            field=djstripe.fields.StripeCurrencyField(null=True, default=None, decimal_places=2, max_digits=7),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='status',
            field=djstripe.fields.StripeCharField(max_length=10, choices=[('paid', 'Paid'), ('pending', 'Pending'), ('in_transit', 'In Transit'), ('canceled', 'Canceled'), ('failed', 'Failed')], help_text='The current status of the transfer. A transfer will be pending until it is submitted to the bank, at which point it becomes in_transit. It will then change to paid if the transaction goes through. If it does not go through successfully, its status will change to failed or canceled.'),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='validation_count',
            field=djstripe.fields.StripeIntegerField(null=True, default=None),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='validation_fees',
            field=djstripe.fields.StripeCurrencyField(null=True, default=None, decimal_places=2, max_digits=7),
        ),
    ]
