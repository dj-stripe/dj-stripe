Managers
========

Last Updated 2018-05-24


SubscriptionManager
-------------------
.. autoclass:: djstripe.managers.SubscriptionManager

    .. automethod:: djstripe.managers.SubscriptionManager.started_during
    .. automethod:: djstripe.managers.SubscriptionManager.active
    .. automethod:: djstripe.managers.SubscriptionManager.canceled
    .. automethod:: djstripe.managers.SubscriptionManager.canceled_during
    .. automethod:: djstripe.managers.SubscriptionManager.started_plan_summary_for
    .. automethod:: djstripe.managers.SubscriptionManager.active_plan_summary
    .. automethod:: djstripe.managers.SubscriptionManager.canceled_plan_summary_for
    .. automethod:: djstripe.managers.SubscriptionManager.churn


TransferManager
---------------
.. autoclass:: djstripe.managers.TransferManager

    .. automethod:: djstripe.managers.TransferManager.during
    .. automethod:: djstripe.managers.TransferManager.paid_totals_for


ChargeManager
---------------
.. autoclass:: djstripe.managers.ChargeManager

    .. automethod:: djstripe.managers.ChargeManager.during
    .. automethod:: djstripe.managers.ChargeManager.paid_totals_for
