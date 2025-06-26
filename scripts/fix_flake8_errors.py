#!/usr/bin/env python3
"""
Quick fix script for common flake8 errors
"""

import os
import re
from pathlib import Path


def fix_f_string_without_placeholders(file_path):
    """Replace f-strings without placeholders with regular strings"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to find f-strings without any {} placeholders
    pattern = r'f"([^"]*?)"(?![^{]*})'
    pattern2 = r"f'([^']*?)'(?![^{]*})"
    
    # Replace f-strings that don't contain {
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        if 'f"' in line or "f'" in line:
            # Check if line contains f-string without {}
            if ('f"' in line and '{' not in line) or ("f'" in line and '{' not in line):
                line = line.replace('f"', '"').replace("f'", "'")
        new_lines.append(line)
    
    new_content = '\n'.join(new_lines)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False


def fix_unused_imports(file_path):
    """Comment out common unused imports for MVP"""
    # This is a simple approach - in production, use autoflake
    unused_patterns = [
        (r'^from decimal import Decimal$', '# from decimal import Decimal  # TODO: Remove if truly unused'),
        (r'^import asyncio$', '# import asyncio  # TODO: Remove if truly unused'),
        (r'^from typing import List, Optional$', '# from typing import List, Optional  # TODO: Remove if truly unused'),
    ]
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    new_lines = []
    changed = False
    
    for line in lines:
        new_line = line
        for pattern, replacement in unused_patterns:
            if re.match(pattern, line.strip()):
                new_line = line.replace(line.strip(), replacement)
                changed = True
                break
        new_lines.append(new_line)
    
    if changed:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
    
    return changed


def fix_true_comparison(file_path):
    """Fix comparison to True"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace == True with is True or just remove it
    new_content = re.sub(r'(\s+)if (.+?) == True:', r'\1if \2:', content)
    new_content = re.sub(r'(\s+)if (.+?) is True:', r'\1if \2:', new_content)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False


def main():
    # Fix Python files in src/
    src_path = Path('src')
    
    fixed_files = []
    
    for py_file in src_path.rglob('*.py'):
        # Skip backup files
        if 'backup' in str(py_file):
            continue
            
        changed = False
        
        # Fix f-strings
        if fix_f_string_without_placeholders(py_file):
            changed = True
            
        # Fix True comparison
        if fix_true_comparison(py_file):
            changed = True
            
        # Fix unused imports (commented out for safety)
        # if fix_unused_imports(py_file):
        #     changed = True
            
        if changed:
            fixed_files.append(py_file)
    
    print(f"Fixed {len(fixed_files)} files:")
    for f in fixed_files:
        print(f"  - {f}")


if __name__ == "__main__":
    main()