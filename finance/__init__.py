import sys

# FIXME: Any better way to handle this..?
try:
    from logbook import Logger, StreamHandler
except ImportError:
    import warnings

    warnings.warn("Could not import logbook")
else:
    StreamHandler(sys.stderr).push_application()
    log = Logger("finance")


__version__ = "0.7.2"
__author__ = "Sumin Byeon"
__email__ = "suminb@gmail.com"
