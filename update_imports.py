import os
import re
import logging

logger = logging.getLogger(__name__)

def update_imports_in_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace imports from hyperdrone_core.constants with imports from constants
    pattern = r'from\s+hyperdrone_core\.constants\s+import'
    replacement = 'from constants import'
    updated_content = re.sub(pattern, replacement, content)
    
    # Replace "from .constants import" with "from constants import" in hyperdrone_core files
    if '\\hyperdrone_core\\' in file_path:
        pattern = r'from\s+\.constants\s+import'
        replacement = 'from constants import'
        updated_content = re.sub(pattern, replacement, updated_content)
    
    # Write the updated content back to the file if changes were made
    if content != updated_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        return True
    return False

def find_python_files(directory):
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def main():
    base_dir = 'c:\\HYPERDRONE'
    python_files = find_python_files(base_dir)
    
    updated_files = []
    for file_path in python_files:
        if update_imports_in_file(file_path):
            updated_files.append(file_path)
    
    logger.info(f"Updated {len(updated_files)} files:")
    for file in updated_files:
        logger.info(f"  - {file}")

if __name__ == "__main__":
    main()