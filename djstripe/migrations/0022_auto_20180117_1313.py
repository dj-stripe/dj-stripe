# Generated by Django 2.0.1 on 2018-01-17 12:13

from django.db import migrations, models
import django.db.models.deletion
import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0021_auto_20180115_1946'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='business_logo',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='djstripe.FileUpload'),
        ),
        migrations.AddField(
            model_name='account',
            name='business_name',
            field=djstripe.fields.StripeCharField(default='', help_text='The publicly visible name of the business', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='business_primary_color',
            field=djstripe.fields.StripeCharField(help_text='A CSS hex color value representing the primary branding color for this account', max_length=7, null=True),
        ),
        migrations.AddField(
            model_name='account',
            name='business_url',
            field=djstripe.fields.StripeCharField(help_text='The publicly visible website of the business', max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='account',
            name='charges_enabled',
            field=djstripe.fields.StripeBooleanField(default=False, help_text='Whether the account can create live charges'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='country',
            field=djstripe.fields.StripeCharField(default='', help_text='The country of the account', max_length=2),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='debit_negative_balances',
            field=djstripe.fields.StripeBooleanField(default=False, null=True, help_text='A Boolean indicating if Stripe should try to reclaim negative balances from an attached bank account.'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='decline_charge_on',
            field=djstripe.fields.StripeJSONField(help_text='Account-level settings to automatically decline certain types of charges regardless of the decision of the card issuer', null=True),
        ),
        migrations.AddField(
            model_name='account',
            name='default_currency',
            field=djstripe.fields.StripeCharField(default='usd', help_text='The currency this account has chosen to use as the default', max_length=3),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='details_submitted',
            field=djstripe.fields.StripeBooleanField(default=False, help_text='Whether account details have been submitted. Standard accounts cannot receive payouts before this is true.'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='display_name',
            field=djstripe.fields.StripeCharField(default='', help_text='The display name for this account. This is used on the Stripe Dashboard to differentiate between accounts.', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='email',
            field=djstripe.fields.StripeCharField(default='', help_text='The primary user’s email address.', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='legal_entity',
            field=djstripe.fields.StripeJSONField(default={}, help_text='Information about the legal entity itself, including about the associated account representative'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='payout_schedule',
            field=djstripe.fields.StripeJSONField(null=True, help_text='Details on when funds from charges are available, and when they are paid out to an external account.'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='payout_statement_descriptor',
            field=djstripe.fields.StripeCharField(default='', help_text='The text that appears on the bank account statement for payouts.', max_length=255),
        ),
        migrations.AddField(
            model_name='account',
            name='payouts_enabled',
            field=djstripe.fields.StripeBooleanField(default=False, help_text='Whether Stripe can send payouts to this account'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='product_description',
            field=djstripe.fields.StripeCharField(help_text='Internal-only description of the product sold or service provided by the business. It’s used by Stripe for risk and underwriting purposes.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='account',
            name='statement_descriptor',
            field=djstripe.fields.StripeCharField(default='', help_text='The default text that appears on credit card statements when a charge is made directly on the account', max_length=255),
        ),
        migrations.AddField(
            model_name='account',
            name='support_email',
            field=djstripe.fields.StripeCharField(default='', help_text='A publicly shareable support email address for the business', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='support_phone',
            field=djstripe.fields.StripeCharField(default='', help_text='A publicly shareable support phone number for the business', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='support_url',
            field=djstripe.fields.StripeCharField(default='', help_text='A publicly shareable URL that provides support for this account', max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='timezone',
            field=djstripe.fields.StripeCharField(default='Etc/UTC', help_text='The timezone used in the Stripe Dashboard for this account.', max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='tos_acceptance',
            field=djstripe.fields.StripeJSONField(help_text='Details on the acceptance of the Stripe Services Agreement', null=True),
        ),
        migrations.AddField(
            model_name='account',
            name='type',
            field=djstripe.fields.StripeCharField(choices=[('custom', 'Custom'), ('express', 'Express'), ('standard', 'Standard')], default='standard', help_text='The Stripe account type.', max_length=8),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='verification',
            field=djstripe.fields.StripeJSONField(help_text='Information on the verification state of the account, including what information is needed and by when', null=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='request_id',
            field=djstripe.fields.StripeCharField(blank=True, help_text="Information about the request that triggered this event, for traceability purposes. If empty string then this is an old entry without that data. If Null then this is not an old entry, but a Stripe 'automated' event with no associated request.", max_length=50, null=True),
        ),
    ]
