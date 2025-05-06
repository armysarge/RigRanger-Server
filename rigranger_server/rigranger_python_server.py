#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RigRanger Server - Python Implementation

A lightweight console application for controlling amateur radios over the network
using Hamlib. This server is designed to run on small devices like Raspberry Pi.
"""

import os
import sys
import json
import signal
import asyncio
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable

# Import from current package
from .hamlib_manager import HamlibManager
from .audio_manager import AudioManager
from .utils import get_ip_addresses, find_available_serial_ports, get_hamlib_model_list, load_config
from .wizard import should_run_wizard, run_config_wizard

# Initialize logger
logger = logging.getLogger("rig_ranger")

try:
    import socketio
    from aiohttp import web
except ImportError:
    logger.info("Required packages not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "python-socketio", "aiohttp"])
    import socketio
    from aiohttp import web


class RigRangerServer:
    """
    The main server class for RigRanger.

    This class implements:
    - A web server for HTTP API endpoints
    - Socket.IO server for real-time communication
    - Event handling for client connections
    - Integration with the HamlibManager
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

        # Set up routes
        self.setup_routes()

        # Create Hamlib manager
        self.hamlib = HamlibManager()

        # Create Audio manager
        self.audio = AudioManager()

        # Set up event handlers
        self.setup_hamlib_events()
        self.setup_audio_events()

        # Runner for the server
        self.runner = None
        self.site = None

    def setup_routes(self) -> None:
        """Set up HTTP routes."""
        # API routes
        self.app.router.add_get('/', self.handle_root)
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_get('/api/radio/info', self.handle_radio_info)
        self.app.router.add_get('/api/radio/frequency', self.handle_get_frequency)
        self.app.router.add_post('/api/radio/frequency', self.handle_set_frequency)
        self.app.router.add_get('/api/radio/mode', self.handle_get_mode)
        self.app.router.add_post('/api/radio/mode', self.handle_set_mode)
        self.app.router.add_get('/api/radio/ptt', self.handle_get_ptt)
        self.app.router.add_post('/api/radio/ptt', self.handle_set_ptt)

        # Static routes
        self.setup_static_routes()

        # Socket.IO events
        self.setup_socket_events()

    def setup_static_routes(self) -> None:
        """Set up routes for serving static files."""
        # Check if the static directory exists
        if not self.static_path.exists():
            logger.warning(f"Static files directory {self.static_path} does not exist. Creating minimal UI.")
            self.static_path.mkdir(parents=True, exist_ok=True)
            self.create_minimal_ui(self.static_path)

        # Add static routes
        self.app.router.add_static('/static/', self.static_path, append_version=True)

        # Serve index.html for the root
        @self.app.routes.get('/')
        async def serve_root(request):
            index_path = self.static_path / 'index.html'
            if index_path.exists():
                return web.FileResponse(index_path)
            else:
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
        return web.json_response({
            'name': 'RigRanger Server',
            'version': '0.1.0',
            'status': 'running',
            'hamlib': self.hamlib.get_status()
        })

    async def handle_status(self, request: web.Request) -> web.Response:
        """
        Handle status API requests.

        Args:
            request: The HTTP request

        Returns:
            web.Response: Server status response
        """
        ips = get_ip_addresses()

        return web.json_response({
            'status': 'running',
            'port': self.port,
            'host': self.host,
            'addresses': ips,
            'hamlib': self.hamlib.get_status()
        })

    async def handle_radio_info(self, request: web.Request) -> web.Response:
        """
        Handle radio info API requests.

        Args:
            request: The HTTP request

        Returns:
            web.Response: Radio info response
        """
        try:
            info = await self.run_in_executor(self.hamlib.get_info)
            return web.json_response(info)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def handle_get_frequency(self, request: web.Request) -> web.Response:
        """
        Handle get frequency API requests.

        Args:
            request: The HTTP request

        Returns:
            web.Response: Current frequency
        """
        try:
            freq = await self.run_in_executor(self.hamlib.get_frequency)
            return web.json_response({'frequency': freq})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def handle_set_frequency(self, request: web.Request) -> web.Response:
        """
        Handle set frequency API requests.

        Args:
            request: The HTTP request

        Returns:
            web.Response: Success/failure response
        """
        try:
            data = await request.json()
            freq = data.get('frequency')

            if freq is None:
                return web.json_response({'error': 'Frequency parameter is required'}, status=400)

            success = await self.run_in_executor(self.hamlib.set_frequency, freq)

            if success:
                return web.json_response({'status': 'success', 'frequency': freq})
            else:
                return web.json_response({'status': 'error', 'message': 'Failed to set frequency'}, status=500)

        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def handle_get_mode(self, request: web.Request) -> web.Response:
        """
        Handle get mode API requests.

        Args:
            request: The HTTP request

        Returns:
            web.Response: Current mode and passband
        """
        try:
            mode_info = await self.run_in_executor(self.hamlib.get_mode)
            return web.json_response(mode_info)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def handle_set_mode(self, request: web.Request) -> web.Response:
        """
        Handle set mode API requests.

        Args:
            request: The HTTP request

        Returns:
            web.Response: Success/failure response
        """
        try:
            data = await request.json()
            mode = data.get('mode')
            passband = data.get('passband', 0)

            if mode is None:
                return web.json_response({'error': 'Mode parameter is required'}, status=400)

            success = await self.run_in_executor(self.hamlib.set_mode, mode, passband)

            if success:
                return web.json_response({'status': 'success', 'mode': mode, 'passband': passband})
            else:
                return web.json_response({'status': 'error', 'message': 'Failed to set mode'}, status=500)

        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def handle_get_ptt(self, request: web.Request) -> web.Response:
        """
        Handle get PTT API requests.

        Args:
            request: The HTTP request

        Returns:
            web.Response: Current PTT status
        """
        try:
            ptt = await self.run_in_executor(self.hamlib.get_ptt)
            return web.json_response({'ptt': ptt})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def handle_set_ptt(self, request: web.Request) -> web.Response:
        """
        Handle set PTT API requests.

        Args:
            request: The HTTP request

        Returns:
            web.Response: Success/failure response
        """
        try:
            data = await request.json()
            ptt = data.get('ptt')

            if ptt is None:
                return web.json_response({'error': 'PTT parameter is required'}, status=400)

            success = await self.run_in_executor(self.hamlib.set_ptt, ptt)

            if success:
                return web.json_response({'status': 'success', 'ptt': ptt})
            else:
                return web.json_response({'status': 'error', 'message': 'Failed to set PTT'}, status=500)

        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    def setup_socket_events(self) -> None:
        """Set up Socket.IO event handlers."""
        @self.sio.event
        async def connect(sid, environ):
            """Handle client connection."""
            logger.info(f"Client connected: {sid}")
            await self.sio.emit('server-status', {
                'status': 'running',
                'hamlib': self.hamlib.get_status()
            }, room=sid)

        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection."""
            logger.info(f"Client disconnected: {sid}")

        @self.sio.event
        async def hamlib_command(sid, data):
            """
            Handle direct Hamlib command execution.

            Args:
                sid: Socket ID
                data: Command data
            """
            try:
                command = data.get('command')
                if not command:
                    await self.sio.emit('command-response', {
                        'error': 'Command parameter is required'
                    }, room=sid)
                    return

                response = await self.run_in_executor(self.hamlib.execute_command, command)

                await self.sio.emit('command-response', {
                    'command': command,
                    'response': response
                }, room=sid)

            except Exception as e:
                await self.sio.emit('command-response', {
                    'error': str(e)
                }, room=sid)

        @self.sio.event
        async def hamlib_function(sid, data):
            """
            Handle Hamlib function calls.

            Args:
                sid: Socket ID
                data: Function data
            """
            try:
                func_name = data.get('function')
                args = data.get('args', [])

                if not func_name:
                    await self.sio.emit('function-response', {
                        'error': 'Function parameter is required'
                    }, room=sid)
                    return

                # Get the function from the HamlibManager
                func = getattr(self.hamlib, func_name, None)

                if func is None:
                    await self.sio.emit('function-response', {
                        'error': f'Function {func_name} not found'
                    }, room=sid)
                    return

                # Execute the function
                result = await self.run_in_executor(func, *args)

                # Send the response
                await self.sio.emit('function-response', {
                    'function': func_name,
                    'args': args,
                    'result': result
                }, room=sid)

            except Exception as e:
                await self.sio.emit('function-response', {
                    'function': data.get('function'),
                    'error': str(e)
                }, room=sid)

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

    def setup_hamlib(self) -> None:
        """Set up Hamlib with the current configuration."""
        # Start the rigctld process
        self.hamlib.start_rigctld(self.hamlib_config)

    async def start(self) -> None:
        """Start the server."""
        # Setup Hamlib
        self.setup_hamlib()

        # Start the web server
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

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

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(server)))

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
        config['hamlib']['device'] = args.device

    # Run the server
    try:
        asyncio.run(run_server(config))
    except KeyboardInterrupt:
        print("\nServer stopped")


if __name__ == "__main__":
    main()
