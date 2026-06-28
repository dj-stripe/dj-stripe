# Release Process

Releases are published to [PyPI](https://pypi.org/project/dj-stripe/) automatically
by the [`release.yml`](https://github.com/dj-stripe/dj-stripe/blob/main/.github/workflows/release.yml)
GitHub Actions workflow whenever a GitHub Release is published. Publishing uses
[PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC), so no
API tokens are involved. The job runs `uv build` and uploads the resulting sdist
and wheel.

This document covers the manual steps a maintainer performs before creating that
release.

## Before a `MAJOR` or `MINOR` release

-   Review deprecation notes (e.g. search the codebase for "deprecated") and remove
    deprecated features as appropriate.
-   Squash unreleased migrations — see below.

## Squash migrations

If there is more than one unreleased migration on `main`, consider squashing them
with `squashmigrations` immediately before tagging the new release. Only ever
squash migrations that have **never** been part of a tagged release.

-   Create a squashed migration with `./manage.py squashmigrations`.
-   Commit it with a message like `Squash x.y.0dev migrations`. This lets users
    running `main` safely upgrade.
-   Transition the squashed migration to a normal migration, per
    [Django's migration-squashing docs](https://docs.djangoproject.com/en/stable/topics/migrations/#migration-squashing):
    -   Delete the migration files it replaces.
    -   Update migrations that depended on the deleted ones to depend on the
        squashed migration instead.
    -   Remove the `replaces` attribute from the squashed migration's `Migration`
        class (this is how Django recognises a squashed migration).
-   Commit these changes with a message like
    `Transition squashed migration to normal migration`.

## Prepare the release commit

-   Choose the version number following [semver](https://semver.org/). If the
    release contains a new migration, it must be a `MAJOR.0.0` or `MAJOR.MINOR.0`
    version.
-   Update the changelog under [`docs/changes/`](https://github.com/dj-stripe/dj-stripe/tree/main/docs/changes):
    finalise the section for this version and check that it summarises the changes
    since the last release.
-   Bump `version` in `pyproject.toml`.
-   Review the tested Stripe API version. The value that matters is
    `DjstripeSettings.DEFAULT_STRIPE_API_VERSION` in
    [`djstripe/settings.py`](https://github.com/dj-stripe/dj-stripe/blob/main/djstripe/settings.py)
    — the most recent Stripe account version the maintainers have tested against.

Commit these changes (a message like `Release $VERSION` is conventional) and push
to `main`.

## Publish the release

-   Create the [GitHub Release](https://github.com/dj-stripe/dj-stripe/releases/new)
    for the new version, tagging the release commit. Publishing it triggers
    `release.yml`, which builds and uploads to PyPI.
-   Verify the new version appears on [PyPI](https://pypi.org/project/dj-stripe/).

## Update the stable branch

Push the release to the matching `stable/MAJOR.MINOR` branch (e.g. `stable/2.11`).
The documentation site builds versioned docs for each stable branch; pushing to
`main` or a `stable/*` branch triggers the
[docs sync workflow](https://github.com/dj-stripe/dj-stripe/blob/main/.github/workflows/docs.yml),
which rebuilds [dj-stripe.dev](https://dj-stripe.dev/).
