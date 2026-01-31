#!/usr/bin/env python3
"""
Testing Framework Wrapper for Financial Analysis Platform
Uses the universal testing framework from the global Claude directory
"""

import sys
import os
from pathlib import Path

# Add the global framework to path
global_framework = Path.home() / ".claude" / "testing_framework_template"
sys.path.insert(0, str(global_framework))

# Import and run the global framework
if __name__ == "__main__":
    # Change to global framework directory for execution
    original_cwd = os.getcwd()
    try:
        os.chdir(global_framework)
        exec(open(global_framework / "run_tests.py").read())
    finally:
        os.chdir(original_cwd)
