# Django + Stripe Made Easy

-   Subscription management
-   Designed for easy implementation of post-registration subscription
    forms
-   Single-unit purchases
-   Works with Django &gt;= 2.2
-   Works with Python &gt;= 3.6
-   Built-in migrations
-   Dead-Easy installation
-   Leverages the best of the 3rd party Django package ecosystem
-   `djstripe` namespace so you can have
    more than one payments related app
-   Documented
-   100% Tested

# Constraints

1.  For stripe.com only
2.  Only use or support well-maintained third-party libraries
3.  For modern Python and Django

<!--
AUTODOC SETUP: Do not remove the piece of code below.

We use mkautodoc (https://github.com/tomchristie/mkautodoc) throughout the documentation.
It works by importing, at docs build time, various attributes from our codebase and
inspecting its docstrings, members etc.
However, throughout our codebase, we call various pieces of Django's machinery. As you
might know, this requires calling django.setup() beforehand…

Autodoc has no way to run code at initialization time. So, as one of the ugliest
workarounds ever written, we force import a member of docs.django_settings initializer,
which runs django.setup() when imported.

We do this in the index.md so that it's done as the very first processed document.

Also see: https://github.com/tomchristie/mkautodoc/issues/16
-->

<style type="text/css">
/* Hide the hack signature from the index. */
.autodoc { display: none; }
</style>

::: docs.django_settings.setup
