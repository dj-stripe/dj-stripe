---
name: Issue with webhooks or sync
about: Create a report to help us improve
title: ''
labels: ''
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:

e.g.:

1. Enable stripe webhook to dj-stripe
2. In stripe dashboard create a billing product with feature X
3. See attached error on webhook

**Expected behavior**
A clear and concise description of what you expected to happen.

If relevant it's very helpful to include webhook tracebacks and content (note that these are logged in the database at /admin/djstripe/webhookeventtrigger/ )

**Environment**
- dj-stripe version: [e.g. master at <hash>, 2.0.0 etc]
- Your Stripe account's default API version: [e.g. 2019-02-19 - shown as "default" on https://dashboard.stripe.com/developers]
- Database: [e.g. MySQL 5.7.25]
- Python version: [e.g. 3.7.2]
- Django version: [e.g. 2.1.7]

**Can you reproduce the issue with the latest version of master?**

[Yes / No]

**Additional context**
Add any other context about the problem here.
