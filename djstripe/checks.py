from django.core import checks


@checks.register("djstripe")
def check_stripe_api_key(app_configs=None, **kwargs):
    from . import settings as djstripe_settings
    errors = []

    if not djstripe_settings.STRIPE_SECRET_KEY:
        msg = "Could not find a Stripe API key."
        hint = "Add STRIPE_TEST_SECRET_KEY and STRIPE_LIVE_SECRET_KEY to your settings."
        errors.append(checks.Critical(msg, hint=hint, id="djstripe.C001"))
    elif djstripe_settings.STRIPE_LIVE_MODE:
        if not djstripe_settings.LIVE_API_KEY.startswith("sk_live_"):
            msg = "Bad Stripe live API key."
            hint = 'STRIPE_LIVE_SECRET_KEY should start with "sk_live_"'
            errors.append(checks.Critical(msg, hint=hint, id="djstripe.W001"))
    else:
        if not djstripe_settings.TEST_API_KEY.startswith("sk_test_"):
            msg = "Bad Stripe test API key."
            hint = 'STRIPE_TEST_SECRET_KEY should start with "sk_test_"'
            errors.append(checks.Critical(msg, hint=hint, id="djstripe.W002"))

    return errors
