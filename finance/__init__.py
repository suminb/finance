import sys

from logbook import Logger, StreamHandler


__version__ = "0.4.1"
__author__ = "Sumin Byeon"
__email__ = "suminb@gmail.com"


StreamHandler(sys.stderr).push_application()
log = Logger("finance")
