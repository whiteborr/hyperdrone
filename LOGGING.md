# HYPERDRONE Logging System

This document describes the logging system implemented in the HYPERDRONE game.

## Overview

The game now uses Python's built-in `logging` module instead of print statements for all diagnostic, error, and informational messages. This provides several benefits:

- Consistent formatting of log messages
- Different log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Ability to log to both console and files
- Better control over what gets logged
- Easier to filter and search logs

## Logging Configuration

The logging system is configured in `logging_config.py`, which provides:

- Console logging for immediate feedback
- File logging with rotation (logs stored in the `logs` directory)
- Customizable log levels
- Formatted log messages with timestamps

## Log Levels

The logging system uses the following log levels:

- **DEBUG**: Detailed information, typically only valuable when diagnosing problems
- **INFO**: Confirmation that things are working as expected
- **WARNING**: Indication that something unexpected happened, or may happen in the future
- **ERROR**: Due to a more serious problem, the software couldn't perform some function
- **CRITICAL**: A serious error indicating the program may be unable to continue running

## Usage in Code

Each module gets its own logger instance:

```python
import logging
logger = logging.getLogger(__name__)
```

Then use the appropriate log level method:

```python
logger.debug("Detailed information for debugging")
logger.info("Normal operational messages")
logger.warning("Warning messages")
logger.error("Error messages")
logger.critical("Critical errors")
```

## Log File Location

Log files are stored in the `logs` directory with automatic rotation:
- Main log file: `logs/hyperdrone.log`
- When the main log file reaches 10MB, it's rotated to `hyperdrone.log.1`
- Up to 5 backup log files are kept

## Customizing Log Levels

To change the log level for the entire application, modify the `setup_logging()` call in `main.py`:

```python
logger = setup_logging(logging.DEBUG)  # For more verbose logging
```

Or for production:

```python
logger = setup_logging(logging.WARNING)  # Only show warnings and errors
```