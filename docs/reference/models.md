# Models

Models hold the bulk of the functionality included in the dj-stripe
package. Each model is tied closely to its corresponding object in the
stripe dashboard. Fields that are not implemented for each model have a
short reason behind the decision in the docstring for each model.

## Core Resources

::: djstripe.models.core


## Payment Methods

<!-- DO NOT INCLUDE LegacySourceMixin AND DjstripePaymentMethod -->
::: djstripe.models.payment_methods
    selection:
        filters: ["!LegacySourceMixin$", "!DjstripePaymentMethod$"]



## Billing

<!-- DO NOT INCLUDE DjstripeInvoiceTotalTaxAmount, DjstripeUpcomingInvoiceTotalTaxAmount AND DJBaseInvoiceSTRIPEPAYMENTMETHOD -->
::: djstripe.models.billing
    selection:
        filters: ["!DjstripeInvoiceTotalTaxAmount$", "!DjstripeUpcomingInvoiceTotalTaxAmount$",
        "!BaseInvoice$"]


## Connect

::: djstripe.models.account

::: djstripe.models.connect


## Fraud

::: djstripe.models.fraud

## Orders

::: djstripe.models.orders

## Sigma

::: djstripe.models.sigma


## Webhooks

::: djstripe.models.webhooks
