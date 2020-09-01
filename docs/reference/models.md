# Models

Models hold the bulk of the functionality included in the dj-stripe
package. Each model is tied closely to its corresponding object in the
stripe dashboard. Fields that are not implemented for each model have a
short reason behind the decision in the docstring for each model.

Last Updated 2019-12-21

## Core Resources

### Balance Transaction

<div class="autoclass">

djstripe.models.BalanceTransaction

</div>

<div class="automethod">

djstripe.models.BalanceTransaction.api_list

</div>

<div class="automethod">

djstripe.models.BalanceTransaction.api_retrieve

</div>

<div class="automethod">

djstripe.models.BalanceTransaction.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.BalanceTransaction.sync_from_stripe_data

</div>

### Charge

<div class="autoclass">

djstripe.models.Charge

</div>

<div class="automethod">

djstripe.models.Charge.api_list

</div>

<div class="automethod">

djstripe.models.Charge.api_retrieve

</div>

<div class="automethod">

djstripe.models.Charge.get_stripe_dashboard_url

</div>

<div class="autoattribute">

djstripe.models.Charge.disputed

</div>

<div class="automethod">

djstripe.models.Charge.refund

</div>

<div class="automethod">

djstripe.models.Charge.capture

</div>

<div class="automethod">

djstripe.models.Charge.str_parts

</div>

<div class="automethod">

djstripe.models.Charge.sync_from_stripe_data

</div>

### Customer

<div class="autoclass">

djstripe.models.Customer

</div>

<div class="automethod">

djstripe.models.Customer.api_list

</div>

<div class="automethod">

djstripe.models.Customer.api_retrieve

</div>

<div class="automethod">

djstripe.models.Customer.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.Customer.get_or_create

</div>

<div class="autoattribute">

djstripe.models.Customer.legacy_cards

</div>

<div class="autoattribute">

djstripe.models.Customer.credits

</div>

<div class="autoattribute">

djstripe.models.Customer.customer_payment_methods

</div>

<div class="autoattribute">

djstripe.models.Customer.pending_charges

</div>

<div class="automethod">

djstripe.models.Customer.subscribe

</div>

<div class="automethod">

djstripe.models.Customer.charge

</div>

<div class="automethod">

djstripe.models.Customer.add_invoice_item

</div>

<div class="automethod">

djstripe.models.Customer.add_card

</div>

<div class="automethod">

djstripe.models.Customer.add_payment_method

</div>

<div class="automethod">

djstripe.models.Customer.purge

</div>

<div class="automethod">

djstripe.models.Customer.has_active_subscription

</div>

<div class="automethod">

djstripe.models.Customer.has_any_active_subscription

</div>

<div class="autoattribute">

djstripe.models.Customer.active_subscriptions

</div>

<div class="autoattribute">

djstripe.models.Customer.valid_subscriptions

</div>

<div class="autoattribute">

djstripe.models.Customer.subscription

</div>

<div class="automethod">

djstripe.models.Customer.can_charge

</div>

<div class="automethod">

djstripe.models.Customer.send_invoice

</div>

<div class="automethod">

djstripe.models.Customer.retry_unpaid_invoices

</div>

<div class="automethod">

djstripe.models.Customer.has_valid_source

</div>

<div class="automethod">

djstripe.models.Customer.add_coupon

</div>

<div class="automethod">

djstripe.models.Customer.upcoming_invoice

</div>

<div class="automethod">

djstripe.models.Customer.str_parts

</div>

<div class="automethod">

djstripe.models.Customer.sync_from_stripe_data

</div>

### Dispute

<div class="autoclass">

djstripe.models.Dispute

</div>

<div class="automethod">

djstripe.models.Dispute.api_list

</div>

<div class="automethod">

djstripe.models.Dispute.api_retrieve

</div>

<div class="automethod">

djstripe.models.Dispute.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.Dispute.str_parts

</div>

<div class="automethod">

djstripe.models.Dispute.sync_from_stripe_data

</div>

### Event

<div class="autoclass">

djstripe.models.Event

</div>

<div class="automethod">

djstripe.models.Event.api_list

</div>

<div class="automethod">

djstripe.models.Event.api_retrieve

</div>

<div class="automethod">

djstripe.models.Event.process

</div>

