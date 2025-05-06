#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RigRanger Server - Entry Point

This script serves as the entry point for the RigRanger Server application.
It simply imports and runs the main function.
"""

import sys
import os

# Add the parent directory to the path to allow imports from the local package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main function
from rigranger_server import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
