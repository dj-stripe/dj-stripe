# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields

import djstripe.fields


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
                ('created', model_utils.fields.AutoCreatedField(verbose_name='created',
                                                                default=django.utils.timezone.now, editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(verbose_name='modified',
                                                                      default=django.utils.timezone.now,
                                                                      editable=False)),
                ('stripe_id', djstripe.fields.StripeIdField(max_length=50, unique=True)),
                ('livemode', djstripe.fields.StripeNullBooleanField(
                    help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. \
                    Otherwise, this field indicates whether this record comes from Stripe test mode or live mode \
                    operation.', default=False)),
                ('stripe_timestamp', djstripe.fields.StripeDateTimeField(
                    help_text='The datetime this object was created in stripe.', null=True)),
                ('metadata', djstripe.fields.StripeJSONField(
                    blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful\
                     for storing additional information about an object in a structured format.', null=True)),
                ('description', djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.',
                                                                null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StripeSource',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(verbose_name='created',
                                                                default=django.utils.timezone.now, editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(verbose_name='modified',
                                                                      default=django.utils.timezone.now,
                                                                      editable=False)),
                ('stripe_id', djstripe.fields.StripeIdField(max_length=50, unique=True)),
                ('livemode', djstripe.fields.StripeNullBooleanField(
                    help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. \
                    Otherwise, this field indicates whether this record comes from Stripe test mode or live mode \
                    operation.', default=False)),
                ('stripe_timestamp', djstripe.fields.StripeDateTimeField(
                    help_text='The datetime this object was created in stripe.', null=True)),
                ('metadata', djstripe.fields.StripeJSONField(
                    blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful\
                     for storing additional information about an object in a structured format.', null=True)),
                ('description', djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.',
                                                                null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Card',
            fields=[
                ('stripesource_ptr', models.OneToOneField(serialize=False, parent_link=True, primary_key=True, on_delete=django.db.models.deletion.CASCADE,
                                                          to='djstripe.StripeSource', auto_created=True)),
                ('address_city', djstripe.fields.StripeTextField(help_text='Billing address city.', null=True)),
                ('address_country', djstripe.fields.StripeTextField(help_text='Billing address country.', null=True)),
                ('address_line1', djstripe.fields.StripeTextField(help_text='Billing address (Line 1).', null=True)),
                ('address_line1_check', djstripe.fields.StripeCharField(
                    choices=[('pass', 'Pass'), ('fail', 'Fail'), ('unavailable', 'Unavailable'),
                             ('unknown', 'Unknown')],
                    max_length=11, help_text='If ``address_line1`` was provided, results of the check.', null=True)),
                ('address_line2', djstripe.fields.StripeTextField(help_text='Billing address (Line 2).', null=True)),
                ('address_state', djstripe.fields.StripeTextField(help_text='Billing address state.', null=True)),
                ('address_zip', djstripe.fields.StripeTextField(help_text='Billing address zip code.', null=True)),
                ('address_zip_check', djstripe.fields.StripeCharField(
                    choices=[('pass', 'Pass'), ('fail', 'Fail'), ('unavailable', 'Unavailable'),
                             ('unknown', 'Unknown')],
                    max_length=11, help_text='If ``address_zip`` was provided, results of the check.', null=True)),
                ('brand', djstripe.fields.StripeCharField(
                    choices=[('Visa', 'Visa'), ('American Express', 'American Express'), ('MasterCard', 'MasterCard'),
                             ('Discover', 'Discover'), ('JCB', 'JCB'), ('Diners Club', 'Diners Club'),
                             ('Unknown', 'Unknown')],
                    max_length=16, help_text='Card brand.')),
                ('country', djstripe.fields.StripeCharField(
                    max_length=2, help_text='Two-letter ISO code representing the country of the card.')),
                ('cvc_check', djstripe.fields.StripeCharField(
                    choices=[('pass', 'Pass'), ('fail', 'Fail'), ('unavailable', 'Unavailable'),
                             ('unknown', 'Unknown')],
                    max_length=11, help_text='If a CVC was provided, results of the check.', null=True)),
                ('dynamic_last4', djstripe.fields.StripeCharField(
                    max_length=4,
                    help_text='(For tokenized numbers only.) The last four digits of the device account number.',
                    null=True)),
                ('exp_month', djstripe.fields.StripeIntegerField(help_text='Card expiration month.')),
                ('exp_year', djstripe.fields.StripeIntegerField(help_text='Card expiration year.')),
                ('fingerprint', djstripe.fields.StripeTextField(
                    help_text='Uniquely identifies this particular card number.', null=True)),
                ('funding', djstripe.fields.StripeCharField(
                    choices=[('credit', 'Credit'), ('debit', 'Debit'), ('prepaid', 'Prepaid'), ('unknown', 'Unknown')],
                    max_length=7, help_text='Card funding type.')),
                ('last4', djstripe.fields.StripeCharField(max_length=4, help_text='Last four digits of Card number.')),
                ('name', djstripe.fields.StripeTextField(help_text='Cardholder name.', null=True)),
                ('tokenization_method', djstripe.fields.StripeCharField(
                    choices=[('apple_pay', 'Apple Pay'), ('android_pay', 'Android Pay')], max_length=11,
                    help_text='If the card number is tokenized, this is the method that was used.', null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('djstripe.stripesource',),
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
            name='account',
            field=models.ForeignKey(
                related_name='charges', on_delete=django.db.models.deletion.CASCADE, null=True, to='djstripe.Account',
                help_text='The account the charge was made on behalf of. Null here indicates that this value was \
                never set.'),
        ),
        migrations.AddField(
            model_name='charge',
            name='source',
            field=models.ForeignKey(related_name='charges', on_delete=django.db.models.deletion.CASCADE, null=True, to='djstripe.StripeSource'),
        ),
        migrations.AddField(
            model_name='charge',
            name='currency',
            field=djstripe.fields.StripeCharField(help_text='Three-letter ISO currency code representing the currency \
            in which the charge was made.', max_length=3, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='charge',
            name='failure_code',
            field=djstripe.fields.StripeCharField(
                choices=[('invalid_number', 'Invalid Number'), ('invalid_expiry_month', 'Invalid Expiry Month'),
                         ('invalid_expiry_year', 'Invalid Expiry Year'), ('invalid_cvc', 'Invalid Cvc'),
                         ('incorrect_number', 'Incorrect Number'), ('expired_card', 'Expired Card'),
                         ('incorrect_cvc', 'Incorrect Cvc'), ('incorrect_zip', 'Incorrect Zip'),
                         ('card_declined', 'Card Declined'), ('missing', 'Missing'),
                         ('processing_error', 'Processing Error'), ('rate_limit', 'Rate Limit')],
                max_length=30, help_text='Error code explaining reason for charge failure if available.', null=True),
        ),
        migrations.AddField(
            model_name='charge',
            name='failure_message',
            field=djstripe.fields.StripeTextField(
                help_text='Message to user further explaining reason for charge failure if available.', null=True),
        ),
        migrations.AddField(
            model_name='charge',
            name='fee_details',
            field=djstripe.fields.StripeJSONField(null=True),
        ),
        migrations.AddField(
            model_name='charge',
            name='fraudulent',
            field=djstripe.fields.StripeBooleanField(
                help_text='Whether or not this charge was marked as fraudulent.', default=False),
        ),
        migrations.AddField(
            model_name='charge',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(
                help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. \
                Otherwise, this field indicates whether this record comes from Stripe test mode or live mode \
                operation.', default=False),
        ),
        migrations.AddField(
            model_name='charge',
            name='metadata',
            field=djstripe.fields.StripeJSONField(
                blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for\
                 storing additional information about an object in a structured format.',
                null=True),
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
            field=djstripe.fields.StripeCharField(
                max_length=20, help_text='The payment source type. If the payment source is supported by dj-stripe, \
                a corresponding model is attached to this Charge via a foreign key matching this field.', null=True),
        ),
        migrations.AddField(
            model_name='charge',
            name='statement_descriptor',
            field=djstripe.fields.StripeCharField(
                max_length=22, help_text='An arbitrary string to be displayed on your customer\'s credit card \
                statement. The statement description may not include <>"\' characters, and will appear on your \
                customer\'s statement in capital letters. Non-ASCII characters are automatically stripped. While \
                most banks display this information consistently, some may display it incorrectly or not at all.',
                null=True),
        ),
        migrations.AddField(
            model_name='charge',
            name='status',
            field=djstripe.fields.StripeCharField(help_text='The status of the payment.',
                                                  choices=[('succeeded', 'Succeeded'), ('failed', 'Failed')],
                                                  max_length=10, default='unknown'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='charge',
            name='transfer',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='djstripe.Transfer',
                                    help_text='The transfer to the destination account (only applicable if the \
                                    charge was created using the destination parameter).'),
        ),
        migrations.AddField(
            model_name='customer',
            name='account_balance',
            field=djstripe.fields.StripeIntegerField(help_text="Current balance, if any, being stored on the \
            customer's account. If negative, the customer has credit to apply to the next invoice. If positive, the \
            customer has an amount owed that will be added to the next invoice. The balance does not refer to any \
            unpaid invoices; it solely takes into account amounts that have yet to be successfully applied to any \
            invoice. This balance is only taken into account for recurring charges.", null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='business_vat_id',
            field=djstripe.fields.StripeCharField(max_length=20, help_text="The customer's VAT identification number.",
                                                  null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='currency',
            field=djstripe.fields.StripeCharField(
                help_text='The currency the customer can be charged in for recurring billing purposes \
                (subscriptions, invoices, invoice items).', max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='delinquent',
            field=djstripe.fields.StripeBooleanField(
                help_text="Whether or not the latest charge for the customer's latest invoice has failed.",
                default=False),
        ),
        migrations.AddField(
            model_name='customer',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(
                help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. \
                Otherwise, this field indicates whether this record comes from Stripe test mode or live mode \
                operation.', default=False),
        ),
        migrations.AddField(
            model_name='customer',
            name='metadata',
            field=djstripe.fields.StripeJSONField(
                blank=True,
                help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing \
                additional information about an object in a structured format.', null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='shipping',
            field=djstripe.fields.StripeJSONField(help_text='Shipping information associated with the customer.',
                                                  null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.',
                                                      null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='metadata',
            field=djstripe.fields.StripeJSONField(
                blank=True,
                help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing \
                additional information about an object in a structured format.', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='received_api_version',
            field=djstripe.fields.StripeCharField(
                max_length=15,
                help_text='the API version at which the event data was rendered. Blank for old entries only, all \
                new entries will have this value', blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='request_id',
            field=djstripe.fields.StripeCharField(
                max_length=50,
                help_text="Information about the request that triggered this event, for traceability purposes. \
                If empty string then this is an old entry without that data. If Null then this is not an old entry, \
                but a Stripe 'automated' event with no associated request.", blank=True, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(
                help_text='The datetime this object was created in stripe.', null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='amount_due',
            field=djstripe.fields.StripeCurrencyField(
                help_text="Final amount due at this time for this invoice. If the invoice's total is smaller than \
                the minimum charge amount, for example, or if there is account credit that can be applied to the \
                invoice, the amount_due may be 0. If there is a positive starting_balance for the invoice \
                (the customer owes money), the amount_due will also take that into account. The charge that gets \
                generated for the invoice will be for the amount specified in amount_due.",
                max_digits=7, default=0, decimal_places=2),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='invoice',
            name='application_fee',
            field=djstripe.fields.StripeCurrencyField(
                max_digits=7,
                help_text="The fee in cents that will be applied to the invoice and transferred to the application \
                owner's Stripe account when the invoice is paid.", decimal_places=2, null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='currency',
            field=djstripe.fields.StripeCharField(help_text='Three-letter ISO currency code.',
                                                  max_length=3, default=''),
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
            field=djstripe.fields.StripeIntegerField(
                help_text='Ending customer balance after attempting to pay invoice. If the invoice has not been \
                attempted yet, this will be null.', null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='forgiven',
            field=djstripe.fields.StripeBooleanField(
                help_text='Whether or not the invoice has been forgiven. Forgiving an invoice instructs us to \
                update the subscription status as if the invoice were successfully paid. Once an invoice has been \
                forgiven, it cannot be unforgiven or reopened.', default=False),
        ),
        migrations.AddField(
            model_name='invoice',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(
                help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. \
                Otherwise, this field indicates whether this record comes from Stripe test mode or live mode \
                operation.', default=False),
        ),
        migrations.AddField(
            model_name='invoice',
            name='metadata',
            field=djstripe.fields.StripeJSONField(
                blank=True,
                help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing \
                additional information about an object in a structured format.',
                null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='next_payment_attempt',
            field=djstripe.fields.StripeDateTimeField(help_text='The time at which payment will next be attempted.',
                                                      null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='starting_balance',
            field=djstripe.fields.StripeIntegerField(
                help_text='Starting customer balance before attempting to pay invoice. If the invoice has not been \
                attempted yet, this will be the current customer balance.', default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='invoice',
            name='statement_descriptor',
            field=djstripe.fields.StripeCharField(
                max_length=22,
                help_text='An arbitrary string to be displayed on your customer\'s credit card statement. \
                The statement description may not include <>"\' characters, and will appear on your customer\'s \
                statement in capital letters. Non-ASCII characters are automatically stripped. While most banks \
                display this information consistently, some may display it incorrectly or not at all.', null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.',
                                                      null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='subscription',
            field=models.ForeignKey(
                related_name='invoices',
                on_delete=django.db.models.deletion.CASCADE,
                null=True,
                to='djstripe.Subscription',
                help_text='The subscription that this invoice was prepared for, if any.'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='subscription_proration_date',
            field=djstripe.fields.StripeDateTimeField(
                help_text='Only set for upcoming invoices that preview prorations. The time used to calculate \
                prorations.',
                null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='tax',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, help_text='The amount of tax included in the \
            total, calculated from ``tax_percent`` and the subtotal. If no ``tax_percent`` is defined, this value \
            will be null.', decimal_places=2, null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='tax_percent',
            field=djstripe.fields.StripePercentField(
                validators=[django.core.validators.MinValueValidator(1.0),
                            django.core.validators.MaxValueValidator(100.0)],
                max_digits=5,
                help_text="This percentage of the subtotal has been added to the total amount of the invoice, \
                including invoice line items and discounts. This field is inherited from the subscription's \
                ``tax_percent`` field, but can be changed before the invoice is paid. This field defaults to null.",
                decimal_places=2, null=True),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='customer',
            field=models.ForeignKey(related_name='invoiceitems', on_delete=django.db.models.deletion.CASCADE, default=1, to='djstripe.Customer',
                                    help_text='The customer associated with this invoiceitem.'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='date',
            field=djstripe.fields.StripeDateTimeField(help_text='The date on the invoiceitem.',
                                                      default=datetime.datetime(2100, 1, 1, 0, 0,
                                                                                tzinfo=django.utils.timezone.utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='discountable',
            field=djstripe.fields.StripeBooleanField(help_text='If True, discounts will apply to this invoice item. \
            Always False for prorations.', default=False),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(
                help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. \
                Otherwise, this field indicates whether this record comes from Stripe test mode or live mode \
                operation.', default=False),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='metadata',
            field=djstripe.fields.StripeJSONField(
                blank=True,
                help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing \
                additional information about an object in a structured format.', null=True),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.',
                                                      null=True),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='subscription',
            field=models.ForeignKey(
                related_name='invoiceitems',
                on_delete=django.db.models.deletion.CASCADE,
                null=True,
                to='djstripe.Subscription',
                help_text='The subscription that this invoice item has been created for, if any.'),
        ),
        migrations.AddField(
            model_name='plan',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True),
        ),
        migrations.AddField(
            model_name='plan',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(
                help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. \
                Otherwise, this field indicates whether this record comes from Stripe test mode or live mode \
                operation.', default=False),
        ),
        migrations.AddField(
            model_name='plan',
            name='metadata',
            field=djstripe.fields.StripeJSONField(
                blank=True,
                help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing \
                additional information about an object in a structured format.', null=True),
        ),
        migrations.AddField(
            model_name='plan',
            name='statement_descriptor',
            field=djstripe.fields.StripeCharField(
                max_length=22,
                help_text='An arbitrary string to be displayed on your customer\'s credit card statement. The \
                statement description may not include <>"\' characters, and will appear on your customer\'s statement \
                in capital letters. Non-ASCII characters are automatically stripped. While most banks display this \
                information consistently, some may display it incorrectly or not at all.', null=True),
        ),
        migrations.AddField(
            model_name='plan',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.',
                                                      null=True),
        ),
        migrations.AlterModelOptions(
            name='plan',
            options={'ordering': ['amount']},
        ),
        migrations.AddField(
            model_name='subscription',
            name='application_fee_percent',
            field=djstripe.fields.StripePercentField(
                validators=[django.core.validators.MinValueValidator(1.0),
                            django.core.validators.MaxValueValidator(100.0)],
                help_text='A positive decimal that represents the fee percentage of the subscription invoice amount \
                that will be transferred to the application owner’s Stripe account each billing period.',
                max_digits=5, decimal_places=2, null=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(
                help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. \
                Otherwise, this field indicates whether this record comes from Stripe test mode or live mode \
                operation.', default=False),
        ),
        migrations.AddField(
            model_name='subscription',
            name='metadata',
            field=djstripe.fields.StripeJSONField(
                blank=True,
                help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing \
                additional information about an object in a structured format.', null=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=50, default='unknown', unique=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='subscription',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.',
                                                      null=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='tax_percent',
            field=djstripe.fields.StripePercentField(
                validators=[django.core.validators.MinValueValidator(1.0),
                            django.core.validators.MaxValueValidator(100.0)],
                max_digits=5,
                help_text='A positive decimal (with at most two decimal places) between 1 and 100. This represents \
                the percentage of the subscription invoice subtotal that will be calculated and added as tax to the \
                final amount each billing period.', decimal_places=2, null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='amount_reversed',
            field=djstripe.fields.StripeCurrencyField(
                max_digits=7,
                help_text='The amount reversed (can be less than the amount attribute on the transfer if a partial \
                reversal was issued).', decimal_places=2, null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='currency',
            field=djstripe.fields.StripeCharField(help_text='Three-letter ISO currency code.',
                                                  max_length=3, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transfer',
            name='destination',
            field=djstripe.fields.StripeIdField(
                help_text='ID of the bank account, card, or Stripe account the transfer was sent to.',
                max_length=50, default='unknown'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transfer',
            name='destination_payment',
            field=djstripe.fields.StripeIdField(
                max_length=50,
                help_text='If the destination is a Stripe account, this will be the ID of the payment that the \
                destination account received for the transfer.', null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='destination_type',
            field=djstripe.fields.StripeCharField(
                help_text='The type of the transfer destination.',
                choices=[('card', 'Card'), ('bank_account', 'Bank Account'), ('stripe_account', 'Stripe Account')],
                max_length=14, default='unknown'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transfer',
            name='failure_code',
            field=djstripe.fields.StripeCharField(
                choices=[('insufficient_funds', 'Insufficient Funds'), ('account_closed', 'Account Closed'),
                         ('no_account', 'No Account'), ('invalid_account_number', 'Invalid Account Number'),
                         ('debit_not_authorized', 'Debit Not Authorized'),
                         ('bank_ownership_changed', 'Bank Ownership Changed'), ('account_frozen', 'Account Frozen'),
                         ('could_not_process', 'Could Not Process'),
                         ('bank_account_restricted', 'Bank Account Restricted'),
                         ('invalid_currency', 'Invalid Currency')],
                max_length=23,
                help_text='Error code explaining reason for transfer failure if available. See \
                https://stripe.com/docs/api/python#transfer_failures.', null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='failure_message',
            field=djstripe.fields.StripeTextField(
                help_text='Message to user further explaining reason for transfer failure if available.', null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='fee',
            field=djstripe.fields.StripeCurrencyField(max_digits=7, decimal_places=2, null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='fee_details',
            field=djstripe.fields.StripeJSONField(null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(
                help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. \
                Otherwise, this field indicates whether this record comes from Stripe test mode or live mode \
                operation.', default=False),
        ),
        migrations.AddField(
            model_name='transfer',
            name='metadata',
            field=djstripe.fields.StripeJSONField(
                blank=True,
                help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing \
                additional information about an object in a structured format.', null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='reversed',
            field=djstripe.fields.StripeBooleanField(
                help_text='Whether or not the transfer has been fully reversed. If the transfer is only partially \
                reversed, this attribute will still be false.', default=False),
        ),
        migrations.AddField(
            model_name='transfer',
            name='source_transaction',
            field=djstripe.fields.StripeIdField(
                max_length=50,
                help_text='ID of the charge (or other transaction) that was used to fund the transfer. If null, the \
                transfer was funded from the available balance.', null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='source_type',
            field=djstripe.fields.StripeCharField(
                help_text='The source balance from which this transfer came.',
                choices=[('card', 'Card'), ('bank_account', 'Bank Account'), ('bitcoin_reciever', 'Bitcoin Reciever'),
                         ('alipay_account', 'Alipay Account')], max_length=16, default='unknown'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transfer',
            name='statement_descriptor',
            field=djstripe.fields.StripeCharField(
                max_length=22,
                help_text='An arbitrary string to be displayed on your customer\'s credit card statement. The \
                statement description may not include <>"\' characters, and will appear on your customer\'s statement \
                in capital letters. Non-ASCII characters are automatically stripped. While most banks display this \
                information consistently, some may display it incorrectly or not at all.', null=True),
        ),
        migrations.AddField(
            model_name='transfer',
            name='stripe_timestamp',
            field=djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.',
                                                      null=True),
        ),
        migrations.AddField(
            model_name='stripesource',
            name='customer',
            field=models.ForeignKey(related_name='sources', on_delete=django.db.models.deletion.CASCADE, to='djstripe.Customer'),
        ),
        migrations.AddField(
            model_name='stripesource',
            name='polymorphic_ctype',
            field=models.ForeignKey(related_name='polymorphic_djstripe.stripesource_set+', on_delete=django.db.models.deletion.CASCADE,
                                    to='contenttypes.ContentType', editable=False, null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='default_source',
            field=models.ForeignKey(related_name='customers', on_delete=django.db.models.deletion.CASCADE, null=True, to='djstripe.StripeSource'),
        ),
        migrations.DeleteModel(
            name='TransferChargeFee',
        ),
    ]
