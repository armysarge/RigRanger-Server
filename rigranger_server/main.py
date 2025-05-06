#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main entry point for the RigRanger Server.

This module provides the main functionality for starting the RigRanger Server
with proper command-line argument parsing and configuration loading.
"""

import os
import sys
import json
import signal
import asyncio
import logging
import argparse
from typing import Dict, List, Any, Optional, Tuple

from .server import RigRangerServer
from .utils import (
    get_ip_addresses,
    find_available_serial_ports,
    get_hamlib_model_list,
    load_config
)
from .wizard import (
    should_run_wizard,
    run_config_wizard
)

# Initialize logger
logger = logging.getLogger("rig_ranger")


def setup_logging(level_name: str) -> None:
    """
    Set up logging configuration.

    Args:
        level_name (str): Logging level name
    """
    level_map = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }

    level = level_map.get(level_name.lower(), logging.INFO)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("rig_ranger_server.log")
        ]
    )


def parse_args():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='RigRanger Server - Lightweight console application for radio control'
    )

    parser.add_argument('-p', '--port', type=int, default=8080,
                        help='Server port number (default: 8080)')
    parser.add_argument('-d', '--device', type=str,
                        help='Serial device path (e.g., /dev/ttyUSB0 or COM3)')
    parser.add_argument('-m', '--model', type=int, default=1,
                        help='Hamlib radio model number (default: 1 - Dummy)')
    parser.add_argument('-c', '--config', type=str,
                        help='Path to configuration file')
    parser.add_argument('--list-models', action='store_true',
                        help='List common Hamlib radio models')
    parser.add_argument('--list-devices', action='store_true',
                        help='List available serial devices')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('-w', '--wizard', action='store_true',
                        help='Run configuration wizard')

    return parser.parse_args()


def show_models() -> None:
    """Show a list of common Hamlib radio models."""
    print("Common Hamlib Radio Models:")
    print("--------------------------")

    models = get_hamlib_model_list()

    for model in models:
        print(f"{model['id']}: {model['name']}")

    print("\nNote: This is a subset of all available models. Use 'rigctl -l' for a complete list.")


def show_devices() -> None:
    """Show a list of available serial devices."""
    print("Available Serial Devices:")
    print("-----------------------")

    devices = find_available_serial_ports()

    if not devices:
        print("No serial devices found.")
        return

    for device in devices:
        print(f"{device['device']}: {device['description']}")


async def run_server(config: Dict[str, Any]) -> None:
    """
    Run the RigRanger server.

    Args:
        config (Dict[str, Any]): Server configuration
    """
    server = RigRangerServer(config)

    # Setup signal handling for graceful shutdown
    loop = asyncio.get_running_loop()

    # Platform-specific signal handling (not implemented on Windows)
    if sys.platform != 'win32':
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(server)))
    else:
        logger.info("Running on Windows - signal handlers not implemented, use Ctrl+C to stop")

    try:
        await server.start()

        # Keep the server running
        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("Server task cancelled")

    finally:
        await server.stop()


async def shutdown(server: RigRangerServer) -> None:
    """
    Shut down the server gracefully.

    Args:
        server (RigRangerServer): The server instance
    """
    logger.info("Shutting down server...")
    await server.stop()
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    asyncio.get_event_loop().stop()


def main() -> None:
    """Main entry point for the server."""
    args = parse_args()

    # Set up logging
    log_level = 'debug' if args.verbose else 'info'
    setup_logging(log_level)

    # Show models or devices if requested
    if args.list_models:
        show_models()
        return

    if args.list_devices:
        show_devices()
        return

    # Check if we should run the wizard
    run_wiz, config_path = should_run_wizard(args)

    # Run configuration wizard if needed
    if run_wiz:
        config = run_config_wizard(config_path)
    else:
        # Load configuration
        config = load_config(args.config)

    # Override configuration with command line arguments
    if args.port:
        config['server']['port'] = args.port

    if args.model:
        config['hamlib']['model'] = args.model

    if args.device:
        config['hamlib']['device'] = args.device    # Run the server
    try:
        asyncio.run(run_server(config))
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except NotImplementedError as e:
        # This captures the specific error you're seeing with signal handlers on Windows
        print("\nError: Signal handlers not supported on this platform.")
        print("This is normal on Windows. The server will still work, but you'll need to use Ctrl+C to stop it.")
        # Try again without signal handlers
        try:
            asyncio.run(run_server(config))
        except KeyboardInterrupt:
            print("\nServer stopped by user")
    except Exception as e:
        print(f"\nError: {str(e)}")
