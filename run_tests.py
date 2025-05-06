#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RigRanger Server - Unit Tests Runner

This script runs all unit tests for the RigRanger Server components.
"""

import os
import sys
import unittest
from pathlib import Path

# Add the parent directory to the path to allow imports from the local package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_tests():
    """Run all tests in the tests directory."""
    # Discover and run all tests
    test_suite = unittest.defaultTestLoader.discover(
        start_dir='tests',
        pattern='test_*.py'
    )

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    print("Running RigRanger Server unit tests...")
    sys.exit(run_tests())
