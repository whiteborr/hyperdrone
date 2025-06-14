# This file is deprecated and has been removed.
# Please import constants directly from the root constants.py file:
#
# from constants import *
#
# This file will be removed in a future update.

import logging
import sys

logger = logging.getLogger(__name__)
logger.error("hyperdrone_core/constants.py is deprecated. Import directly from root constants.py.")

# Import from root constants.py for backward compatibility
from constants import *