try:
    import floppyforms
except ImportError:
    floppyforms = None

if floppyforms:

    class StripeWidget(floppyforms.TextInput):
        template_name = 'djstripe/stripe_input.html'
