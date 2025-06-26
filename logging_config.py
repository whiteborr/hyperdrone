# logging_config.py
from logging import getLogger, Formatter, StreamHandler, INFO
from logging.handlers import RotatingFileHandler
from os.path import join, dirname, abspath
from os import makedirs
from sys import stdout

def setup_logging(log_level=INFO):
    """
    Configure logging for the entire application.
    
    Args:
        log_level: The logging level to use (default: logging.INFO)
    """
    # Create logs directory if it doesn't exist
    logs_dir = join(dirname(abspath(__file__)), 'logs')
    makedirs(logs_dir, exist_ok=True)
    
    # Configure root logger
    root_logger = getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers to avoid duplicate logs
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)
    
    # Create formatters
    console_formatter = Formatter('%(levelname)s: %(message)s')
    file_formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler
    console_handler = StreamHandler(stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # File handler (rotating log file)
    file_handler = RotatingFileHandler(
        join(logs_dir, 'hyperdrone.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(log_level)
    root_logger.addHandler(file_handler)
    
    # Return the configured logger
    return root_logger
