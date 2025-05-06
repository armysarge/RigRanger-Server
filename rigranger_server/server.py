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
from typing import Dict, Any

import socketio
from aiohttp import web

from .hamlib_manager import HamlibManager
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
    - Static file serving for web interface
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
        self.host = self.server_config.get('host', '0.0.0.0')

        # Static files path
        self.static_path = Path(self.server_config.get('static_files_path', 'public'))

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
        self.setup_static_routes()
        self.setup_hamlib_events()
        self.setup_audio_events()

        # Runner for the server
        self.runner = None
        self.site = None

    def setup_routes(self) -> None:
        """Set up HTTP API routes."""
        setup_api_routes(self)

    def setup_static_routes(self) -> None:
        """Set up routes for serving static files."""
        # Check if the static directory exists
        if not self.static_path.exists():
            logger.warning(f"Static files directory {self.static_path} does not exist. Creating minimal UI.")
            self.static_path.mkdir(parents=True, exist_ok=True)
            self.create_minimal_ui(self.static_path)

        # Add static routes
        self.app.router.add_static('/static/', self.static_path, append_version=True)        # Serve index.html for the root
        self.app.router.add_get('/', self.handle_root)

    async def handle_root(self, request: web.Request) -> web.Response:
        """
        Handle requests to the root URL.

        Args:
            request: The HTTP request

        Returns:
            web.Response: Server info response
        """
        # Serve the index.html file if the public directory exists
        index_path = self.static_path / 'index.html'
        if index_path.exists():
            return web.FileResponse(index_path)

        # Otherwise, return a simple text response
        return web.Response(text="RigRanger Server is running.", content_type='text/plain')

    def create_minimal_ui(self, static_path: Path) -> None:
        """
        Create a minimal UI if the public directory doesn't exist.

        Args:
            static_path (Path): Path to the static files directory
        """
        # Create a basic index.html file
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RigRanger Server</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            line-height: 1.6;
        }
        h1 {
            color: #1976d2;
        }
        .status {
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }
        .connected {
            background-color: #e8f5e9;
            color: #2e7d32;
        }
        .disconnected {
            background-color: #ffebee;
            color: #c62828;
        }
    </style>
</head>
<body>
    <h1>RigRanger Server</h1>
    <div id="status" class="status disconnected">Not connected to server</div>
    <p>This is a minimal UI for the RigRanger Server. For a better experience, place your custom UI files in the 'public' directory.</p>

    <script src="/socket.io/socket.io.js"></script>
    <script>
        const socket = io();
        const statusDiv = document.getElementById('status');

        socket.on('connect', () => {
            statusDiv.textContent = 'Connected to server';
            statusDiv.className = 'status connected';
        });

        socket.on('disconnect', () => {
            statusDiv.textContent = 'Disconnected from server';
            statusDiv.className = 'status disconnected';
        });

        socket.on('hamlib-status', (data) => {
            if (data.status === 'connected') {
                statusDiv.textContent = 'Connected to radio';
                statusDiv.className = 'status connected';
            } else {
                statusDiv.textContent = 'Radio status: ' + data.status;
                statusDiv.className = 'status disconnected';
            }
        });
    </script>
</body>
</html>
"""
        index_path = static_path / 'index.html'
        with open(index_path, 'w') as f:
            f.write(index_html)

        logger.info(f"Created minimal UI at {index_path}")

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
            logger.info(f"Access the web interface at: http://{ip}:{self.port}")

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
