# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import model_utils.fields
import djstripe.fields
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('djstripe', '0008_auto_20150806_1641'),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('created', model_utils.fields.AutoCreatedField(verbose_name='created', editable=False, default=django.utils.timezone.now)),
                ('modified', model_utils.fields.AutoLastModifiedField(verbose_name='modified', editable=False, default=django.utils.timezone.now)),
                ('stripe_id', djstripe.fields.StripeIdField(unique=True, max_length=50)),
                ('livemode', djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.')),
                ('stripe_timestamp', djstripe.fields.StripeDateTimeField(null=True, help_text='The datetime this object was created in stripe.')),
                ('metadata', djstripe.fields.StripeJSONField(null=True, blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.')),
                ('description', djstripe.fields.StripeTextField(null=True, blank=True, help_text='A description of this object.')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StripeSource',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('created', model_utils.fields.AutoCreatedField(verbose_name='created', editable=False, default=django.utils.timezone.now)),
                ('modified', model_utils.fields.AutoLastModifiedField(verbose_name='modified', editable=False, default=django.utils.timezone.now)),
                ('stripe_id', djstripe.fields.StripeIdField(unique=True, max_length=50)),
                ('livemode', djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.')),
                ('stripe_timestamp', djstripe.fields.StripeDateTimeField(null=True, help_text='The datetime this object was created in stripe.')),
                ('metadata', djstripe.fields.StripeJSONField(null=True, blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.')),
                ('description', djstripe.fields.StripeTextField(null=True, blank=True, help_text='A description of this object.')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='event',
            name='validated_message',
        ),
        migrations.AddField(
            model_name='charge',
            name='currency',
            field=djstripe.fields.StripeCharField(null=True, max_length=3, help_text='Three-letter ISO currency code representing the currency in which the charge was made.'),
        ),
        migrations.AddField(
            model_name='charge',
            name='failure_code',
            field=djstripe.fields.StripeCharField(null=True, choices=[('invalid_number', 'Invalid Number'), ('invalid_expiry_month', 'Invalid Expiry Month'), ('invalid_expiry_year', 'Invalid Expiry Year'), ('invalid_cvc', 'Invalid Cvc'), ('incorrect_number', 'Incorrect Number'), ('expired_card', 'Expired Card'), ('incorrect_cvc', 'Incorrect Cvc'), ('incorrect_zip', 'Incorrect Zip'), ('card_declined', 'Card Declined'), ('missing', 'Missing'), ('processing_error', 'Processing Error'), ('rate_limit', 'Rate Limit')], max_length=30, help_text='Error code explaining reason for charge failure if available.'),
        ),
        migrations.AddField(
            model_name='charge',
            name='failure_message',
            field=djstripe.fields.StripeTextField(null=True, help_text='Message to user further explaining reason for charge failure if available.'),
        ),
        migrations.AddField(
            model_name='charge',
            name='fraudulent',
            field=djstripe.fields.StripeBooleanField(help_text='Whether or not this charge was marked as fraudulent.', default=False),
        ),
        migrations.AddField(
            model_name='charge',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AddField(
            model_name='charge',
            name='metadata',
            field=djstripe.fields.StripeJSONField(null=True, blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.'),
        ),
        migrations.AddField(
            model_name='charge',
            name='shipping',
            field=djstripe.fields.StripeJSONField(null=True, help_text='Shipping information for the charge'),
        ),
        migrations.AddField(
            model_name='charge',
            name='source_stripe_id',
            field=djstripe.fields.StripeIdField(null=True, max_length=50, help_text='The payment source id.'),
        ),
        migrations.AddField(
            model_name='charge',
            name='source_type',
            field=djstripe.fields.StripeCharField(null=True, max_length=20, help_text='The payment source type. If the payment source is supported by dj-stripe, a corresponding model is attached to this Charge via a foreign key matching this field.'),
        ),
        migrations.AddField(
            model_name='charge',
            name='status',
            field=djstripe.fields.StripeCharField(null=True, choices=[('succeeded', 'Succeeded'), ('failed', 'Failed')], max_length=10, help_text='The status of the payment is either ``succeeded`` or ``failed``.'),
        ),
        migrations.AddField(
            model_name='charge',
            name='transfer',
            field=models.ForeignKey(help_text='The transfer to the destination account (only applicable if the charge was created using the destination parameter).', null=True, to='djstripe.Transfer'),
        ),
        migrations.AddField(
            model_name='customer',
            name='account_balance',
            field=djstripe.fields.StripeIntegerField(null=True, help_text="Current balance, if any, being stored on the customer's account. If negative, the customer has credit to apply to the next invoice. If positive, the customer has an amount owed that will be added to the next invoice. The balance does not refer to any unpaid invoices; it solely takes into account amounts that have yet to be successfully applied to any invoice. This balance is only taken into account for recurring charges."),
        ),
        migrations.AddField(
            model_name='customer',
            name='currency',
            field=djstripe.fields.StripeCharField(null=True, max_length=3, help_text='The currency the customer can be charged in for recurring billing purposes (subscriptions, invoices, invoice items).'),
        ),
        migrations.AddField(
            model_name='customer',
            name='delinquent',
            field=djstripe.fields.StripeBooleanField(help_text='Whether or not the latest charge for the customer’s latest invoice has failed.', default=False),
        ),
        migrations.AddField(
            model_name='customer',
            name='description',
            field=djstripe.fields.StripeTextField(null=True, blank=True, help_text='A description of this object.'),
        ),
        migrations.AddField(
            model_name='customer',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AddField(
            model_name='customer',
            name='metadata',
            field=djstripe.fields.StripeJSONField(null=True, blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.'),
        ),
        migrations.AddField(
            model_name='customer',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(null=True, help_text='The datetime this object was created in stripe.'),
        ),
        migrations.AddField(
            model_name='event',
            name='description',
            field=djstripe.fields.StripeTextField(null=True, blank=True, help_text='A description of this object.'),
        ),
        migrations.AddField(
            model_name='event',
            name='metadata',
            field=djstripe.fields.StripeJSONField(null=True, blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.'),
        ),
        migrations.AddField(
            model_name='event',
            name='received_api_version',
            field=djstripe.fields.StripeCharField(help_text='the API version at which the event data was rendered. Blank for old entries only, all new entries will have this value', blank=True, max_length=15),
        ),
        migrations.AddField(
            model_name='event',
            name='request_id',
            field=djstripe.fields.StripeCharField(null=True, blank=True, max_length=50, help_text="Information about the request that triggered this event, for traceability purposes. If empty string then this is an old entry without that data. If Null then this is not an old entry, but a Stripe 'automated' event with no associated request."),
        ),
        migrations.AddField(
            model_name='event',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(null=True, help_text='The datetime this object was created in stripe.'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='description',
            field=djstripe.fields.StripeTextField(null=True, blank=True, help_text='A description of this object.'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='metadata',
            field=djstripe.fields.StripeJSONField(null=True, blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(null=True, help_text='The datetime this object was created in stripe.'),
        ),
        migrations.AddField(
            model_name='plan',
            name='description',
            field=djstripe.fields.StripeTextField(null=True, blank=True, help_text='A description of this object.'),
        ),
        migrations.AddField(
            model_name='plan',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AddField(
            model_name='plan',
            name='metadata',
            field=djstripe.fields.StripeJSONField(null=True, blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.'),
        ),
        migrations.AddField(
            model_name='plan',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(null=True, help_text='The datetime this object was created in stripe.'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='metadata',
            field=djstripe.fields.StripeJSONField(null=True, blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(null=True, help_text='The datetime this object was created in stripe.'),
        ),
        migrations.AlterField(
            model_name='charge',
            name='amount',
            field=djstripe.fields.StripeCurrencyField(null=True, max_digits=7, decimal_places=2, help_text='Amount charged.'),
        ),
        migrations.AlterField(
            model_name='charge',
            name='amount_refunded',
            field=djstripe.fields.StripeCurrencyField(null=True, max_digits=7, decimal_places=2, help_text='Amount refunded (can be less than the amount attribute on the charge if a partial refund was issued).'),
        ),
        migrations.AlterField(
            model_name='charge',
            name='captured',
            field=djstripe.fields.StripeBooleanField(help_text='If the charge was created without capturing, this boolean represents whether or not it is still uncaptured or has since been captured.', default=False),
        ),
        migrations.AlterField(
            model_name='charge',
            name='card_kind',
            field=djstripe.fields.StripeCharField(null=True, default=None, max_length=50),
        ),
        migrations.AlterField(
            model_name='charge',
            name='card_last_4',
            field=djstripe.fields.StripeCharField(null=True, default=None, max_length=4),
        ),
        migrations.AlterField(
            model_name='charge',
            name='customer',
            field=models.ForeignKey(help_text='The customer associated with this charge.', related_name='charges', to='djstripe.Customer'),
        ),
        migrations.AlterField(
            model_name='charge',
            name='description',
            field=djstripe.fields.StripeTextField(null=True, blank=True, help_text='A description of this object.'),
        ),
        migrations.AlterField(
            model_name='charge',
            name='disputed',
            field=djstripe.fields.StripeBooleanField(help_text='Whether or not this charge is disputed.', default=False),
        ),
        migrations.AlterField(
            model_name='charge',
            name='fee',
            field=djstripe.fields.StripeCurrencyField(null=True, max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='charge',
            name='invoice',
            field=models.ForeignKey(help_text='The invoice associated with this charge, if it exists.', related_name='charges', null=True, to='djstripe.Invoice'),
        ),
        migrations.AlterField(
            model_name='charge',
            name='paid',
            field=djstripe.fields.StripeBooleanField(help_text='``true`` if the charge succeeded, or was successfully authorized for later capture, ``false`` otherwise.', default=False),
        ),
        migrations.AlterField(
            model_name='charge',
            name='refunded',
            field=djstripe.fields.StripeBooleanField(help_text='Whether or not the charge has been fully refunded. If the charge is only partially refunded, this attribute will still be false.', default=False),
        ),
        migrations.AlterField(
            model_name='charge',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(unique=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='charge',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(null=True, help_text='The datetime this object was created in stripe.'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='card_exp_month',
            field=djstripe.fields.StripePositiveIntegerField(null=True, default=None),
        ),
        migrations.AlterField(
            model_name='customer',
            name='card_exp_year',
            field=djstripe.fields.StripePositiveIntegerField(null=True, default=None),
        ),
        migrations.AlterField(
            model_name='customer',
            name='card_fingerprint',
            field=djstripe.fields.StripeCharField(null=True, default=None, max_length=200),
        ),
        migrations.AlterField(
            model_name='customer',
            name='card_kind',
            field=djstripe.fields.StripeCharField(null=True, default=None, max_length=50),
        ),
        migrations.AlterField(
            model_name='customer',
            name='card_last_4',
            field=djstripe.fields.StripeCharField(null=True, default=None, max_length=4),
        ),
        migrations.AlterField(
            model_name='customer',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(unique=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='event',
            name='customer',
            field=models.ForeignKey(help_text='In the event that there is a related customer, this will point to that Customer record', null=True, to='djstripe.Customer'),
        ),
        migrations.AlterField(
            model_name='event',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AlterField(
            model_name='event',
            name='processed',
            field=models.BooleanField(help_text='If validity is performed, webhook event processor(s) may run to take further action on the event. Once these have run, this is set to True.', default=False),
        ),
        migrations.AlterField(
            model_name='event',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(unique=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='event',
            name='type',
            field=djstripe.fields.StripeCharField(help_text="Stripe's event description code", max_length=250),
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
            name='attempted',
            field=djstripe.fields.StripeNullBooleanField(),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='attempts',
            field=djstripe.fields.StripePositiveIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='charge',
            field=djstripe.fields.StripeIdField(null=True, blank=True, default='', max_length=50),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='closed',
            field=djstripe.fields.StripeBooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='date',
            field=djstripe.fields.StripeDateTimeField(),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='paid',
            field=djstripe.fields.StripeBooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='period_end',
            field=djstripe.fields.StripeDateTimeField(),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='period_start',
            field=djstripe.fields.StripeDateTimeField(),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(unique=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='subtotal',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='total',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='plan',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(unique=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='adjustment_count',
            field=djstripe.fields.StripeIntegerField(),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='adjustment_fees',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='adjustment_gross',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='amount',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='charge_count',
            field=djstripe.fields.StripeIntegerField(),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='charge_fees',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='charge_gross',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='collected_fee_count',
            field=djstripe.fields.StripeIntegerField(),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='collected_fee_gross',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='date',
            field=djstripe.fields.StripeDateTimeField(help_text='Date the transfer is scheduled to arrive at destination'),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='description',
            field=djstripe.fields.StripeTextField(null=True, blank=True, help_text='A description of this object.'),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='event',
            field=models.ForeignKey(to='djstripe.Event', related_name='transfers', null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='net',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='refund_count',
            field=djstripe.fields.StripeIntegerField(),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='refund_fees',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='refund_gross',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='status',
            field=djstripe.fields.StripeCharField(max_length=25),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(unique=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='validation_count',
            field=djstripe.fields.StripeIntegerField(),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='validation_fees',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.CreateModel(
            name='Card',
            fields=[
                ('stripesource_ptr', models.OneToOneField(to='djstripe.StripeSource', primary_key=True, auto_created=True, parent_link=True, serialize=False)),
                ('brand', djstripe.fields.StripeCharField(help_text='Card brand.', choices=[('Visa', 'Visa'), ('American Express', 'American Express'), ('MasterCard', 'MasterCard'), ('Discover', 'Discover'), ('JCB', 'JCB'), ('Diners Club', 'Diners Club'), ('Unknown', 'Unknown')], max_length=16)),
                ('exp_month', djstripe.fields.StripeIntegerField(help_text='Card expiration month.')),
                ('exp_year', djstripe.fields.StripeIntegerField(help_text='Card expiration year.')),
                ('funding', djstripe.fields.StripeCharField(help_text='Card funding type.', choices=[('credit', 'Credit'), ('debit', 'Debit'), ('prepaid', 'Prepaid'), ('unknown', 'Unknown')], max_length=7)),
                ('last4', djstripe.fields.StripeCharField(help_text='Last four digits of Card number.', max_length=4)),
                ('address_city', djstripe.fields.StripeTextField(null=True, help_text='Billing address city.')),
                ('address_country', djstripe.fields.StripeTextField(null=True, help_text='Billing address country.')),
                ('address_line1', djstripe.fields.StripeTextField(null=True, help_text='Billing address (Line 1).')),
                ('address_line1_check', djstripe.fields.StripeCharField(null=True, choices=[('pass', 'Pass'), ('fail', 'Fail'), ('unavailable', 'Unavailable'), ('unknown', 'Unknown')], max_length=11, help_text='If ``address_line1`` was provided, results of the check.')),
                ('address_line2', djstripe.fields.StripeTextField(null=True, help_text='Billing address (Line 2).')),
                ('address_state', djstripe.fields.StripeTextField(null=True, help_text='Billing address state.')),
                ('address_zip', djstripe.fields.StripeTextField(null=True, help_text='Billing address zip code.')),
                ('address_zip_check', djstripe.fields.StripeCharField(null=True, choices=[('pass', 'Pass'), ('fail', 'Fail'), ('unavailable', 'Unavailable'), ('unknown', 'Unknown')], max_length=11, help_text='If ``address_zip`` was provided, results of the check.')),
                ('country', djstripe.fields.StripeCharField(help_text='Two-letter ISO code representing the country of the card.', max_length=2)),
                ('cvc_check', djstripe.fields.StripeCharField(null=True, choices=[('pass', 'Pass'), ('fail', 'Fail'), ('unavailable', 'Unavailable'), ('unknown', 'Unknown')], max_length=11, help_text='If a CVC was provided, results of the check.')),
                ('dynamic_last4', djstripe.fields.StripeCharField(null=True, max_length=4, help_text='(For tokenized numbers only.) The last four digits of the device account number.')),
                ('name', djstripe.fields.StripeTextField(null=True, help_text='Cardholder name.')),
                ('tokenization_method', djstripe.fields.StripeCharField(null=True, choices=[('apple_pay', 'Apple Pay'), ('android_pay', 'Android Pay')], max_length=11, help_text='If the card number is tokenized, this is the method that was used.')),
                ('fingerprint', djstripe.fields.StripeTextField(null=True, help_text='Uniquely identifies this particular card number.')),
            ],
            options={
                'abstract': False,
            },
            bases=('djstripe.stripesource',),
        ),
        migrations.AddField(
            model_name='stripesource',
            name='customer',
            field=models.ForeignKey(to='djstripe.Customer', related_name='sources'),
        ),
        migrations.AddField(
            model_name='stripesource',
            name='polymorphic_ctype',
            field=models.ForeignKey(to='contenttypes.ContentType', editable=False, related_name='polymorphic_djstripe.stripesource_set+', null=True),
        ),
        migrations.AddField(
            model_name='charge',
            name='account',
            field=models.ForeignKey(help_text='The account the charge was made on behalf of. Null here indicates that this value was never set.', related_name='charges', null=True, to='djstripe.Account'),
        ),
        migrations.AddField(
            model_name='charge',
            name='source',
            field=models.ForeignKey(to='djstripe.StripeSource', related_name='charges', null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='default_source',
            field=models.ForeignKey(to='djstripe.StripeSource', related_name='customers', null=True),
        ),
    ]
