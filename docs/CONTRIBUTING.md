# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit helps, and
credit will always be given.

You can contribute in many ways:

## Types of Contributions

### Report Bugs

Report bugs at <https://github.com/dj-stripe/dj-stripe/issues>.

If you are reporting a bug, please include:

-   The version of python and Django you're running
-   Detailed steps to reproduce the bug.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" is open to whoever
wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "feature" is open to
whoever wants to implement it.

### Write Documentation

dj-stripe could always use more documentation, whether as part of the official dj-stripe
docs, in docstrings, or even on the web in blog posts, articles, and such.

To see the project's documentation live, run the following command:

    mkdocs serve

The documentation site will then be served on <http://127.0.0.1:8000>.

!!! attention "In case of any installation error"

    In case you get the error that some plugin is not installed, please run:
        ``` bash
        poetry install --with docs
        ```

If you wish to just generate the documentation, you can replace `serve` with `build`,
and the docs will be generated into the `site/` folder.

### Submit Feedback

The best way to send feedback is to file an issue at
<https://github.com/dj-stripe/dj-stripe/issues>.

If you are proposing a feature:

-   Explain in detail how it would work.
-   Keep the scope as narrow as possible, to make it easier to implement.
-   Remember that this is a volunteer-driven project, and that contributions are welcome
    :)

### Contributor Discussion

For questions regarding contributions to dj-stripe, another avenue is our Discord
channel at <https://discord.gg/UJY8fcc>.

## Get Started!

Ready to contribute? Here's how to set up local development.

1.  Fork [dj-stripe on Github](https://github.com/dj-stripe/dj-stripe).

1.  Clone your fork locally:

        $ git clone git@github.com:your_name_here/dj-stripe.git

1.  Set up [pre-commit](https://pre-commit.com/):

        $ git init # A git repo is required to install pre-commit
        $ pre-commit install

1.  Set up your test database. If you're running tests using PostgreSQL:

        $ createdb djstripe

    or if you want to test vs sqlite (for convenience) or MySQL, they can be selected by
    setting this environment variable:

        $ export DJSTRIPE_TEST_DB_VENDOR=sqlite
        # or: export DJSTRIPE_TEST_DB_VENDOR=mysql

    For postgres and mysql, the database host,port,username and password can be set with
    environment variables, see `tests/settings.py`

1.  Install [Poetry](https://python-poetry.org/) if you do not have it already.

    You can set up a virtual environment with:

        $ poetry install

    You can then, at any time, open a shell into that environment with:

        $ poetry shell

1.  When you're done making changes, check that your changes pass the tests. A quick
    test run can be done as follows:

        $ DJSTRIPE_TEST_DB_VENDOR=sqlite poetry run pytest --reuse-db

    You should also check that the tests pass with other python and Django versions with
    tox. pytest will output both command line and html coverage statistics and will warn
    you if your changes caused code coverage to drop.:

        $ pip install tox
        $ tox

1.  If your changes altered the models you may need to generate Django migrations:

        $ DJSTRIPE_TEST_DB_VENDOR=sqlite poetry run ./manage.py makemigrations

1.  Commit your changes and push your branch to GitHub:

        $ git add .
        $ git commit -m "Your detailed description of your changes."
        $ git push

1.  Submit a pull request through the GitHub website.

Congratulations, you're now a dj-stripe contributor! Have some ♥ from us.

## Preferred Django Model Field Types

When mapping from Stripe API field types to Django model fields, we try to follow Django
best practises where practical.

The following types should be preferred for fields that map to the Stripe API (which is
almost all fields in our models).

### Strings

-   Stripe API string fields have a [default maximum length of 5,000
    characters](https://github.com/stripe/openapi/issues/26#issuecomment-392957633).
-   In some cases a maximum length (`maxLength`) is specified in the [Stripe OpenAPI
    schema](https://github.com/stripe/openapi/tree/master/openapi).
-   We follow [Django's
    recommendation](https://docs.djangoproject.com/en/dev/ref/models/fields/#null) and
    avoid using null on string fields (which means we store `""` for string fields that
    are `null` in stripe). Note that is enforced in the sync logic in
    [StripeModel.\_stripe_object_to_record](https://github.com/dj-stripe/dj-stripe/blob/master/djstripe/models/base.py).
-   For long string fields (eg above 255 characters) we prefer `TextField` over
    `Charfield`.

Therefore the default type for string fields that don't have a maxLength specified in
the [Stripe OpenAPI schema](https://github.com/stripe/openapi/tree/master/openapi)
should usually be:

    str_field = TextField(max_length=5000, default=", blank=True, help_text="...")

### Enumerations

Fields that have a defined set of values can be implemented using `StripeEnumField`.

### Hash (dictionaries)

Use the `JSONField` in `djstripe.fields`.

### Currency amounts

Stripe handles all currency amounts as integer cents, we currently have a mixture of
fields as integer cents and decimal (eg dollar, euro etc) values, but we are aiming to
standardise on cents (see <https://github.com/dj-stripe/dj-stripe/issues/955>).

All new currency amount fields should use `StripeQuantumCurrencyAmountField`.

### Dates and Datetimes

The Stripe API uses an integer timestamp (seconds since the Unix epoch) for dates and
datetimes. We store this as a datetime field, using `StripeDateTimeField`.

## Django Migration Policy

Migrations are considered a breaking change, so it's not usually not acceptable to add a
migration to a stable branch, it will be a new `MAJOR.MINOR.0` release.

A workaround to this in the case that the Stripe API data isn't compatible with out
model (eg Stripe is sending `null` to a non-null field) is to implement the
`_manipulate_stripe_object_hook` classmethod on the model.

### Avoid new migrations with non-schema changes

If a code change produces a migration that doesn't alter the database schema (eg
changing `help_text`) then instead of adding a new migration you can edit the most
recent migration that affects the field in question.

e.g.:
<https://github.com/dj-stripe/dj-stripe/commit/e2762c38918a90f00c42ecf21187a920bd3a2087>

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1.  The pull request should include tests.
1.  The pull request must not drop code coverage below the current level.
1.  If the pull request adds functionality, the docs should be updated. Put your new
    functionality into a function with a docstring.
1.  If the pull request makes changes to a model, include Django migrations.
1.  The pull request should work for Python 3.6+. Check [Github
    Actions](https://github.com/dj-stripe/dj-stripe/actions) and make sure that the
    tests pass for all supported Python versions.
1.  Code formatting: Make sure to install `pre-commit` to automatically run it on `staged files` or run manually with `pre-commit run --all-files` at the dj-stripe root to keep a consistent style.
