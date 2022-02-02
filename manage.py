#!/usr/bin/env python
import os
import sys

import debugpy

try:
    from django.core.management import execute_from_command_line
except ImportError as exc:
    raise ImportError(
        "Couldn't import Django. "
        "Run `poetry shell` to activate a virtual environment first."
    ) from exc


# ? Attach a python debuger on 0.0.0.0:5678. Can be used directly in VScode Debugger
try:
    # each gunicorn worker will try to attach to the same host and port
    # and that will throw an error as 1 process can be attached to a port
    debugpy.listen(address=("0.0.0.0", 5678))
    print("Django: Attached remote debugger")
except RuntimeError as error:
    # do nothing
    print(f"Multiple workers trying to attach the remote debugger. {error}")


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
