# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import djstripe.fields
import django.core.validators
import datetime
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('djstripe', '0008_auto_20150806_1641'),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(verbose_name='created', default=django.utils.timezone.now, editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(verbose_name='modified', default=django.utils.timezone.now, editable=False)),
                ('stripe_id', djstripe.fields.StripeIdField(max_length=50, unique=True)),
                ('livemode', djstripe.fields.StripeNullBooleanField(help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.', default=False)),
                ('stripe_timestamp', djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.', null=True)),
                ('metadata', djstripe.fields.StripeJSONField(blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.', null=True)),
                ('description', djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StripeSource',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(verbose_name='created', default=django.utils.timezone.now, editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(verbose_name='modified', default=django.utils.timezone.now, editable=False)),
                ('stripe_id', djstripe.fields.StripeIdField(max_length=50, unique=True)),
                ('livemode', djstripe.fields.StripeNullBooleanField(help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.', default=False)),
                ('stripe_timestamp', djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.', null=True)),
                ('metadata', djstripe.fields.StripeJSONField(blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.', null=True)),
                ('description', djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='transferchargefee',
            name='transfer',
        ),
        migrations.RemoveField(
            model_name='charge',
            name='card_kind',
        ),
        migrations.RemoveField(
            model_name='charge',
            name='card_last_4',
        ),
        migrations.RemoveField(
            model_name='charge',
            name='invoice',
        ),
        migrations.RemoveField(
            model_name='customer',
            name='card_exp_month',
        ),
        migrations.RemoveField(
            model_name='customer',
            name='card_exp_year',
        ),
        migrations.RemoveField(
            model_name='customer',
            name='card_fingerprint',
        ),
        migrations.RemoveField(
            model_name='customer',
            name='card_kind',
        ),
        migrations.RemoveField(
            model_name='customer',
            name='card_last_4',
        ),
        migrations.RemoveField(
            model_name='event',
            name='validated_message',
        ),
        migrations.RemoveField(
            model_name='invoiceitem',
            name='line_type',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='amount',
        ),
        migrations.RemoveField(
            model_name='transfer',
            name='event',
        ),
        migrations.AddField(
            model_name='charge',
            name='currency',
            field=djstripe.fields.StripeCharField(help_text='Three-letter ISO currency code representing the currency in which the charge was made.', max_length=3, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='charge',
            name='failure_code',
            field=djstripe.fields.StripeCharField(choices=[('invalid_number', 'Invalid Number'), ('invalid_expiry_month', 'Invalid Expiry Month'), ('invalid_expiry_year', 'Invalid Expiry Year'), ('invalid_cvc', 'Invalid Cvc'), ('incorrect_number', 'Incorrect Number'), ('expired_card', 'Expired Card'), ('incorrect_cvc', 'Incorrect Cvc'), ('incorrect_zip', 'Incorrect Zip'), ('card_declined', 'Card Declined'), ('missing', 'Missing'), ('processing_error', 'Processing Error'), ('rate_limit', 'Rate Limit')], max_length=30, help_text='Error code explaining reason for charge failure if available.', null=True),
        ),
        migrations.AddField(
            model_name='charge',
            name='failure_message',
            field=djstripe.fields.StripeTextField(help_text='Message to user further explaining reason for charge failure if available.', null=True),
        ),
        migrations.AddField(
            model_name='charge',
            name='fee_details',
            field=djstripe.fields.StripeJSONField(default={}),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='charge',
            name='fraudulent',
            field=djstripe.fields.StripeBooleanField(help_text='Whether or not this charge was marked as fraudulent.', default=False),
        ),
        migrations.AddField(
            model_name='charge',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.', default=False),
        ),
        migrations.AddField(
            model_name='charge',
            name='metadata',
            field=djstripe.fields.StripeJSONField(blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.', null=True),
        ),
        migrations.AddField(
            model_name='charge',
            name='shipping',
            field=djstripe.fields.StripeJSONField(help_text='Shipping information for the charge', null=True),
        ),
        migrations.AddField(
            model_name='charge',
            name='source_stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, help_text='The payment source id.', null=True),
        ),
        migrations.AddField(
            model_name='charge',
            name='source_type',
            field=djstripe.fields.StripeCharField(max_length=20, help_text='The payment source type. If the payment source is supported by dj-stripe, a corresponding model is attached to this Charge via a foreign key matching this field.', null=True),
        ),
        migrations.AddField(
            model_name='charge',
            name='statement_descriptor',
            field=djstripe.fields.StripeCharField(max_length=22, help_text='An arbitrary string to be displayed on your customer\'s credit card statement. The statement description may not include <>"\' characters, and will appear on your customer\'s statement in capital letters. Non-ASCII characters are automatically stripped. While most banks display this information consistently, some may display it incorrectly or not at all.', null=True),
        ),
        migrations.AddField(
            model_name='charge',
            name='status',
            field=djstripe.fields.StripeCharField(help_text='The status of the payment.', choices=[('succeeded', 'Succeeded'), ('failed', 'Failed')], max_length=10, default='unknown'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='charge',
            name='transfer',
            field=models.ForeignKey(null=True, to='djstripe.Transfer', help_text='The transfer to the destination account (only applicable if the charge was created using the destination parameter).'),
        ),
        migrations.AddField(
            model_name='customer',
            name='account_balance',
            field=djstripe.fields.StripeIntegerField(help_text="Current balance, if any, being stored on the customer's account. If negative, the customer has credit to apply to the next invoice. If positive, the customer has an amount owed that will be added to the next invoice. The balance does not refer to any unpaid invoices; it solely takes into account amounts that have yet to be successfully applied to any invoice. This balance is only taken into account for recurring charges.", null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='business_vat_id',
            field=djstripe.fields.StripeCharField(max_length=20, help_text="The customer's VAT identification number.", null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='currency',
            field=djstripe.fields.StripeCharField(help_text='The currency the customer can be charged in for recurring billing purposes (subscriptions, invoices, invoice items).', max_length=3, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='customer',
            name='delinquent',
            field=djstripe.fields.StripeBooleanField(help_text="Whether or not the latest charge for the customer's latest invoice has failed.", default=False),
        ),
        migrations.AddField(
            model_name='customer',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.', default=False),
        ),
        migrations.AddField(
            model_name='customer',
            name='metadata',
            field=djstripe.fields.StripeJSONField(blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.', null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='shipping',
            field=djstripe.fields.StripeJSONField(help_text='Shipping information associated with the customer.', null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='metadata',
            field=djstripe.fields.StripeJSONField(blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='received_api_version',
            field=djstripe.fields.StripeCharField(max_length=15, help_text='the API version at which the event data was rendered. Blank for old entries only, all new entries will have this value', blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='request_id',
            field=djstripe.fields.StripeCharField(max_length=50, help_text="Information about the request that triggered this event, for traceability purposes. If empty string then this is an old entry without that data. If Null then this is not an old entry, but a Stripe 'automated' event with no associated request.", blank=True, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.', null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='amount_due',
            field=djstripe.fields.StripeCurrencyField(help_text="Final amount due at this time for this invoice. If the invoice's total is smaller than the minimum charge amount, for example, or if there is account credit that can be applied to the invoice, the amount_due may be 0. If there is a positive starting_balance for the invoice (the customer owes money), the amount_due will also take that into account. The charge that gets generated for the invoice will be for the amount specified in amount_due.", max_digits=7, default=0, decimal_places=2),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='invoice',
            name='application_fee',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, help_text="The fee in cents that will be applied to the invoice and transferred to the application owner's Stripe account when the invoice is paid.", decimal_places=2, null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='currency',
            field=djstripe.fields.StripeCharField(help_text='Three-letter ISO currency code.', max_length=3, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='invoice',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='ending_balance',
            field=djstripe.fields.StripeIntegerField(help_text='Ending customer balance after attempting to pay invoice. If the invoice has not been attempted yet, this will be null.', null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='forgiven',
            field=djstripe.fields.StripeBooleanField(help_text='Whether or not the invoice has been forgiven. Forgiving an invoice instructs us to update the subscription status as if the invoice were successfully paid. Once an invoice has been forgiven, it cannot be unforgiven or reopened.', default=False),
        ),
        migrations.AddField(
            model_name='invoice',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.', default=False),
        ),
        migrations.AddField(
            model_name='invoice',
            name='metadata',
            field=djstripe.fields.StripeJSONField(blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.', null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='next_payment_attempt',
            field=djstripe.fields.StripeDateTimeField(help_text='The time at which payment will next be attempted.', null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='starting_balance',
            field=djstripe.fields.StripeIntegerField(help_text='Starting customer balance before attempting to pay invoice. If the invoice has not been attempted yet, this will be the current customer balance.', default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='invoice',
            name='statement_descriptor',
            field=djstripe.fields.StripeCharField(max_length=22, help_text='An arbitrary string to be displayed on your customer\'s credit card statement. The statement description may not include <>"\' characters, and will appear on your customer\'s statement in capital letters. Non-ASCII characters are automatically stripped. While most banks display this information consistently, some may display it incorrectly or not at all.', null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.', null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='subscription',
            field=models.ForeignKey(related_name='invoices', null=True, to='djstripe.Subscription', help_text='The subscription that this invoice was prepared for, if any.'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='subscription_proration_date',
            field=djstripe.fields.StripeDateTimeField(help_text='Only set for upcoming invoices that preview prorations. The time used to calculate prorations.', null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='tax',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, help_text='The amount of tax included in the total, calculated from ``tax_percent`` and the subtotal. If no ``tax_percent`` is defined, this value will be null.', decimal_places=2, null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='tax_percent',
            field=djstripe.fields.StripePercentField(validators=[django.core.validators.MinValueValidator(1.0), django.core.validators.MaxValueValidator(100.0)], max_digits=5, help_text="This percentage of the subtotal has been added to the total amount of the invoice, including invoice line items and discounts. This field is inherited from the subscription's ``tax_percent`` field, but can be changed before the invoice is paid. This field defaults to null.", decimal_places=2, null=True),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='customer',
            field=models.ForeignKey(related_name='invoiceitems', default=1, to='djstripe.Customer', help_text='The customer associated with this invoiceitem.'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='date',
            field=djstripe.fields.StripeDateTimeField(help_text='The date on the invoiceitem.', default=datetime.datetime(2100, 1, 1, 0, 0)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='discountable',
            field=djstripe.fields.StripeBooleanField(help_text='If True, discounts will apply to this invoice item. Always False for prorations.', default=False),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.', default=False),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='metadata',
            field=djstripe.fields.StripeJSONField(blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.', null=True),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.', null=True),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='subscription',
            field=models.ForeignKey(related_name='invoiceitems', null=True, to='djstripe.Subscription', help_text='The subscription that this invoice item has been created for, if any.'),
        ),
        migrations.AddField(
            model_name='plan',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True),
        ),
        migrations.AddField(
            model_name='plan',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.', default=False),
        ),
        migrations.AddField(
            model_name='plan',
            name='metadata',
            field=djstripe.fields.StripeJSONField(blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.', null=True),
        ),
        migrations.AddField(
            model_name='plan',
            name='statement_descriptor',
            field=djstripe.fields.StripeCharField(max_length=22, help_text='An arbitrary string to be displayed on your customer\'s credit card statement. The statement description may not include <>"\' characters, and will appear on your customer\'s statement in capital letters. Non-ASCII characters are automatically stripped. While most banks display this information consistently, some may display it incorrectly or not at all.', null=True),
        ),
        migrations.AddField(
            model_name='plan',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.', null=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='application_fee_percent',
            field=djstripe.fields.StripePercentField(validators=[django.core.validators.MinValueValidator(1.0), django.core.validators.MaxValueValidator(100.0)], help_text='A positive decimal that represents the fee percentage of the subscription invoice amount that will be transferred to the application owner’s Stripe account each billing period.', max_digits=5, decimal_places=2, null=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.', default=False),
        ),
        migrations.AddField(
            model_name='subscription',
            name='metadata',
            field=djstripe.fields.StripeJSONField(blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.', null=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, default='unknown', unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='subscription',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.', null=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='tax_percent',
            field=djstripe.fields.StripePercentField(validators=[django.core.validators.MinValueValidator(1.0), django.core.validators.MaxValueValidator(100.0)], max_digits=5, help_text='A positive decimal (with at most two decimal places) between 1 and 100. This represents the percentage of the subscription invoice subtotal that will be calculated and added as tax to the final amount each billing period.', decimal_places=2, null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='amount_reversed',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, help_text='The amount reversed (can be less than the amount attribute on the transfer if a partial reversal was issued).', decimal_places=2, null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='currency',
            field=djstripe.fields.StripeCharField(help_text='Three-letter ISO currency code.', max_length=3, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transfer',
            name='destination',
            field=djstripe.fields.StripeIdField(help_text='ID of the bank account, card, or Stripe account the transfer was sent to.', max_length=50, default='unknown'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transfer',
            name='destination_payment',
            field=djstripe.fields.StripeIdField(max_length=50, help_text='If the destination is a Stripe account, this will be the ID of the payment that the destination account received for the transfer.', null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='destination_type',
            field=djstripe.fields.StripeCharField(help_text='The type of the transfer destination.', choices=[('card', 'Card'), ('bank_account', 'Bank Account'), ('stripe_account', 'Stripe Account')], max_length=14, default='unknown'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transfer',
            name='failure_code',
            field=djstripe.fields.StripeCharField(choices=[('insufficient_funds', 'Insufficient Funds'), ('account_closed', 'Account Closed'), ('no_account', 'No Account'), ('invalid_account_number', 'Invalid Account Number'), ('debit_not_authorized', 'Debit Not Authorized'), ('bank_ownership_changed', 'Bank Ownership Changed'), ('account_frozen', 'Account Frozen'), ('could_not_process', 'Could Not Process'), ('bank_account_restricted', 'Bank Account Restricted'), ('invalid_currency', 'Invalid Currency')], max_length=23, help_text='Error code explaining reason for transfer failure if available. See https://stripe.com/docs/api/python#transfer_failures.', null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='failure_message',
            field=djstripe.fields.StripeTextField(help_text='Message to user further explaining reason for transfer failure if available.', null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='fee',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, default=0, decimal_places=2),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transfer',
            name='fee_details',
            field=djstripe.fields.StripeJSONField(default={}),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transfer',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.', default=False),
        ),
        migrations.AddField(
            model_name='transfer',
            name='metadata',
            field=djstripe.fields.StripeJSONField(blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.', null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='reversed',
            field=djstripe.fields.StripeBooleanField(help_text='Whether or not the transfer has been fully reversed. If the transfer is only partially reversed, this attribute will still be false.', default=False),
        ),
        migrations.AddField(
            model_name='transfer',
            name='source_transaction',
            field=djstripe.fields.StripeIdField(max_length=50, help_text='ID of the charge (or other transaction) that was used to fund the transfer. If null, the transfer was funded from the available balance.', null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='source_type',
            field=djstripe.fields.StripeCharField(help_text='The source balance from which this transfer came.', choices=[('card', 'Card'), ('bank_account', 'Bank Account'), ('bitcoin_reciever', 'Bitcoin Reciever'), ('alipay_account', 'Alipay Account')], max_length=16, default='unknown'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transfer',
            name='statement_descriptor',
            field=djstripe.fields.StripeCharField(max_length=22, help_text='An arbitrary string to be displayed on your customer\'s credit card statement. The statement description may not include <>"\' characters, and will appear on your customer\'s statement in capital letters. Non-ASCII characters are automatically stripped. While most banks display this information consistently, some may display it incorrectly or not at all.', null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.', null=True),
        ),
        migrations.AlterField(
            model_name='charge',
            name='amount',
            field=djstripe.fields.StripeCurrencyField(help_text='Amount charged.', max_digits=7, default=0, decimal_places=2),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='charge',
            name='amount_refunded',
            field=djstripe.fields.StripeCurrencyField(help_text='Amount refunded (can be less than the amount attribute on the charge if a partial refund was issued).', max_digits=7, default=0, decimal_places=2),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='charge',
            name='captured',
            field=djstripe.fields.StripeBooleanField(help_text='If the charge was created without capturing, this boolean represents whether or not it is still uncaptured or has since been captured.', default=False),
        ),
        migrations.AlterField(
            model_name='charge',
            name='customer',
            field=models.ForeignKey(related_name='charges', to='djstripe.Customer', help_text='The customer associated with this charge.'),
        ),
        migrations.AlterField(
            model_name='charge',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True),
        ),
        migrations.AlterField(
            model_name='charge',
            name='disputed',
            field=djstripe.fields.StripeBooleanField(help_text='Whether or not this charge is disputed.', default=False),
        ),
        migrations.AlterField(
            model_name='charge',
            name='fee',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, default=0, decimal_places=2),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='charge',
            name='paid',
            field=djstripe.fields.StripeBooleanField(help_text='True if the charge succeeded, or was successfully authorized for later capture, False otherwise.', default=False),
        ),
        migrations.AlterField(
            model_name='charge',
            name='refunded',
            field=djstripe.fields.StripeBooleanField(help_text='Whether or not the charge has been fully refunded. If the charge is only partially refunded, this attribute will still be false.', default=False),
        ),
        migrations.AlterField(
            model_name='charge',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='charge',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.', null=True),
        ),
        migrations.AlterField(
            model_name='customer',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='customer',
            field=models.ForeignKey(null=True, to='djstripe.Customer', help_text='In the event that there is a related customer, this will point to that Customer record'),
        ),
        migrations.AlterField(
            model_name='event',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.', default=False),
        ),
        migrations.AlterField(
            model_name='event',
            name='processed',
            field=models.BooleanField(help_text='If validity is performed, webhook event processor(s) may run to take further action on the event. Once these have run, this is set to True.', default=False),
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
            field=models.NullBooleanField(help_text='Tri-state bool. Null == validity not yet confirmed. Otherwise, this field indicates that this event was checked via stripe api and found to be either authentic (valid=True) or in-authentic (possibly malicious)'),
        ),
        migrations.AlterField(
            model_name='event',
            name='webhook_message',
            field=djstripe.fields.StripeJSONField(help_text='data received at webhook. data should be considered to be garbage until validity check is run and valid flag is set'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='attempt_count',
            field=djstripe.fields.StripeIntegerField(help_text='Number of payment attempts made for this invoice, from the perspective of the payment retry schedule. Any payment attempt counts as the first attempt, and subsequently only automatic retries increment the attempt count. In other words, manual payment attempts after the first attempt do not affect the retry schedule.', default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='attempted',
            field=djstripe.fields.StripeBooleanField(help_text='Whether or not an attempt has been made to pay the invoice. An invoice is not attempted until 1 hour after the ``invoice.created`` webhook, for example, so you might not want to display that invoice as unpaid to your users.', default=False),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='charge',
            field=models.OneToOneField(to='djstripe.Charge', related_name='invoice', null=True, help_text='The latest charge generated for this invoice, if any.'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='closed',
            field=djstripe.fields.StripeBooleanField(help_text="Whether or not the invoice is still trying to collect payment. An invoice is closed if it's either paid or it has been marked closed. A closed invoice will no longer attempt to collect payment.", default=False),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='customer',
            field=models.ForeignKey(related_name='invoices', to='djstripe.Customer', help_text='The customer associated with this invoice.'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='date',
            field=djstripe.fields.StripeDateTimeField(help_text='The date on the invoice.'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='paid',
            field=djstripe.fields.StripeBooleanField(help_text='The time at which payment will next be attempted.', default=False),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='period_end',
            field=djstripe.fields.StripeDateTimeField(help_text='End of the usage period during which invoice items were added to this invoice.'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='period_start',
            field=djstripe.fields.StripeDateTimeField(help_text='Start of the usage period during which invoice items were added to this invoice.'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='subtotal',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, help_text='Only set for upcoming invoices that preview prorations. The time used to calculate prorations.', decimal_places=2),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='total',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2, verbose_name='Total after discount.'),
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
            field=models.ForeignKey(related_name='invoiceitems', to='djstripe.Invoice', help_text='The invoice to which this invoiceitem is attached.'),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='period_end',
            field=djstripe.fields.StripeDateTimeField(help_text="Might be the date when this invoiceitem's invoice was sent."),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='period_start',
            field=djstripe.fields.StripeDateTimeField(help_text='Might be the date when this invoiceitem was added to the invoice'),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='plan',
            field=models.ForeignKey(related_name='invoiceitems', null=True, to='djstripe.Plan', help_text='If the invoice item is a proration, the plan of the subscription for which the proration was computed.'),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='proration',
            field=djstripe.fields.StripeBooleanField(help_text='Whether or not the invoice item was created automatically as a proration adjustment when the customer switched plans.', default=False),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='quantity',
            field=djstripe.fields.StripeIntegerField(help_text='If the invoice item is a proration, the quantity of the subscription for which the proration was computed.', null=True),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='plan',
            name='amount',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, help_text='Amount to be charged on the interval specified.', decimal_places=2),
        ),
        migrations.AlterField(
            model_name='plan',
            name='currency',
            field=djstripe.fields.StripeCharField(max_length=3, help_text='Three-letter ISO currency code'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='interval',
            field=djstripe.fields.StripeCharField(choices=[('day', 'Day'), ('week', 'Week'), ('month', 'Month'), ('year', 'Year')], max_length=5, help_text='The frequency with which a subscription should be billed.'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='interval_count',
            field=djstripe.fields.StripeIntegerField(help_text='The number of intervals (specified in the interval property) between each subscription billing.', null=True),
        ),
        migrations.AlterField(
            model_name='plan',
            name='name',
            field=djstripe.fields.StripeTextField(help_text='Name of the plan, to be displayed on invoices and in the web interface.'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='plan',
            name='trial_period_days',
            field=djstripe.fields.StripeIntegerField(help_text='Number of trial period days granted when subscribing a customer to this plan. Null if the plan has no trial period.', null=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='cancel_at_period_end',
            field=djstripe.fields.StripeBooleanField(help_text='If the subscription has been canceled with the ``at_period_end`` flag set to true, ``cancel_at_period_end`` on the subscription will be true. You can use this attribute to determine whether a subscription that has a status of active is scheduled to be canceled at the end of the current period.', default=False),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='canceled_at',
            field=djstripe.fields.StripeDateTimeField(help_text='If the subscription has been canceled, the date of that cancellation. If the subscription was canceled with ``cancel_at_period_end``, canceled_at will still reflect the date of the initial cancellation request, not the end of the subscription period when the subscription is automatically moved to a canceled state.', null=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='current_period_end',
            field=djstripe.fields.StripeDateTimeField(help_text='End of the current period for which the subscription has been invoiced. At the end of this period, a new invoice will be created.', default=datetime.datetime(2100, 1, 1, 0, 0)),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='subscription',
            name='current_period_start',
            field=djstripe.fields.StripeDateTimeField(help_text='Start of the current period for which the subscription has been invoiced.', default=datetime.datetime(2100, 1, 1, 0, 0)),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='subscription',
            name='customer',
            field=models.ForeignKey(related_name='subscriptions', default=1, to='djstripe.Customer', help_text='The customer associated with this subscription.'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='subscription',
            name='ended_at',
            field=djstripe.fields.StripeDateTimeField(help_text='If the subscription has ended (either because it was canceled or because the customer was switched to a subscription to a new plan), the date the subscription ended.', null=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='plan',
            field=models.ForeignKey(related_name='subscriptions', to='djstripe.Plan', help_text='The plan associated with this subscription.'),
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
            field=djstripe.fields.StripeCharField(choices=[('trialing', 'Trialing'), ('active', 'Active'), ('past_due', 'Past Due'), ('canceled', 'Canceled'), ('unpaid', 'Unpaid')], max_length=8, help_text='The status of this subscription.'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='trial_end',
            field=djstripe.fields.StripeDateTimeField(help_text='If the subscription has a trial, the end of that trial.', null=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='trial_start',
            field=djstripe.fields.StripeDateTimeField(help_text='If the subscription has a trial, the beginning of that trial.', null=True),
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
            field=djstripe.fields.StripeCurrencyField(max_digits=7, help_text='The amount transferred', decimal_places=2),
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
            field=djstripe.fields.StripeDateTimeField(help_text="Date the transfer is scheduled to arrive in the bank. This doesn't factor in delays like weekends or bank holidays."),
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
            field=djstripe.fields.StripeCharField(choices=[('paid', 'Paid'), ('pending', 'Pending'), ('in_transit', 'In Transit'), ('canceled', 'Canceled'), ('failed', 'Failed')], max_length=10, help_text='The current status of the transfer. A transfer will be pending until it is submitted to the bank, at which point it becomes in_transit. It will then change to paid if the transaction goes through. If it does not go through successfully, its status will change to failed or canceled.'),
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
        migrations.CreateModel(
            name='Card',
            fields=[
                ('stripesource_ptr', models.OneToOneField(serialize=False, parent_link=True, primary_key=True, to='djstripe.StripeSource', auto_created=True)),
                ('address_city', djstripe.fields.StripeTextField(help_text='Billing address city.', null=True)),
                ('address_country', djstripe.fields.StripeTextField(help_text='Billing address country.', null=True)),
                ('address_line1', djstripe.fields.StripeTextField(help_text='Billing address (Line 1).', null=True)),
                ('address_line1_check', djstripe.fields.StripeCharField(choices=[('pass', 'Pass'), ('fail', 'Fail'), ('unavailable', 'Unavailable'), ('unknown', 'Unknown')], max_length=11, help_text='If ``address_line1`` was provided, results of the check.', null=True)),
                ('address_line2', djstripe.fields.StripeTextField(help_text='Billing address (Line 2).', null=True)),
                ('address_state', djstripe.fields.StripeTextField(help_text='Billing address state.', null=True)),
                ('address_zip', djstripe.fields.StripeTextField(help_text='Billing address zip code.', null=True)),
                ('address_zip_check', djstripe.fields.StripeCharField(choices=[('pass', 'Pass'), ('fail', 'Fail'), ('unavailable', 'Unavailable'), ('unknown', 'Unknown')], max_length=11, help_text='If ``address_zip`` was provided, results of the check.', null=True)),
                ('brand', djstripe.fields.StripeCharField(choices=[('Visa', 'Visa'), ('American Express', 'American Express'), ('MasterCard', 'MasterCard'), ('Discover', 'Discover'), ('JCB', 'JCB'), ('Diners Club', 'Diners Club'), ('Unknown', 'Unknown')], max_length=16, help_text='Card brand.')),
                ('country', djstripe.fields.StripeCharField(max_length=2, help_text='Two-letter ISO code representing the country of the card.')),
                ('cvc_check', djstripe.fields.StripeCharField(choices=[('pass', 'Pass'), ('fail', 'Fail'), ('unavailable', 'Unavailable'), ('unknown', 'Unknown')], max_length=11, help_text='If a CVC was provided, results of the check.', null=True)),
                ('dynamic_last4', djstripe.fields.StripeCharField(max_length=4, help_text='(For tokenized numbers only.) The last four digits of the device account number.', null=True)),
                ('exp_month', djstripe.fields.StripeIntegerField(help_text='Card expiration month.')),
                ('exp_year', djstripe.fields.StripeIntegerField(help_text='Card expiration year.')),
                ('fingerprint', djstripe.fields.StripeTextField(help_text='Uniquely identifies this particular card number.', null=True)),
                ('funding', djstripe.fields.StripeCharField(choices=[('credit', 'Credit'), ('debit', 'Debit'), ('prepaid', 'Prepaid'), ('unknown', 'Unknown')], max_length=7, help_text='Card funding type.')),
                ('last4', djstripe.fields.StripeCharField(max_length=4, help_text='Last four digits of Card number.')),
                ('name', djstripe.fields.StripeTextField(help_text='Cardholder name.', null=True)),
                ('tokenization_method', djstripe.fields.StripeCharField(choices=[('apple_pay', 'Apple Pay'), ('android_pay', 'Android Pay')], max_length=11, help_text='If the card number is tokenized, this is the method that was used.', null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('djstripe.stripesource',),
        ),
        migrations.DeleteModel(
            name='TransferChargeFee',
        ),
        migrations.AddField(
            model_name='stripesource',
            name='customer',
            field=models.ForeignKey(related_name='sources', to='djstripe.Customer'),
        ),
        migrations.AddField(
            model_name='stripesource',
            name='polymorphic_ctype',
            field=models.ForeignKey(related_name='polymorphic_djstripe.stripesource_set+', to='contenttypes.ContentType', editable=False, null=True),
        ),
        migrations.AddField(
            model_name='charge',
            name='account',
            field=models.ForeignKey(related_name='charges', null=True, to='djstripe.Account', help_text='The account the charge was made on behalf of. Null here indicates that this value was never set.'),
        ),
        migrations.AddField(
            model_name='charge',
            name='source',
            field=models.ForeignKey(related_name='charges', null=True, to='djstripe.StripeSource'),
        ),
        migrations.AddField(
            model_name='customer',
            name='default_source',
            field=models.ForeignKey(related_name='customers', null=True, to='djstripe.StripeSource'),
        ),
    ]