<div class="automethod">

djstripe.models.Event.invoke_webhook_handlers

</div>

<div class="autoattribute">

djstripe.models.Event.parts

</div>

<div class="autoattribute">

djstripe.models.Event.category

</div>

<div class="autoattribute">

djstripe.models.Event.verb

</div>

<div class="autoattribute">

djstripe.models.Event.customer

</div>

<div class="automethod">

djstripe.models.Event.str_parts

</div>

<div class="automethod">

djstripe.models.Event.sync_from_stripe_data

</div>

### File Upload

<div class="autoclass">

djstripe.models.FileUpload

</div>

<div class="automethod">

djstripe.models.FileUpload.api_list

</div>

<div class="automethod">

djstripe.models.FileUpload.api_retrieve

</div>

<div class="automethod">

djstripe.models.FileUpload.sync_from_stripe_data

</div>

### Payout

<div class="autoclass">

djstripe.models.Payout

</div>

<div class="automethod">

djstripe.models.Payout.api_list

</div>

<div class="automethod">

djstripe.models.Payout.api_retrieve

</div>

<div class="automethod">

djstripe.models.Payout.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.Payout.str_parts

</div>

<div class="automethod">

djstripe.models.Payout.sync_from_stripe_data

</div>

### PaymentIntent

<div class="autoclass">

djstripe.models.PaymentIntent

</div>

<div class="automethod">

djstripe.models.PaymentIntent.api_list

</div>

<div class="automethod">

djstripe.models.PaymentIntent.api_retrieve

</div>

<div class="automethod">

djstripe.models.PaymentIntent.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.PaymentIntent.str_parts

</div>

<div class="automethod">

djstripe.models.PaymentIntent.sync_from_stripe_data

</div>

### Product

<div class="autoclass">

djstripe.models.Product

</div>

<div class="automethod">

djstripe.models.Product.api_list

</div>

<div class="automethod">

djstripe.models.Product.api_retrieve

</div>

<div class="automethod">

djstripe.models.Product.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.Product.sync_from_stripe_data

</div>

### Refund

<div class="autoclass">

djstripe.models.Refund

</div>

<div class="automethod">

djstripe.models.Refund.api_list

</div>

<div class="automethod">

djstripe.models.Refund.api_retrieve

</div>

<div class="automethod">

djstripe.models.Refund.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.Refund.sync_from_stripe_data

</div>

## Payment Methods

### BankAccount

<div class="autoclass">

djstripe.models.BankAccount

</div>

<div class="automethod">

djstripe.models.BankAccount.api_list

</div>

<div class="automethod">

djstripe.models.BankAccount.api_retrieve

</div>

<div class="automethod">

djstripe.models.BankAccount.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.BankAccount.str_parts

</div>

<div class="automethod">

djstripe.models.BankAccount.sync_from_stripe_data

</div>

### Card

<div class="autoclass">

djstripe.models.Card

</div>

<div class="automethod">

djstripe.models.Card.api_list

</div>

<div class="automethod">

djstripe.models.Card.api_retrieve

</div>

<div class="automethod">

djstripe.models.Card.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.Card.remove

</div>

<div class="automethod">

djstripe.models.Card.create_token

</div>

<div class="automethod">

djstripe.models.Card.str_parts

</div>

<div class="automethod">

djstripe.models.Card.sync_from_stripe_data

</div>

### PaymentMethod

<div class="autoclass">

djstripe.models.PaymentMethod

</div>

<div class="automethod">

djstripe.models.PaymentMethod.api_list

</div>

<div class="automethod">

djstripe.models.PaymentMethod.api_retrieve

</div>

<div class="automethod">

djstripe.models.PaymentMethod.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.PaymentMethod.attach

</div>

<div class="automethod">

djstripe.models.PaymentMethod.detach

</div>

<div class="automethod">

djstripe.models.PaymentMethod.str_parts

</div>

<div class="automethod">

djstripe.models.PaymentMethod.sync_from_stripe_data

</div>

### Source

<div class="autoclass">

djstripe.models.Source

</div>

<div class="automethod">

djstripe.models.Source.api_list

</div>

<div class="automethod">

djstripe.models.Source.api_retrieve

</div>

<div class="automethod">

djstripe.models.Source.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.Source.detach

