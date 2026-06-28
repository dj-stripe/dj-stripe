# Upgrading dj-stripe

dj-stripe periodically **squashes its migrations**. When a release squashes
migrations, its migration history no longer lines up with much older versions, so
you cannot always jump straight from a very old version to the latest one — the
intermediate migration state is missing.

The safe approach is to upgrade **one release at a time** through any version that
introduced a migration, running `migrate` at each step so your database is brought
forward through every migration in order.

## Step-by-step

Suppose you are on `2.4.0` and want to reach a much newer version.

1.  Identify the next release that changed migrations. Check the
    [releases page](https://github.com/dj-stripe/dj-stripe/releases) and the
    [release notes](https://dj-stripe.dev/changes) — a release is a migration step if its version is
    `MAJOR.0.0` or `MAJOR.MINOR.0` (dj-stripe only adds migrations in those
    releases).
2.  Pin dj-stripe to that version, e.g. update your requirements from
    `dj-stripe==2.4.0` to `dj-stripe==2.5.0`.
3.  Run the migration:

    ```bash
    python manage.py migrate djstripe
    ```

    This must succeed. If it fails, you have likely skipped an intermediate
    version — step back and migrate through it first.
4.  Repeat for each subsequent migration-bearing release until you reach your
    target version.

If you hit an incompatibility with the bundled Stripe library version, try bumping
`stripe` in your requirements as well. See
[issue #1842](https://github.com/dj-stripe/dj-stripe/issues/1842#issuecomment-1319185657)
for one such case.

## Summary

1.  Upgrade through each migration-bearing release in order, never skipping one.
2.  Run `python manage.py migrate djstripe` at every step and confirm it succeeds
    before moving on.
3.  Always review the [release notes](https://dj-stripe.dev/changes) for the
    versions you pass through, in case a release needs manual steps beyond
    migrations.
