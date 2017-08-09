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

Report bugs at https://github.com/dj-stripe/dj-stripe/issues.

If you are reporting a bug, please include:

* The version of python and Django you're running
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

If you are adding to dj-stripe's documentation, you can see your changes by changing
into the ``docs`` directory, running ``make html`` (or ``make.bat html`` if you're
developing on Windows) from the command line, and then opening ``docs/_build/html/index.html``
in a web browser.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/dj-stripe/dj-stripe/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions are welcome :)

New Modules
-----------

As with Django we're aiming for future compatibility with Python 3.x.  Please ensure that any
new modules use the following future import statement:

```
from __future__ import absolute_import, division, print_function, unicode_literals
```

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

6. When you're done making changes, check that your changes pass the tests, including
   testing other Python versions with tox. runtests will output both command line and
   html coverage statistics and will warn you if your changes caused code coverage to drop.
   Note that if your system time is not in UTC, some tests will fail. If you want to ignore
   those tests, the --skip-utc command line option is available on runtests.py.::

    $ pip install -r tests/requirements.txt
    $ tox

7. If your changes altered the models you may need to generate Django migrations::

    $ python makemigrations.py

8. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

9. Submit a pull request through the GitHub website.

10. Congratulations, you're now a dj-stripe contributor!  Have some <3 from us.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. The pull request must not drop code coverage below the current level.
3. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring.
4. If the pull request makes changes to a model, include Django migrations (Django 1.7+).
5. The pull request should work for Python 2.7, 3.4, 3.5 and 3.6. Check
   https://travis-ci.org/dj-stripe/dj-stripe/pull_requests
   and make sure that the tests pass for all supported Python versions.
