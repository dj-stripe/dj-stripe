# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-06-29 05:28
from __future__ import unicode_literals

from django.db import migrations
import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0031_auto_20170606_1708'),
    ]

    operations = [
        migrations.AlterField(
            model_name='card',
            name='address_line1_check',
            field=djstripe.fields.StripeCharField(choices=[(b'fail', 'Fail'), (b'pass', 'Pass'), (b'unavailable', 'Unavailable'), (b'unchecked', 'Unchecked')], help_text=b'If ``address_line1`` was provided, results of the check.', max_length=11, null=True),
        ),
        migrations.AlterField(
            model_name='card',
            name='address_zip_check',
            field=djstripe.fields.StripeCharField(choices=[(b'fail', 'Fail'), (b'pass', 'Pass'), (b'unavailable', 'Unavailable'), (b'unchecked', 'Unchecked')], help_text=b'If ``address_zip`` was provided, results of the check.', max_length=11, null=True),
        ),
        migrations.AlterField(
            model_name='card',
            name='brand',
            field=djstripe.fields.StripeCharField(choices=[(b'MasterCard', 'MasterCard'), (b'Unknown', 'Unknown'), (b'Discover', 'Discover'), (b'Diners Club', 'Diners Club'), (b'Visa', 'Visa'), (b'JCB', 'JCB'), (b'American Express', 'American Express')], help_text=b'Card brand.', max_length=16),
        ),
        migrations.AlterField(
            model_name='card',
            name='cvc_check',
            field=djstripe.fields.StripeCharField(choices=[(b'fail', 'Fail'), (b'pass', 'Pass'), (b'unavailable', 'Unavailable'), (b'unchecked', 'Unchecked')], help_text=b'If a CVC was provided, results of the check.', max_length=11, null=True),
        ),
        migrations.AlterField(
            model_name='card',
            name='funding',
            field=djstripe.fields.StripeCharField(choices=[(b'credit', 'Credit'), (b'unknown', 'Unknown'), (b'prepaid', 'Prepaid'), (b'debit', 'Debit')], help_text=b'Card funding type.', max_length=7),
        ),
        migrations.AlterField(
            model_name='card',
            name='tokenization_method',
            field=djstripe.fields.StripeCharField(choices=[(b'android_pay', 'Android Pay'), (b'apple_pay', 'Apple Pay')], help_text=b'If the card number is tokenized, this is the method that was used.', max_length=11, null=True),
        ),
        migrations.AlterField(
            model_name='charge',
            name='failure_code',
            field=djstripe.fields.StripeCharField(choices=[(b'invalid_number', 'Invalid number'), (b'missing', 'No card being charged'), (b'incorrect_cvc', 'Incorrect security code'), (b'invalid_expiry_month', 'Invalid expiration month'), (b'invalid_expiry_year', 'Invalid expiration year'), (b'incorrect_zip', 'ZIP code failed validation'), (b'processing_error', 'Processing error'), (b'invalid_cvc', 'Invalid security code'), (b'card_declined', 'Card was declined'), (b'invalid_swipe_data', 'Invalid swipe data'), (b'expired_card', 'Expired card'), (b'incorrect_number', 'Incorrect number')], help_text=b'Error code explaining reason for charge failure if available.', max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='charge',
            name='source_type',
            field=djstripe.fields.StripeCharField(choices=[(b'alipay_account', 'Alipay account'), (b'bank_account', 'Bank account'), (b'card', 'Card'), (b'bitcoin_receiver', 'Bitcoin receiver')], help_text=b'The payment source type. If the payment source is supported by dj-stripe, a corresponding model is attached to this Charge via a foreign key matching this field.', max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='charge',
            name='status',
            field=djstripe.fields.StripeCharField(choices=[(b'failed', 'Failed'), (b'pending', 'Pending'), (b'succeeded', 'Succeeded')], help_text=b'The status of the payment.', max_length=10),
        ),
        migrations.AlterField(
            model_name='coupon',
            name='duration',
            field=djstripe.fields.StripeCharField(choices=[(b'forever', 'Forever'), (b'repeating', 'Multi-month'), (b'once', 'Once')], help_text=b'Describes how long a customer who applies this coupon will get the discount.', max_length=9),
        ),
        migrations.AlterField(
            model_name='plan',
            name='interval',
            field=djstripe.fields.StripeCharField(choices=[(b'week', 'Week'), (b'year', 'Year'), (b'day', 'Day'), (b'month', 'Month')], help_text=b'The frequency with which a subscription should be billed.', max_length=5),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='status',
            field=djstripe.fields.StripeCharField(choices=[(b'unpaid', 'Unpaid'), (b'canceled', 'Canceled'), (b'active', 'Active'), (b'past_due', 'Past due'), (b'trialing', 'Trialing')], help_text=b'The status of this subscription.', max_length=8),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='failure_code',
            field=djstripe.fields.StripeCharField(choices=[(b'invalid_account_number', 'Invalid account number'), (b'bank_account_restricted', 'Bank account has restrictions on payouts allowed.'), (b'bank_ownership_changed', 'Destination bank account has changed ownership.'), (b'debit_not_authorized', 'Debit transactions not approved on the bank account.'), (b'could_not_process', 'Bank could not process payout.'), (b'account_closed', 'Bank account has been closed.'), (b'account_frozen', 'Bank account has been frozen.'), (b'invalid_currency', 'Bank account does not support currency.'), (b'unsupported_card', 'Card no longer supported.'), (b'insufficient_funds', 'Stripe account has insufficient funds.'), (b'no_account', 'Bank account could not be located.')], help_text=b'Error code explaining reason for transfer failure if available. See https://stripe.com/docs/api/python#transfer_failures.', max_length=23, null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='source_type',
            field=djstripe.fields.StripeCharField(choices=[(b'alipay_account', 'Alipay account'), (b'bank_account', 'Bank account'), (b'card', 'Card'), (b'bitcoin_receiver', 'Bitcoin receiver')], help_text=b'The source balance from which this transfer came.', max_length=16),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='status',
            field=djstripe.fields.StripeCharField(choices=[(b'failed', 'Failed'), (b'in_transit', 'In transit'), (b'paid', 'Paid'), (b'canceled', 'Canceled'), (b'pending', 'Pending')], help_text=b'The current status of the transfer. A transfer will be pending until it is submitted to the bank, at which point it becomes in_transit. It will then change to paid if the transaction goes through. If it does not go through successfully, its status will change to failed or canceled.', max_length=10),
        ),
    ]
