# -*- coding: utf-8 -*-

import warnings

from .models import StripeObject as MovedStripeObject
from .models import Account, Card, Charge, Coupon, Customer, Event, Invoice, Payout, Plan, Subscription, Transfer


warnings.warn(
    "djstripe.stripe_objects is a deprecated module, please use djstripe.models",
    DeprecationWarning
)

StripeObject = MovedStripeObject
StripeCharge = Charge
StripeCustomer = Customer
StripeEvent = Event
StripePayout = Payout
StripeCard = Card
StripeCoupon = Coupon
StripeInvoice = Invoice
StripePlan = Plan
StripeSubscription = Subscription
StripeAccount = Account
StripeTransfer = Transfer
