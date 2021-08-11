import calendar
import time

import stripe

from djstripe.models import UsageRecord

gmt = time.gmtime()
ts = calendar.timegm(gmt)

stripe.api_key = "sk_test_51ItQ7cJSZQVUcJYgHMIKKvkqL6XNUHRI1kQcpoR9yEdOusA5rWpTXpXYnIqHpIvWlu5odQYNBDVwNSYTJN1HmtCC00RvEyLiZW"
stripe_usage_record = stripe.SubscriptionItem.create_usage_record(
    "si_JipZoDPT7Bw1tm", quantity=50, timestamp=ts
)


UsageRecord.sync_from_stripe_data(stripe_usage_record)
