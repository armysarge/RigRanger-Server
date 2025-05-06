#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Socket.IO event handlers for RigRanger Server.

This module defines all the Socket.IO event handlers for the RigRanger Server.
"""

import logging
from typing import Any

# Initialize logger
logger = logging.getLogger("rig_ranger.socketio_events")


def setup_socket_events(server: Any) -> None:
    """
    Set up Socket.IO event handlers.

    Args:
        server: The RigRanger server instance
    """
    @server.sio.event
    async def connect(sid, environ):
        """Handle client connection."""
        logger.info(f"Client connected: {sid}")
        await server.sio.emit('server-status', {
            'status': 'running',
            'hamlib': server.hamlib.get_status()
        }, room=sid)

    @server.sio.event
    async def disconnect(sid):
        """Handle client disconnection."""
        logger.info(f"Client disconnected: {sid}")

    @server.sio.event
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
                await server.sio.emit('command-response', {
                    'error': 'Command parameter is required'
                }, room=sid)
                return

            response = await server.run_in_executor(server.hamlib.execute_command, command)

            await server.sio.emit('command-response', {
                'command': command,
                'response': response
            }, room=sid)

        except Exception as e:
            await server.sio.emit('command-response', {
                'error': str(e)
            }, room=sid)

    @server.sio.event
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
                await server.sio.emit('function-response', {
                    'error': 'Function parameter is required'
                }, room=sid)
                return

            # Get the function from the HamlibManager
            func = getattr(server.hamlib, func_name, None)

            if func is None:
                await server.sio.emit('function-response', {
                    'error': f'Function {func_name} not found'
                }, room=sid)
                return

            # Execute the function
            result = await server.run_in_executor(func, *args)

            # Send the response
            await server.sio.emit('function-response', {
                'function': func_name,
                'args': args,
                'result': result
            }, room=sid)

        except Exception as e:
            await server.sio.emit('function-response', {
                'function': data.get('function'),
                'error': str(e)
            }, room=sid)

    # Optional: Add audio events if needed
    @server.sio.event
    async def audio_command(sid, data):
        """
        Handle audio commands.

        Args:
            sid: Socket ID
            data: Command data
        """
        try:
            command = data.get('command')

            if not command:
                await server.sio.emit('audio-response', {
                    'error': 'Command parameter is required'
                }, room=sid)
                return

            # Handle different audio commands
            if command == 'get_devices':
                # Example implementation
                devices = await server.run_in_executor(lambda: {'input': [], 'output': []})
                await server.sio.emit('audio-response', {
                    'command': command,
                    'devices': devices
                }, room=sid)
            else:
                await server.sio.emit('audio-response', {
                    'error': f'Unknown audio command: {command}'
                }, room=sid)

        except Exception as e:
            await server.sio.emit('audio-response', {
                'error': str(e)
            }, room=sid)
