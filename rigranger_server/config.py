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
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Initialize logger
logger = logging.getLogger("rig_ranger.config")

DEFAULT_CONFIG = {
    "server": {
        "port": 8080,
        "host": "0.0.0.0"
    },
    "hamlib": {
        "model": 1,  # Default: Hamlib dummy device
        "device": None,
        "port": 4532,
        "baud": 19200,
        "retry_interval": 5,
        "reconnect_attempts": 5
    },
    "audio": {
        "enabled": False,
        "input_device": "default",
        "output_device": "default",
        "sample_rate": 48000,
        "channels": 1
    },
    "logging": {
        "level": "info",
        "file": "rig_ranger_server.log",
        "console": True
    }
}

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


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from a file or use default configuration.

    Args:
        config_path (str, optional): Path to the configuration file

    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    # If no config path specified, use default path
    if not config_path:
        config_path = get_default_config_path()

    # Start with default config
    config = DEFAULT_CONFIG.copy()

    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)

            # Deep merge user config with default config
            for section, section_config in user_config.items():
                if section in config and isinstance(config[section], dict) and isinstance(section_config, dict):
                    config[section].update(section_config)
                else:
                    config[section] = section_config

            logger.info(f"Configuration loaded from {config_path}")
        else:
            logger.info("No configuration file found, using defaults")

    except Exception as e:
        logger.error(f"Error loading configuration from {config_path}: {e}")
        logger.info("Using default configuration")

    return config


def save_config(config: Dict[str, Any], config_path: Optional[str] = None) -> bool:
    """
    Save configuration to a file.

    Args:
        config (Dict[str, Any]): Configuration dictionary
        config_path (str, optional): Path to save the configuration file

    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        # If no config path specified, use default path
        if not config_path:
            config_path = get_default_config_path()

        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)

        # Write config to file
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        logger.info(f"Configuration saved to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration to {config_path}: {e}")
        return False


def update_config(config: Dict[str, Any], updates: Dict[str, Any], config_path: Optional[str] = None) -> Tuple[Dict[str, Any], bool]:
    """
    Update and save configuration.

    Args:
        config (Dict[str, Any]): Current configuration dictionary
        updates (Dict[str, Any]): Updates to apply
        config_path (str, optional): Path to save the configuration file

    Returns:
        Tuple[Dict[str, Any], bool]: Updated config and success flag
    """
    # Deep merge updates into config
    for section, section_updates in updates.items():
        if section in config and isinstance(config[section], dict) and isinstance(section_updates, dict):
            config[section].update(section_updates)
        else:
            config[section] = section_updates

    # Save the updated config
    success = save_config(config, config_path)

    return config, success
