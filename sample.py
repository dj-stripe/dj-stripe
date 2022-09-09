# import calendar
# import time

# import stripe

# from djstripe.models import UsageRecord

# gmt = time.gmtime()
# ts = calendar.timegm(gmt)

# stripe.api_key = "sk_test_51ItQ7cJSZQVUcJYgHMIKKvkqL6XNUHRI1kQcpoR9yEdOusA5rWpTXpXYnIqHpIvWlu5odQYNBDVwNSYTJN1HmtCC00RvEyLiZW"
# stripe_usage_record = stripe.SubscriptionItem.create_usage_record(
#     "si_JipZoDPT7Bw1tm", quantity=50, timestamp=ts
# )


# UsageRecord.sync_from_stripe_data(stripe_usage_record)

# import stripe

# from djstripe.models import Invoice, Price

# stripe.api_key = "sk_test_51ItQ7cJSZQVUcJYgHMIKKvkqL6XNUHRI1kQcpoR9yEdOusA5rWpTXpXYnIqHpIvWlu5odQYNBDVwNSYTJN1HmtCC00RvEyLiZW"

# invoice = stripe.Invoice.retrieve("in_1L2x08JSZQVUcJYgS4zWwSw5")
# # price = stripe.Price.retrieve("price_1J5O0hJSZQVUcJYgYpVPGEb9")
# invoice_inst = Invoice.sync_from_stripe_data(invoice)
# # price_inst = Price.sync_from_stripe_data(price)


# # 100 <class 'int'> 100 <class 'int'> 100 <class 'int'> 0 <class 'int'>
# print(
#     invoice_inst.total,
#     type(invoice_inst.total),
#     invoice_inst.amount_due,
#     type(invoice_inst.amount_due),
#     invoice_inst.amount_paid,
#     type(invoice_inst.amount_paid),
#     invoice_inst.amount_remaining,
#     type(invoice_inst.amount_remaining),
# )


# # # 500 <class 'decimal.Decimal'> 500 <class 'int'>
# # print(
# #     price_inst.unit_amount_decimal, type(price_inst.unit_amount_decimal),
# #     price_inst.unit_amount, type(price_inst.unit_amount),
# # )


# import stripe

# from djstripe.models import Order
# from djstripe.models.billing import Coupon

# stripe.api_key = "sk_test_51ItQ7cJSZQVUcJYgHMIKKvkqL6XNUHRI1kQcpoR9yEdOusA5rWpTXpXYnIqHpIvWlu5odQYNBDVwNSYTJN1HmtCC00RvEyLiZW"
# stripe.api_version = "2020-08-27; orders_beta=v4"

# coupon = Coupon.objects.first()


# # # Create Order on Platform Account (dj-stripe)
# # ord = stripe.Order.create(
# #     currency="usd",
# #     customer="cus_KZ0Gc1NBVWHzny",
# #     # automatic_tax={"enabled": True},
# #     line_items=[
# #         {
# #             "price": "price_1J5O0hJSZQVUcJYgYpVPGEb9",
# #         },
# #     ],
# #     payment={
# #         "settings": {
# #             "payment_method_types": ["card"],
# #         },
# #     },
# #     expand=["line_items"],
# # )

# # Create Order on Connected Account (DEV-CUSTOM-1)
# ord = stripe.Order.create(
#     currency="usd",
#     customer="cus_Jipya0TWp92QHK",
#     # automatic_tax={"enabled": True},
#     line_items=[
#         {
#             "product": "prod_Jiq2VaC3ZLklHA",
#             "quantity": 10,
#         },
#     ],
#     payment={
#         "settings": {
#             "payment_method_types": ["card"],
#         },
#     },
#     expand=["line_items"],
#     stripe_account="acct_1J5NiOQuFmP1Mw5u",
# )

# # Modify the Order by adding a discount
# ord = stripe.Order.modify(
#     ord.id,
#     discounts=[{"coupon": coupon.id}],
#     expand=["discounts"],
# )
# # Modify the Order by updating the metadata on the Connected Account
# ord = stripe.Order.modify(
#     ord.id,
#     metadata={"updated": 5},
#     stripe_account="acct_1J5NiOQuFmP1Mw5u",
# )

# # # Submit the order
# # ord = stripe.Order.submit(
# #     ord.id,
# #     expected_total=375,
# #     expand=["payment.payment_intent"],
# # )
# ord = ord.submit(
#     expected_total=375,
#     expand=["payment.payment_intent"],
# )

# # # Submit the order on the Connected Account
# # ord = stripe.Order.submit(
# #     ord.id,
# #     expected_total=10000,
# #     stripe_account="acct_1J5NiOQuFmP1Mw5u",
# #     expand=["payment.payment_intent"],
# # )

# ord = ord.submit(
#     expected_total=10000,
#     stripe_account="acct_1J5NiOQuFmP1Mw5u",
#     expand=["payment.payment_intent"],
# )


# # # Reopen the order
# # ord = stripe.Order.reopen(ord.id)
# ord = ord.reopen()

# # # Reopen the order on the Connected Account
# # ord = stripe.Order.reopen(
# #     ord.id,
# #     stripe_account="acct_1J5NiOQuFmP1Mw5u",
# # )
# ord = ord.reopen(stripe_account="acct_1J5NiOQuFmP1Mw5u")


# # # Add a PM to the created Payment Intent
# pi_confirm = stripe.PaymentIntent.confirm(
#     ord["payment"]["payment_intent"],
#     payment_method="card_1K2GRRJSZQVUcJYg5OZSvD3a",
# )
# # # Add a PM to the created Payment Intent on the connected account
# pi_confirm = stripe.PaymentIntent.confirm(
#     ord["payment"]["payment_intent"],
#     payment_method="src_1J5OKGQuFmP1Mw5uomdktMCq",
#     # stripe_account="acct_1J5NiOQuFmP1Mw5u",
# )


# # # Cancel the order
# # stripe.Order.cancel(ord.id)


# ord = ord.cancel()


# # # Cancel the orderon the Connected Account
# # stripe.Order.cancel(
# #     ord.id,
# #     stripe_account="acct_1J5NiOQuFmP1Mw5u",
# # )

# ord = ord.cancel(stripe_account="acct_1J5NiOQuFmP1Mw5u")


import stripe

from djstripe.models import Invoice, Price

stripe.api_key = "sk_test_51ItQ7cJSZQVUcJYgHMIKKvkqL6XNUHRI1kQcpoR9yEdOusA5rWpTXpXYnIqHpIvWlu5odQYNBDVwNSYTJN1HmtCC00RvEyLiZW"

pr = stripe.Price.create(
    billing_scheme="tiered",
    currency="usd",
    recurring={"interval": "month"},
    product="prod_MSFGDn5MFetWhR",
    tiers_mode="graduated",
    tiers=[
        {"flat_amount": 500, "up_to": 1},
        {"flat_amount": 500, "up_to": "inf"},
    ],
)
