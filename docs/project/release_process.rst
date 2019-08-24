Release Process
===============

.. contents::


.. Attention:: Before ``MAJOR`` or ``MINOR`` releases:

	* Review deprecation notes (eg search for "deprecated") and remove deprecated features as appropriate
	* Squash migrations (ONLY on unreleased migrations) - see below

.. _squash_migrations:

Squash migrations
-----------------

If there's more than one unreleased migration on master consider squashing them with ``squashmigrations``,
immediately before tagging the new release:

* Create a new squashed migration with ``./manage.py squashmigrations`` (only squash migrations that have never been in a tagged release)
* Commit the squashed migration on master with a commit message like "Squash migrations" (this will allow users who running master to safely upgrade)
* Then transition the squashed migration to a normal migration as per Django:
	* Delete all the migration files it replaces
	* Update all migrations that depend on the deleted migrations to depend on the squashed migration instead
	* Remove the ``replaces`` attribute in the Migration class of the squashed migration (this is how Django tells that it is a squashed migration)
* Commit these changes to master with a message like "Transition squashed migration to normal migration"
* Then do the normal release process - bump version as another commit and tag the release

See https://docs.djangoproject.com/en/dev/topics/migrations/#migration-squashing

Prepare changes for the release commit
--------------------------------------

* Choose your version number (using https://semver.org/  )
	* if there's a new migration, it should be a ``MAJOR.0.0`` or ``MAJOR.MINOR.0`` version.
* Review and update ``HISTORY.rst``
	* Add a section for this release version
	* Set date on this release version
	* Check that summary of feature/fixes is since the last release is up to date
* Update package version number in ``setup.cfg``
* Review and update supported API version in ``README.rst``
	(this is the most recent Stripe account version tested against, not ``DEFAULT_STRIPE_API_VERSION``)
* ``git add`` to stage these changes

Create signed release commit tag
--------------------------------

.. Note:: Before doing this you should have a GPG key set up on github

	If you don't have a GPG key already, one method is via https://keybase.io/ , and then add it to your github profile.

* Create a release tag with the above staged changes (where ``$VERSION`` is the version number to be released::

	$ git commit -m "Release $VERSION"
	$ git tag -fsm "Release $VERSION" $VERSION

This can be expressed as a bash function as follows::

	git_release() { git commit -m "Release $1" && git tag -fsm "Release $1" $1; }

* Push the commit and tag::

	$ git push --follow-tags

Update/create stable branch
---------------------------

Push these changes to the appropriate ``stable/MAJOR.MINOR`` version branch (eg ``stable/2.0``) if they're not already - note that this will trigger the readthedocs build

Configure readthedocs
---------------------

If this is this is a new stable branch then do the following on https://readthedocs.org/dashboard/dj-stripe/versions/

* Find the new ``stable/MAJOR.MINOR`` branch name and mark it as active (and then save)
* Change the default version to this new branch

Release on pypi
---------------

TODO
