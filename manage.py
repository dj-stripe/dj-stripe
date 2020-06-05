#!/usr/bin/env python
import os
import sys

try:
    from django.core.management import execute_from_command_line
except ImportError as exc:
    raise ImportError(
        "Couldn't import Django. "
        "Run `poetry shell` to activate a virtual environment first."
    ) from exc


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
