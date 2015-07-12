from djstripe.models import Plan


basic_plan, basic_plan_created = Plan.objects.get_or_create(
    stripe_id="basic_id",
    name="Basic Plan",
    currency='USD',
    interval=1,
    amount=100,
    trial_period_days=0
)

gold_plan, gold_plan_created = Plan.objects.get_or_create(
    stripe_id="gold_id",
    name="Gold Plan",
    currency='USD',
    interval=1,
    interval_count=1,
    amount=100,
    trial_period_days=0
)

test_trial, test_trial_created = Plan.objects.get_or_create(
    stripe_id="test_trial",
    name="Trial Plan",
    currency='USD',
    interval=1,
    interval_count=1,
    amount=100,
    trial_period_days=7
)

test_trial, test_trial_created = Plan.objects.get_or_create(
    stripe_id="test_trial_9",
    name="Trial Plan",
    currency='USD',
    interval=1,
    interval_count=1,
    amount=100,
    trial_period_days=9
)

test_deletion, test_deletion_created = Plan.objects.get_or_create(
    stripe_id="test_deletion",
    name="test_deletion",
    currency='USD',
    interval=1,
    interval_count=1,
    amount=100
)

test0, test0_created = Plan.objects.get_or_create(
    stripe_id="test0",
    name="test0",
    currency='USD',
    interval=1,
    interval_count=1,
    amount=100
)
test, test_created = Plan.objects.get_or_create(
    stripe_id="test",
    name="test",
    currency='USD',
    interval=1,
    interval_count=1,
    amount=100
)

test2, test_created = Plan.objects.get_or_create(
    stripe_id="test2",
    name="test2",
    currency='USD',
    interval=1,
    interval_count=1,
    amount=100
)

Plan.objects.get_or_create(
    stripe_id="test_plan",
    name="test_plan",
    currency='USD',
    interval=1,
    interval_count=1,
    amount=100
)

fish_plan, fish_plan_created = Plan.objects.get_or_create(
    stripe_id="fish",
    name="fish",
    currency='USD',
    interval=1,
    interval_count=1,
    amount=100
)
