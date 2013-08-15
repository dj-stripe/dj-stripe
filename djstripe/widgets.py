try:
    import floppyforms
except ImportError:
    floppyforms = None

if floppyforms:

    class StripeWidget(floppyforms.NumberInput):
        template_name = 'djstripe/stripe_input.html'
