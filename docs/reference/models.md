# Models

Models hold the bulk of the functionality included in the dj-stripe
package. Each model is tied closely to its corresponding object in the
stripe dashboard. Fields that are not implemented for each model have a
short reason behind the decision in the docstring for each model.

## Core Resources

### Balance Transaction

::: djstripe.models.BalanceTransaction
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data

### Charge

djstripe.models.Charge
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url disputed refund capture sync_from_stripe_data

### Customer

::: djstripe.models.Customer
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url get_or_create legacy_cards credits customer_payment_methods pending_charges subscribe charge add_invoice_item add_card add_payment_method purge has_any_active_subscription active_subscriptions valid_subscriptions subscription can_charge send_invoice retry_unpaid_invoices has_valid_source add_coupon upcoming_invoice sync_from_stripe_data

### Dispute

::: djstripe.models.Dispute
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data


### Event

::: djstripe.models.Event
    :docstring:
    :members: api_list api_retrieve process invoke_webhook_handlers parts category verb customer get_stripe_dashboard_url sync_from_stripe_data

### File Upload

::: djstripe.models.FileUpload
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data

### Payout


::: djstripe.models.Payout
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data

### PaymentIntent

::: djstripe.models.PaymentIntent
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data

### Price

::: djstripe.models.Price
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url get_or_create human_readable_price sync_from_stripe_data

### Product

::: djstripe.models.Product
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data

### Refund


::: djstripe.models.Refund
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data

## Payment Methods

### BankAccount

::: djstripe.models.BankAccount
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data

### Card


::: djstripe.models.Card
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url remove create_token sync_from_stripe_data

### PaymentMethod

::: djstripe.models.PaymentMethod
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url attach detach sync_from_stripe_data


### Source

::: djstripe.models.Source
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url detach sync_from_stripe_data

## Billing

### Coupon


::: djstripe.models.Coupon
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url human_readable_amount human_readable sync_from_stripe_data

### Invoice

::: djstripe.models.Invoice
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url upcoming retry plan sync_from_stripe_data

### InvoiceItem


::: djstripe.models.InvoiceItem
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data

### Plan

::: djstripe.models.Plan
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url get_or_create amount_in_cents human_readable_price sync_from_stripe_data

### Subscription


::: djstripe.models.Subscription
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url update extend cancel reactivate is_period_current is_status_current is_status_temporarily_current is_valid sync_from_stripe_data

### SubscriptionItem

::: djstripe.models.SubscriptionItem
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data

### TaxRate


::: djstripe.models.TaxRate
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data


### UpcomingInvoice

::: djstripe.models.UpcomingInvoice
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url invoiceitems sync_from_stripe_data

### UsageRecord

::: djstripe.models.UsageRecord
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data

## Connect

### Account

::: djstripe.models.Account
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url get_default_account sync_from_stripe_data

### Application Fee

::: djstripe.models.ApplicationFee
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data

### Country Spec

::: djstripe.models.CountrySpec
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data

### Transfer

::: djstripe.models.Transfer
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data

### Transfer Reversal

::: djstripe.models.TransferReversal
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data

## Fraud

TODO

## Orders

TODO

## Sigma

### ScheduledQueryRun

::: djstripe.models.ScheduledQueryRun
    :docstring:
    :members: api_list api_retrieve get_stripe_dashboard_url sync_from_stripe_data

## Webhooks

### WebhookEventTrigger

::: djstripe.models.WebhookEventTrigger
    :docstring:
    :members: json_body is_test_event from_request
