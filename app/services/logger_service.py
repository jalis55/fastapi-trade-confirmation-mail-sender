import logging
import sys
from pathlib import Path

def setup_logger(log_name='app_logger', file_name='process.log'):
    # FIXED: Resolves absolute path safely no matter where the file is imported
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    
    log_dir = project_root / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f'{file_name}'
    
    # Create logger
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.INFO)
    
    # Clean old handlers to prevent duplicate lines in console/files
    logger.handlers.clear()
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8') # Added safe encoding
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger
