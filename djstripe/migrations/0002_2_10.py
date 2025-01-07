# Generated by Django 5.1.4 on 2025-01-07 15:50

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("djstripe", "0001_initial"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="djstripeupcominginvoicetotaltaxamount", unique_together=None
        ),
        migrations.RemoveField(
            model_name="djstripeupcominginvoicetotaltaxamount", name="invoice"
        ),
        migrations.RemoveField(
            model_name="djstripeupcominginvoicetotaltaxamount", name="tax_rate"
        ),
        migrations.AlterModelOptions(
            name="price", options={"get_latest_by": "created"}
        ),
        migrations.RemoveField(model_name="account", name="description"),
        migrations.RemoveField(model_name="activeentitlement", name="description"),
        migrations.RemoveField(model_name="applicationfee", name="description"),
        migrations.RemoveField(model_name="balancetransaction", name="description"),
        migrations.RemoveField(model_name="bankaccount", name="description"),
        migrations.RemoveField(model_name="card", name="description"),
        migrations.RemoveField(model_name="charge", name="description"),
        migrations.RemoveField(model_name="coupon", name="description"),
        migrations.RemoveField(model_name="customer", name="address"),
        migrations.RemoveField(model_name="customer", name="balance"),
        migrations.RemoveField(model_name="customer", name="coupon_end"),
        migrations.RemoveField(model_name="customer", name="coupon_start"),
        migrations.RemoveField(model_name="customer", name="delinquent"),
        migrations.RemoveField(model_name="customer", name="description"),
        migrations.RemoveField(model_name="customer", name="discount"),
        migrations.RemoveField(model_name="customer", name="invoice_prefix"),
        migrations.RemoveField(model_name="customer", name="invoice_settings"),
        migrations.RemoveField(model_name="customer", name="phone"),
        migrations.RemoveField(model_name="customer", name="preferred_locales"),
        migrations.RemoveField(model_name="customer", name="shipping"),
        migrations.RemoveField(model_name="customer", name="tax_exempt"),
        migrations.RemoveField(model_name="discount", name="description"),
        migrations.RemoveField(model_name="discount", name="invoice_item"),
        migrations.RemoveField(model_name="dispute", name="amount"),
        migrations.RemoveField(model_name="dispute", name="balance_transactions"),
        migrations.RemoveField(model_name="dispute", name="currency"),
        migrations.RemoveField(model_name="dispute", name="description"),
        migrations.RemoveField(model_name="dispute", name="evidence"),
        migrations.RemoveField(model_name="dispute", name="evidence_details"),
        migrations.RemoveField(model_name="dispute", name="is_charge_refundable"),
        migrations.RemoveField(model_name="dispute", name="reason"),
        migrations.RemoveField(model_name="dispute", name="status"),
        migrations.RemoveField(model_name="earlyfraudwarning", name="description"),
        migrations.RemoveField(model_name="event", name="description"),
        migrations.RemoveField(model_name="feature", name="description"),
        migrations.RemoveField(model_name="file", name="description"),
        migrations.RemoveField(model_name="file", name="filename"),
        migrations.RemoveField(model_name="file", name="purpose"),
        migrations.RemoveField(model_name="file", name="size"),
        migrations.RemoveField(model_name="file", name="type"),
        migrations.RemoveField(model_name="file", name="url"),
        migrations.RemoveField(model_name="filelink", name="description"),
        migrations.RemoveField(model_name="filelink", name="expires_at"),
        migrations.RemoveField(model_name="filelink", name="url"),
        migrations.RemoveField(model_name="invoice", name="account_country"),
        migrations.RemoveField(model_name="invoice", name="account_name"),
        migrations.RemoveField(model_name="invoice", name="amount_due"),
        migrations.RemoveField(model_name="invoice", name="amount_paid"),
        migrations.RemoveField(model_name="invoice", name="amount_remaining"),
        migrations.RemoveField(model_name="invoice", name="application_fee_amount"),
        migrations.RemoveField(model_name="invoice", name="attempt_count"),
        migrations.RemoveField(model_name="invoice", name="attempted"),
        migrations.RemoveField(model_name="invoice", name="auto_advance"),
        migrations.RemoveField(model_name="invoice", name="billing_reason"),
        migrations.RemoveField(model_name="invoice", name="collection_method"),
        migrations.RemoveField(model_name="invoice", name="customer_address"),
        migrations.RemoveField(model_name="invoice", name="customer_email"),
        migrations.RemoveField(model_name="invoice", name="customer_name"),
        migrations.RemoveField(model_name="invoice", name="customer_phone"),
        migrations.RemoveField(model_name="invoice", name="customer_shipping"),
        migrations.RemoveField(model_name="invoice", name="customer_tax_exempt"),
        migrations.RemoveField(model_name="invoice", name="default_source"),
        migrations.RemoveField(model_name="invoice", name="description"),
        migrations.RemoveField(model_name="invoice", name="discount"),
        migrations.RemoveField(model_name="invoice", name="discounts"),
        migrations.RemoveField(model_name="invoice", name="ending_balance"),
        migrations.RemoveField(model_name="invoice", name="footer"),
        migrations.RemoveField(model_name="invoice", name="hosted_invoice_url"),
        migrations.RemoveField(model_name="invoice", name="invoice_pdf"),
        migrations.RemoveField(model_name="invoice", name="next_payment_attempt"),
        migrations.RemoveField(model_name="invoice", name="paid"),
        migrations.RemoveField(model_name="invoice", name="period_end"),
        migrations.RemoveField(model_name="invoice", name="period_start"),
        migrations.RemoveField(
            model_name="invoice", name="post_payment_credit_notes_amount"
        ),
        migrations.RemoveField(
            model_name="invoice", name="pre_payment_credit_notes_amount"
        ),
        migrations.RemoveField(model_name="invoice", name="starting_balance"),
        migrations.RemoveField(model_name="invoice", name="statement_descriptor"),
        migrations.RemoveField(model_name="invoice", name="status_transitions"),
        migrations.RemoveField(
            model_name="invoice", name="subscription_proration_date"
        ),
        migrations.RemoveField(model_name="invoice", name="threshold_reason"),
        migrations.RemoveField(model_name="invoice", name="webhooks_delivered_at"),
        migrations.RemoveField(model_name="invoiceitem", name="description"),
        migrations.RemoveField(model_name="issuingauthorization", name="description"),
        migrations.RemoveField(model_name="issuingcard", name="description"),
        migrations.RemoveField(model_name="issuingcardholder", name="description"),
        migrations.RemoveField(model_name="issuingdispute", name="description"),
        migrations.RemoveField(model_name="issuingtransaction", name="description"),
        migrations.RemoveField(model_name="lineitem", name="description"),
        migrations.RemoveField(model_name="mandate", name="description"),
        migrations.RemoveField(model_name="paymentintent", name="amount"),
        migrations.RemoveField(model_name="paymentintent", name="amount_capturable"),
        migrations.RemoveField(model_name="paymentintent", name="amount_received"),
        migrations.RemoveField(model_name="paymentintent", name="canceled_at"),
        migrations.RemoveField(model_name="paymentintent", name="cancellation_reason"),
        migrations.RemoveField(model_name="paymentintent", name="capture_method"),
        migrations.RemoveField(model_name="paymentintent", name="client_secret"),
        migrations.RemoveField(model_name="paymentintent", name="confirmation_method"),
        migrations.RemoveField(model_name="paymentintent", name="currency"),
        migrations.RemoveField(model_name="paymentintent", name="description"),
        migrations.RemoveField(model_name="paymentintent", name="last_payment_error"),
        migrations.RemoveField(model_name="paymentintent", name="next_action"),
        migrations.RemoveField(model_name="paymentintent", name="payment_method_types"),
        migrations.RemoveField(model_name="paymentintent", name="receipt_email"),
        migrations.RemoveField(model_name="paymentintent", name="setup_future_usage"),
        migrations.RemoveField(model_name="paymentintent", name="shipping"),
        migrations.RemoveField(model_name="paymentintent", name="statement_descriptor"),
        migrations.RemoveField(model_name="paymentintent", name="status"),
        migrations.RemoveField(model_name="paymentintent", name="transfer_data"),
        migrations.RemoveField(model_name="paymentintent", name="transfer_group"),
        migrations.RemoveField(model_name="paymentmethod", name="acss_debit"),
        migrations.RemoveField(model_name="paymentmethod", name="affirm"),
        migrations.RemoveField(model_name="paymentmethod", name="afterpay_clearpay"),
        migrations.RemoveField(model_name="paymentmethod", name="alipay"),
        migrations.RemoveField(model_name="paymentmethod", name="au_becs_debit"),
        migrations.RemoveField(model_name="paymentmethod", name="bacs_debit"),
        migrations.RemoveField(model_name="paymentmethod", name="bancontact"),
        migrations.RemoveField(model_name="paymentmethod", name="billing_details"),
        migrations.RemoveField(model_name="paymentmethod", name="blik"),
        migrations.RemoveField(model_name="paymentmethod", name="boleto"),
        migrations.RemoveField(model_name="paymentmethod", name="card"),
        migrations.RemoveField(model_name="paymentmethod", name="card_present"),
        migrations.RemoveField(model_name="paymentmethod", name="customer_balance"),
        migrations.RemoveField(model_name="paymentmethod", name="eps"),
        migrations.RemoveField(model_name="paymentmethod", name="fpx"),
        migrations.RemoveField(model_name="paymentmethod", name="giropay"),
        migrations.RemoveField(model_name="paymentmethod", name="grabpay"),
        migrations.RemoveField(model_name="paymentmethod", name="ideal"),
        migrations.RemoveField(model_name="paymentmethod", name="interac_present"),
        migrations.RemoveField(model_name="paymentmethod", name="klarna"),
        migrations.RemoveField(model_name="paymentmethod", name="konbini"),
        migrations.RemoveField(model_name="paymentmethod", name="link"),
        migrations.RemoveField(model_name="paymentmethod", name="oxxo"),
        migrations.RemoveField(model_name="paymentmethod", name="p24"),
        migrations.RemoveField(model_name="paymentmethod", name="paynow"),
        migrations.RemoveField(model_name="paymentmethod", name="pix"),
        migrations.RemoveField(model_name="paymentmethod", name="promptpay"),
        migrations.RemoveField(model_name="paymentmethod", name="sepa_debit"),
        migrations.RemoveField(model_name="paymentmethod", name="sofort"),
        migrations.RemoveField(model_name="paymentmethod", name="us_bank_account"),
        migrations.RemoveField(model_name="paymentmethod", name="wechat_pay"),
        migrations.RemoveField(model_name="payout", name="amount"),
        migrations.RemoveField(model_name="payout", name="arrival_date"),
        migrations.RemoveField(model_name="payout", name="automatic"),
        migrations.RemoveField(model_name="payout", name="description"),
        migrations.RemoveField(model_name="payout", name="failure_code"),
        migrations.RemoveField(model_name="payout", name="failure_message"),
        migrations.RemoveField(model_name="payout", name="method"),
        migrations.RemoveField(model_name="payout", name="source_type"),
        migrations.RemoveField(model_name="payout", name="statement_descriptor"),
        migrations.RemoveField(model_name="payout", name="status"),
        migrations.RemoveField(model_name="payout", name="type"),
        migrations.RemoveField(model_name="plan", name="description"),
        migrations.RemoveField(model_name="price", name="billing_scheme"),
        migrations.RemoveField(model_name="price", name="description"),
        migrations.RemoveField(model_name="price", name="recurring"),
        migrations.RemoveField(model_name="price", name="tiers"),
        migrations.RemoveField(model_name="price", name="tiers_mode"),
        migrations.RemoveField(model_name="price", name="transform_quantity"),
        migrations.RemoveField(model_name="price", name="type"),
        migrations.RemoveField(model_name="price", name="unit_amount"),
        migrations.RemoveField(model_name="price", name="unit_amount_decimal"),
        migrations.RemoveField(model_name="product", name="attributes"),
        migrations.RemoveField(model_name="product", name="caption"),
        migrations.RemoveField(model_name="product", name="deactivate_on"),
        migrations.RemoveField(model_name="product", name="default_price"),
        migrations.RemoveField(model_name="product", name="description"),
        migrations.RemoveField(model_name="product", name="images"),
        migrations.RemoveField(model_name="product", name="package_dimensions"),
        migrations.RemoveField(model_name="product", name="shippable"),
        migrations.RemoveField(model_name="product", name="statement_descriptor"),
        migrations.RemoveField(model_name="product", name="type"),
        migrations.RemoveField(model_name="promotioncode", name="description"),
        migrations.RemoveField(model_name="refund", name="description"),
        migrations.RemoveField(model_name="refund", name="failure_reason"),
        migrations.RemoveField(model_name="refund", name="reason"),
        migrations.RemoveField(model_name="refund", name="receipt_number"),
        migrations.RemoveField(model_name="refund", name="status"),
        migrations.RemoveField(model_name="review", name="description"),
        migrations.RemoveField(model_name="scheduledqueryrun", name="description"),
        migrations.RemoveField(model_name="session", name="description"),
        migrations.RemoveField(model_name="setupintent", name="application"),
        migrations.RemoveField(model_name="setupintent", name="cancellation_reason"),
        migrations.RemoveField(model_name="setupintent", name="client_secret"),
        migrations.RemoveField(model_name="setupintent", name="description"),
        migrations.RemoveField(model_name="setupintent", name="last_setup_error"),
        migrations.RemoveField(model_name="setupintent", name="next_action"),
        migrations.RemoveField(model_name="setupintent", name="payment_method_types"),
        migrations.RemoveField(model_name="setupintent", name="status"),
        migrations.RemoveField(model_name="setupintent", name="usage"),
        migrations.RemoveField(model_name="source", name="description"),
        migrations.RemoveField(model_name="subscription", name="description"),
        migrations.RemoveField(model_name="subscriptionitem", name="description"),
        migrations.RemoveField(model_name="subscriptionschedule", name="description"),
        migrations.RemoveField(model_name="taxcode", name="description"),
        migrations.RemoveField(model_name="taxrate", name="description"),
        migrations.RemoveField(model_name="transfer", name="description"),
        migrations.RemoveField(model_name="transferreversal", name="description"),
        migrations.RemoveField(model_name="upcominginvoice", name="account_country"),
        migrations.RemoveField(model_name="upcominginvoice", name="account_name"),
        migrations.RemoveField(model_name="upcominginvoice", name="amount_due"),
        migrations.RemoveField(model_name="upcominginvoice", name="amount_paid"),
        migrations.RemoveField(model_name="upcominginvoice", name="amount_remaining"),
        migrations.RemoveField(
            model_name="upcominginvoice", name="application_fee_amount"
        ),
        migrations.RemoveField(model_name="upcominginvoice", name="attempt_count"),
        migrations.RemoveField(model_name="upcominginvoice", name="attempted"),
        migrations.RemoveField(model_name="upcominginvoice", name="auto_advance"),
        migrations.RemoveField(model_name="upcominginvoice", name="billing_reason"),
        migrations.RemoveField(model_name="upcominginvoice", name="collection_method"),
        migrations.RemoveField(model_name="upcominginvoice", name="customer_address"),
        migrations.RemoveField(model_name="upcominginvoice", name="customer_email"),
        migrations.RemoveField(model_name="upcominginvoice", name="customer_name"),
        migrations.RemoveField(model_name="upcominginvoice", name="customer_phone"),
        migrations.RemoveField(model_name="upcominginvoice", name="customer_shipping"),
        migrations.RemoveField(
            model_name="upcominginvoice", name="customer_tax_exempt"
        ),
        migrations.RemoveField(model_name="upcominginvoice", name="description"),
        migrations.RemoveField(model_name="upcominginvoice", name="discount"),
        migrations.RemoveField(model_name="upcominginvoice", name="discounts"),
        migrations.RemoveField(model_name="upcominginvoice", name="ending_balance"),
        migrations.RemoveField(model_name="upcominginvoice", name="footer"),
        migrations.RemoveField(model_name="upcominginvoice", name="hosted_invoice_url"),
        migrations.RemoveField(model_name="upcominginvoice", name="invoice_pdf"),
        migrations.RemoveField(
            model_name="upcominginvoice", name="next_payment_attempt"
        ),
        migrations.RemoveField(model_name="upcominginvoice", name="paid"),
        migrations.RemoveField(model_name="upcominginvoice", name="period_end"),
        migrations.RemoveField(model_name="upcominginvoice", name="period_start"),
        migrations.RemoveField(
            model_name="upcominginvoice", name="post_payment_credit_notes_amount"
        ),
        migrations.RemoveField(
            model_name="upcominginvoice", name="pre_payment_credit_notes_amount"
        ),
        migrations.RemoveField(model_name="upcominginvoice", name="starting_balance"),
        migrations.RemoveField(
            model_name="upcominginvoice", name="statement_descriptor"
        ),
        migrations.RemoveField(model_name="upcominginvoice", name="status_transitions"),
        migrations.RemoveField(
            model_name="upcominginvoice", name="subscription_proration_date"
        ),
        migrations.RemoveField(model_name="upcominginvoice", name="threshold_reason"),
        migrations.RemoveField(
            model_name="upcominginvoice", name="webhooks_delivered_at"
        ),
        migrations.RemoveField(model_name="verificationreport", name="description"),
        migrations.RemoveField(model_name="verificationsession", name="description"),
        migrations.RemoveField(model_name="webhookendpoint", name="description"),
        migrations.DeleteModel(name="DjstripeInvoiceTotalTaxAmount"),
        migrations.DeleteModel(name="DjstripeUpcomingInvoiceTotalTaxAmount"),
    ]
