"""dbtscope: interactive map of a dbt project (domain universe and ERD), from the manifest."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("dbtscope")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0.0.0"
