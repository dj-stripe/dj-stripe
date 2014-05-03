==========================
Integration Tests
==========================

All the tests in this directory interact with the stripe API. In order to make them fire, you
need to set the STRIPE_PUBLIC_KEY and STRIPE_PRIVATE_KEY in your environment. Otherwise these tests will fail.