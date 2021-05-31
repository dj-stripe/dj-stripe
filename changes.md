Update pre-commit with mypy.
Improve Documentation:
    1) The Process webhook celery example
    2) More examples of how to use the library.
        A) Especially webhooks
    3) How to set up dev and testing environment to contribute
Improve Automation (Borrow from pydanny):
    1) Add running pre-commit as a job in the "linting" stage in ci.yml.
    2) Automatically populate contributors like pydanny
    5) Add Change-log template
    6) Add release_drafter yaml

Add a Dockerfle and a docker-compose file to allow users to run the entire app in a docker container for dev
