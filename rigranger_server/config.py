#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration utilities for RigRanger Server.

This module provides functions for loading, saving, and managing configuration
for the RigRanger Server.
"""

import os
import json
import logging
from typing import Dict, Any

# Initialize logger
logger = logging.getLogger("rig_ranger.config")

DEFAULT_CONFIG = {
    "server": {
        "port": 8080,
        "host": "0.0.0.0",
        "static_files_path": "public"
    },
    "hamlib": {
        "model": 1,  # Default: Hamlib dummy device
        "device": None,
        "port": 4532
    },
    "audio": {
        "enabled": False,
        "input_device": "default",
        "output_device": "default",
        "sample_rate": 48000,
        "channels": 1
    }
}


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from a file or use default configuration.

    Args:
        config_path (str, optional): Path to the configuration file

    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    config = DEFAULT_CONFIG.copy()

    if config_path:
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)

            # Merge user config with default config
            for section in user_config:
                if section in config:
                    config[section].update(user_config[section])
                else:
                    config[section] = user_config[section]

            logger.info(f"Configuration loaded from {config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration from {config_path}: {e}")
            logger.info("Using default configuration")

    return config


def save_config(config: Dict[str, Any], config_path: str) -> bool:
    """
    Save configuration to a file.

    Args:
        config (Dict[str, Any]): Configuration dictionary
        config_path (str): Path to save the configuration file

    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)

        logger.info(f"Configuration saved to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration to {config_path}: {e}")
        return False


def get_default_config_path() -> str:
    """
    Get the default path for the configuration file.

    Returns:
        str: Path to the default configuration file
    """
    if os.name == 'nt':  # Windows
        app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
        config_dir = os.path.join(app_data, 'RigRanger')
    else:  # Unix/Linux/MacOS
        config_dir = os.path.expanduser('~/.config/rigranger')

    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, 'config.json')
