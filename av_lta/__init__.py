try:
    from os.path import dirname

    with open(dirname(__file__) + "/__version__.txt") as f:
        _version = f.read().strip()
except FileNotFoundError:
    _version = "0.0.0"

__version__ = _version
from . import registration  # noqa
