"""
RigRanger Server - Python Implementation

A lightweight console application for controlling amateur radios over the network
using Hamlib. This server is designed to run on small devices like Raspberry Pi.

This module provides the core functionality for the RigRanger Server.
"""

__version__ = '0.1.0'
__author__ = 'RigRanger Project Contributors'

# Import main components for easier access
from .server import RigRangerServer
from .main import main

# Export main function for the entry point script
__all__ = ['RigRangerServer', 'main']
