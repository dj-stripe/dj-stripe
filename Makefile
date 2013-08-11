lint:
	flake8 dj-stripe tests

test:
	python runtests.py

coverage:
	coverage run --source djstripe runtests.py
	coverage report -m

htmlcov:
	coverage run --source djstripe runtests.py
	coverage html
	open htmlcov/index.html
