# Create a Stripe Usage Record

Usage records allow you to report customer usage and metrics to Stripe for metered billing of subscription prices

Usage records created using Djstripe's [`UsageRecord.create()`][djstripe.models.billing.UsageRecord.create] method will both create and sync the created `UsageRecord` object with your db.


**Note:**
 UsageRecord objects created directly will not sync because Stripe does not expose a way to retrieve UsageRecord objects directly. They can thus only be synced at creation time.

## Code:

```python
from djstripe.models import UsageRecord

# create and sync UsageRecord object
UsageRecord.create(id=<SUBSCRIPTION_ITEM_ID>, quantity=<SUBSCRIPTION_ITEM_QUANTITY>, timestamp=timestamp)

```