</div>

<div class="automethod">

djstripe.models.Source.str_parts

</div>

<div class="automethod">

djstripe.models.Source.sync_from_stripe_data

</div>

## Billing

### Coupon

<div class="autoclass">

djstripe.models.Coupon

</div>

<div class="automethod">

djstripe.models.Coupon.api_list

</div>

<div class="automethod">

djstripe.models.Coupon.api_retrieve

</div>

<div class="automethod">

djstripe.models.Coupon.get_stripe_dashboard_url

</div>

<div class="autoattribute">

djstripe.models.Coupon.human_readable_amount

</div>

<div class="autoattribute">

djstripe.models.Coupon.human_readable

</div>

<div class="automethod">

djstripe.models.Coupon.str_parts

</div>

<div class="automethod">

djstripe.models.Coupon.sync_from_stripe_data

</div>

### Invoice

<div class="autoclass">

djstripe.models.Invoice

</div>

<div class="automethod">

djstripe.models.Invoice.api_list

</div>

<div class="automethod">

djstripe.models.Invoice.api_retrieve

</div>

<div class="automethod">

djstripe.models.Invoice.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.Invoice.upcoming

</div>

<div class="automethod">

djstripe.models.Invoice.retry

</div>

<div class="autoattribute">

djstripe.models.Invoice.plan

</div>

<div class="automethod">

djstripe.models.Invoice.str_parts

</div>

<div class="automethod">

djstripe.models.Invoice.sync_from_stripe_data

</div>

### InvoiceItem

<div class="autoclass">

djstripe.models.InvoiceItem

</div>

<div class="automethod">

djstripe.models.InvoiceItem.api_list

</div>

<div class="automethod">

djstripe.models.InvoiceItem.api_retrieve

</div>

<div class="automethod">

djstripe.models.InvoiceItem.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.InvoiceItem.str_parts

</div>

<div class="automethod">

djstripe.models.InvoiceItem.sync_from_stripe_data

</div>

### Plan

<div class="autoclass">

djstripe.models.Plan

</div>

<div class="automethod">

djstripe.models.Plan.api_list

</div>

<div class="automethod">

djstripe.models.Plan.api_retrieve

</div>

<div class="automethod">

djstripe.models.Plan.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.Plan.get_or_create

</div>

<div class="autoattribute">

djstripe.models.Plan.amount_in_cents

</div>

<div class="autoattribute">

djstripe.models.Plan.human_readable_price

</div>

<div class="automethod">

djstripe.models.Plan.str_parts

</div>

<div class="automethod">

djstripe.models.Plan.sync_from_stripe_data

</div>

### Subscription

<div class="autoclass">

djstripe.models.Subscription

</div>

<div class="automethod">

djstripe.models.Subscription.api_list

</div>

<div class="automethod">

djstripe.models.Subscription.api_retrieve

</div>

<div class="automethod">

djstripe.models.Subscription.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.Subscription.update

</div>

<div class="automethod">

djstripe.models.Subscription.extend

</div>

<div class="automethod">

djstripe.models.Subscription.cancel

</div>

<div class="automethod">

djstripe.models.Subscription.reactivate

</div>

<div class="automethod">

djstripe.models.Subscription.is_period_current

</div>

<div class="automethod">

djstripe.models.Subscription.is_status_current

</div>

<div class="automethod">

djstripe.models.Subscription.is_status_temporarily_current

</div>

<div class="automethod">

djstripe.models.Subscription.is_valid

</div>

<div class="automethod">

djstripe.models.Subscription.str_parts

</div>

<div class="automethod">

djstripe.models.Subscription.sync_from_stripe_data

</div>

### SubscriptionItem

<div class="autoclass">

djstripe.models.SubscriptionItem

</div>

<div class="automethod">

djstripe.models.SubscriptionItem.api_list

</div>

<div class="automethod">

djstripe.models.SubscriptionItem.api_retrieve

</div>

<div class="automethod">

djstripe.models.SubscriptionItem.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.SubscriptionItem.sync_from_stripe_data

</div>

### TaxRate

<div class="autoclass">

djstripe.models.TaxRate

</div>

<div class="automethod">

djstripe.models.TaxRate.api_list

</div>

<div class="automethod">

djstripe.models.TaxRate.api_retrieve

