========
Usage
========

Nearly every project breaks payment types into two broad categories, and will support either or both:

1. Ongoing Subscriptions (Well supported)
2. Individual Checkouts (Early, undocumented support)

Ongoing Subscriptions
=====================

dj-stripe provides three methods to support ongoing subscriptions:

* Middleware approach to constrain entire projects easily.
* Class-Based View mixin to constrain individual views.
* View decoration to constrain Function-based views.

.. warning:: **anonymous** users always raise a ``ImproperlyConfigured`` exception.

     When **anonymous** users encounter these components they will raise a ``django.core.exceptions.ImproperlyConfigured`` exception. This is done because dj-stripe is not an authentication system, so it does a hard error to make it easier for you to catch where content may not be behind authentication systems.

Any project can use one or more of these methods to control access.


Constraining Entire Sites
-------------------------

If you want to quickly constrain an entire site, the ``djstripe.middleware.SubscriptionPaymentMiddleware`` middleware does the following to user requests:

* **authenticated** users are redirected to ``djstripe.views.SubscribeFormView`` unless they:

    * have a valid subscription --or--
    * are superusers (user.is_superuser==True) --or--
    * are staff members (user.is_staff==True).

* **anonymous** users always raise a ``django.core.exceptions.ImproperlyConfigured`` exception when they encounter these systems. This is done because dj-stripe is not an authentication system.

----

**Example:**

Step 1: Add the middleware:

.. code-block:: python

    MIDDLEWARE_CLASSES = (
        ...
        'djstripe.middleware.SubscriptionPaymentMiddleware',
        ...
        )

Step 2: Specify exempt URLS:

.. code-block:: python

    # sample only - customize to your own needs!
    # djstripe pages are automatically exempt!
    DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS = (
        'home',
        'about',
        "[spam]",  # Anything in the dj-spam namespace
    )

Using this example any request on this site that isn't on the homepage, about, spam, or djstripe pages is redirected to ``djstripe.views.SubscribeFormView``.

.. note::

    The extensive list of rules for this feature can be found at https://github.com/dj-stripe/dj-stripe/blob/master/djstripe/middleware.py.

.. seealso::

    * :doc:`settings`

Constraining Class-Based Views
------------------------------

If you want to quickly constrain a single Class-Based View, the ``djstripe.decorators.subscription_payment_required`` decorator does the following to user requests:

* **authenticated** users are redirected to ``djstripe.views.SubscribeFormView`` unless they:

    * have a valid subscription --or--
    * are superusers (user.is_superuser==True) --or--
    * are staff members (user.is_staff==True).

* **anonymous** users always raise a ``django.core.exceptions.ImproperlyConfigured`` exception when they encounter these systems. This is done because dj-stripe is not an authentication system.

----

**Example:**

.. code-block:: python

    # import necessary Django stuff
    from django.http import HttpResponse
    from django.views.generic import View
    from django.contrib.auth.decorators import login_required

    # import the wonderful decorator
    from djstripe.decorators import subscription_payment_required

    # import method_decorator which allows us to use function
    # decorators on Class-Based View dispatch function.
    from django.utils.decorators import method_decorator


    class MyConstrainedView(View):

        def get(self, request, *args, **kwargs):
            return HttpReponse("I like cheese")

        @method_decorator(login_required)
        @method_decorator(subscription_payment_required)
        def dispatch(self, *args, **kwargs):
            return super(MyConstrainedView, self).dispatch(*args, **kwargs)


If you are unfamiliar with this technique please read the following documentation `here <https://docs.djangoproject.com/en/1.5/topics/class-based-views/intro/#decorating-the-class>`_.


Constraining Function-Based Views
---------------------------------

If you want to quickly constrain a single Function-Based View, the ``djstripe.decorators.subscription_payment_required`` decorator does the following to user requests:

* **authenticated** users are redirected to ``djstripe.views.SubscribeFormView`` unless they:

    * have a valid subscription --or--
    * are superusers (user.is_superuser==True) --or--
    * are staff members (user.is_staff==True).

* **anonymous** users always raise a ``django.core.exceptions.ImproperlyConfigured`` exception when they encounter these systems. This is done because dj-stripe is not an authentication system.

----

**Example:**

.. code-block:: python

    # import necessary Django stuff
    from django.contrib.auth.decorators import login_required
    from django.http import HttpResponse

    # import the wonderful decorator
    from djstripe.decorators import subscription_payment_required

    @login_required
    @subscription_payment_required
    def my_constrained_view(request):
        return HttpResponse("I like cheese")


Don't do this!
---------------

Described is an anti-pattern. View logic belongs in views.py, not urls.py.

.. code-block:: python

    # DON'T DO THIS!!!
    from django.conf.urls import patterns, url
    from django.contrib.auth.decorators import login_required
    from djstripe.decorators import subscription_payment_required

    from contents import views

    urlpatterns = patterns("",

        # Class-Based View anti-pattern
        url(
            r"^content/$",

            # Not using decorators as decorators
            # Harder to see what's going on
            login_required(
                subscription_payment_required(
                    views.ContentDetailView.as_view()
                )
            ),
            name="content_detail"
        ),
        # Function-Based View anti-pattern
        url(
            r"^content/$",

            # Example with function view
            login_required(
                subscription_payment_required(
                    views.content_list_view
                )
            ),
            name="content_detail"
        ),
    )

Extending Subscriptions
=======================

``Subscription.extend(*delta*)``

Subscriptions can be extended by using the ``Subscription.extend`` method, which takes a positive ``timedelta`` as its only property. This method is useful if you want to offer time-cards, gift-cards, or some other external way of subscribing users or extending subscriptions, while keeping the billing handling within Stripe.

.. warning::

    Subscription extensions are achieved by manipulating the ``trial_end`` of the subscription instance, which means that Stripe will change the status to ``trialing``.
