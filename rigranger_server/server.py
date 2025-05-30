#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RigRanger Server - Main Server Implementation

This module contains the core server functionality for the RigRanger Server.
It sets up the web server, Socket.IO server, and manages connections.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import socketio
from aiohttp import web

from .hamlib.hamlib_manager import HamlibManager
from .audio_manager import AudioManager
from .api_routes import setup_api_routes
from .socketio_events import setup_socket_events

# Initialize logger
logger = logging.getLogger("rig_ranger.server")


class RigRangerServer:
    """
    The main server class for RigRanger.

    This class implements:
    - A web server for HTTP API endpoints
    - Socket.IO server for real-time communication
    - Event handling for client connections
    - Integration with the HamlibManager and AudioManager
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the RigRanger server.

        Args:
            config (Dict[str, Any]): Server configuration
        """
        self.config = config
        self.server_config = config.get('server', {})
        self.hamlib_config = config.get('hamlib', {})
        self.audio_config = config.get('audio', {})

        # Port and host
        self.port = self.server_config.get('port', 8080)
        self.host = self.server_config.get('host', '0.0.0.0')        # No static files path needed for API-only server

        # Set up Socket.IO and web application
        self.sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
        self.app = web.Application()
        self.sio.attach(self.app)

        # Create Hamlib manager
        self.hamlib = HamlibManager()

        # Create Audio manager
        self.audio = AudioManager()

        # Set up routes and event handlers
        self.setup_routes()
        self.setup_hamlib_events()
        self.setup_audio_events()

        # Runner for the server
        self.runner = None
        self.site = None

    def setup_routes(self) -> None:
        # Set up API routes
        setup_api_routes(self)

        # Set up Socket.IO events
        setup_socket_events(self)

    def setup_hamlib_events(self) -> None:
        """Set up event handlers for Hamlib events."""
        # Status events
        self.hamlib.on('status', self.on_hamlib_status)

        # Data events
        self.hamlib.on('data', self.on_hamlib_data)

        # Debug events
        self.hamlib.on('debug', self.on_hamlib_debug)

    def on_hamlib_status(self, status) -> None:
        """
        Handle Hamlib status events.

        Args:
            status: Status data
        """
        logger.info(f"Hamlib status: {status}")
        asyncio.create_task(self.sio.emit('hamlib-status', status))

    def on_hamlib_data(self, data) -> None:
        """
        Handle Hamlib data events.

        Args:
            data: Data received from Hamlib
        """
        logger.debug(f"Hamlib data: {data}")
        asyncio.create_task(self.sio.emit('hamlib-data', {'data': data}))

    def on_hamlib_debug(self, message) -> None:
        """
        Handle Hamlib debug events.

        Args:
            message: Debug message
        """
        logger.debug(f"Hamlib debug: {message}")
        asyncio.create_task(self.sio.emit('hamlib-debug', {'message': message}))

    def setup_audio_events(self) -> None:
        """Set up event handlers for audio events."""
        # Not implemented in this version
        pass

    async def run_in_executor(self, func, *args):
        """
        Run a blocking function in a thread executor.

        Args:
            func: The function to run
            *args: Arguments to pass to the function

        Returns:
            Any: The result of the function
        """
        return await asyncio.get_event_loop().run_in_executor(None, func, *args)

    def setup_hamlib(self) -> None:
        """Set up Hamlib with the current configuration."""
        # Start the rigctld process
        self.hamlib.start_rigctld(self.hamlib_config)

    def create_minimal_ui(self, static_path: Path) -> None:
        """A placeholder for backwards compatibility. Not used in API-only server."""
        pass

    async def start(self) -> None:
        """Start the server."""
        # Setup Socket.IO events
        setup_socket_events(self)

        # Setup Hamlib
        self.setup_hamlib()

        # Start the web server
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        from .utils import get_ip_addresses
        ips = get_ip_addresses()
        logger.info(f"Server started on port {self.port}")

        for ip in ips:
            logger.info(f"Access the API at: http://{ip}:{self.port}")

    async def stop(self) -> None:
        """Stop the server."""
        # Stop the Hamlib manager
        self.hamlib.stop()

        # Stop the web server
        if self.site:
            await self.site.stop()

        if self.runner:
            await self.runner.cleanup()

        logger.info("Server stopped")

    def update_config(self, new_config: Dict[str, Any], config_path: Optional[str] = None) -> bool:
        """
        Update the server configuration.

        Args:
            new_config (Dict[str, Any]): New configuration dictionary
            config_path (str, optional): Path to the config file

        Returns:
            bool: True if update was successful
        """
        from .config import update_config as update_config_file

        try:
            # Update configuration through the centralized config management
            updated_config, success = update_config_file(self.config, new_config, config_path)

            if success:
                # Update internal state
                self.config = updated_config
                if 'server' in new_config:
                    self.server_config.update(new_config['server'])
                if 'hamlib' in new_config:
                    self.hamlib_config.update(new_config['hamlib'])
                    # Restart Hamlib with new config
                    self.setup_hamlib()
                if 'audio' in new_config:
                    self.audio_config.update(new_config['audio'])

            return success
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return False
