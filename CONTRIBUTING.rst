============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given. 

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/pydanny/dj-stripe/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug"
is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "feature"
is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

dj-stripe could always use more documentation, whether as part of the 
official dj-stripe docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/pydanny/dj-stripe/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `dj-stripe` for local development.

1. Fork the `dj-stripe` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/dj-stripe.git

3. Assuming the tests are run against PostgreSQL::

    $ createdb djstripe

4. Install your local copy into a virtualenv. Assuming you have virtualenvwrapper installed, this is how you set up your fork for local development::

    $ mkvirtualenv dj-stripe
    $ cd dj-stripe/
    $ python setup.py develop

5. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

Now you can make your changes locally.

6. When you're done making changes, check that your changes pass flake8 and the
tests, including testing other Python versions with tox. runtests will output both
command line and html coverage statistics and will warn you if your changes caused code
coverage to drop.::

    $ pip install -r requirements_test.txt
    $ flake8 djstripe tests
    $ python runtests.py
    $ tox
  
.. note:: Most pep8 errors in this package either of type E501 or E128.

    Run flake8 with the ignore flag to hide those errors:

        $ flake8 djstripe tests --ignore=E501,E128

To get flake8 and tox, just pip install them into your virtualenv. 

7. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

9. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring.
3. If the pull request makes changes to a model, include both South migrations (Django <= 1.6)
   and Django migrations (Django 1.7+).
4. The pull request should work for Python 2.7, 3.3, and 3.4. Check 
   https://travis-ci.org/pydanny/dj-stripe/pull_requests
   and make sure that the tests pass for all supported Python versions.