</div>

<div class="automethod">

djstripe.models.TaxRate.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.TaxRate.sync_from_stripe_data

</div>

### UpcomingInvoice

<div class="autoclass">

djstripe.models.UpcomingInvoice

</div>

<div class="automethod">

djstripe.models.UpcomingInvoice.api_list

</div>

<div class="automethod">

djstripe.models.UpcomingInvoice.api_retrieve

</div>

<div class="automethod">

djstripe.models.UpcomingInvoice.get_stripe_dashboard_url

</div>

<div class="autoattribute">

djstripe.models.UpcomingInvoice.invoiceitems

</div>

<div class="automethod">

djstripe.models.UpcomingInvoice.str_parts

</div>

<div class="automethod">

djstripe.models.UpcomingInvoice.sync_from_stripe_data

</div>

### UsageRecord

<div class="autoclass">

djstripe.models.UsageRecord

</div>

<div class="automethod">

djstripe.models.UsageRecord.api_list

</div>

<div class="automethod">

djstripe.models.UsageRecord.api_retrieve

</div>

<div class="automethod">

djstripe.models.UsageRecord.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.UsageRecord.sync_from_stripe_data

</div>

## Connect

### Account

<div class="autoclass">

djstripe.models.Account

</div>

<div class="automethod">

djstripe.models.Account.api_list

</div>

<div class="automethod">

djstripe.models.Account.api_retrieve

</div>

<div class="automethod">

djstripe.models.Account.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.Account.get_connected_account_from_token

</div>

<div class="automethod">

djstripe.models.Account.get_default_account

</div>

<div class="automethod">

djstripe.models.Account.str_parts

</div>

<div class="automethod">

djstripe.models.Account.sync_from_stripe_data

</div>

### Application Fee

<div class="autoclass">

djstripe.models.ApplicationFee

</div>

<div class="automethod">

djstripe.models.ApplicationFee.api_list

</div>

<div class="automethod">

djstripe.models.ApplicationFee.api_retrieve

</div>

<div class="automethod">

djstripe.models.ApplicationFee.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.ApplicationFee.sync_from_stripe_data

</div>

### Country Spec

<div class="autoclass">

djstripe.models.CountrySpec

</div>

<div class="automethod">

djstripe.models.CountrySpec.api_list

</div>

<div class="automethod">

djstripe.models.CountrySpec.api_retrieve

</div>

<div class="automethod">

djstripe.models.CountrySpec.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.CountrySpec.sync_from_stripe_data

</div>

### Transfer

<div class="autoclass">

djstripe.models.Transfer

</div>

<div class="automethod">

djstripe.models.Transfer.api_list

</div>

<div class="automethod">

djstripe.models.Transfer.api_retrieve

</div>

<div class="automethod">

djstripe.models.Transfer.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.Transfer.str_parts

</div>

<div class="automethod">

djstripe.models.Transfer.sync_from_stripe_data

</div>

### Transfer Reversal

<div class="autoclass">

djstripe.models.TransferReversal

</div>

<div class="automethod">

djstripe.models.TransferReversal.api_list

</div>

<div class="automethod">

djstripe.models.TransferReversal.api_retrieve

</div>

<div class="automethod">

djstripe.models.TransferReversal.get_stripe_dashboard_url

</div>

<div class="automethod">

djstripe.models.TransferReversal.sync_from_stripe_data

</div>

## Fraud

TODO

## Orders

TODO

## Sigma

### ScheduledQueryRun

<div class="autoclass">

djstripe.models.ScheduledQueryRun

</div>

<div class="automethod">

djstripe.models.ScheduledQueryRun.api_list

</div>

<div class="automethod">

djstripe.models.ScheduledQueryRun.api_retrieve

</div>

<div class="automethod">

djstripe.models.ScheduledQueryRun.sync_from_stripe_data

</div>

## Webhooks

### WebhookEventTrigger

<div class="autoclass">

djstripe.models.WebhookEventTrigger

</div>

<div class="autoattribute">

djstripe.models.WebhookEventTrigger.json_body

</div>

<div class="autoattribute">

djstripe.models.WebhookEventTrigger.is_test_event

</div>

<div class="automethod">

djstripe.models.WebhookEventTrigger.from_request

</div>
