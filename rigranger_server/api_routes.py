#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Routes for RigRanger Server.

This module defines all the HTTP API endpoints for the RigRanger Server.
"""

import logging
from aiohttp import web
from typing import Any

from .utils import get_ip_addresses

# Initialize logger
logger = logging.getLogger("rig_ranger.api_routes")


async def handle_root(server: Any, request: web.Request) -> web.Response:
    """
    Handle requests to the root URL.

    Args:
        server: The RigRanger server instance
        request: The HTTP request

    Returns:
        web.Response: Server info response
    """
    return web.json_response({
        'name': 'RigRanger Server',
        'version': '0.1.0',
        'status': 'running',
        'hamlib': server.hamlib.get_status()
    })


async def handle_status(server: Any, request: web.Request) -> web.Response:
    """
    Handle status API requests.

    Args:
        server: The RigRanger server instance
        request: The HTTP request

    Returns:
        web.Response: Server status response
    """
    ips = get_ip_addresses()

    return web.json_response({
        'status': 'running',
        'port': server.port,
        'host': server.host,
        'addresses': ips,
        'hamlib': server.hamlib.get_status()
    })


async def handle_radio_info(server: Any, request: web.Request) -> web.Response:
    """
    Handle radio info API requests.

    Args:
        server: The RigRanger server instance
        request: The HTTP request

    Returns:
        web.Response: Radio info response
    """
    try:
        info = await server.run_in_executor(server.hamlib.get_info)
        return web.json_response(info)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)


async def handle_get_frequency(server: Any, request: web.Request) -> web.Response:
    """
    Handle get frequency API requests.

    Args:
        server: The RigRanger server instance
        request: The HTTP request

    Returns:
        web.Response: Current frequency
    """
    try:
        freq = await server.run_in_executor(server.hamlib.get_frequency)
        return web.json_response({'frequency': freq})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)


async def handle_set_frequency(server: Any, request: web.Request) -> web.Response:
    """
    Handle set frequency API requests.

    Args:
        server: The RigRanger server instance
        request: The HTTP request

    Returns:
        web.Response: Success/failure response
    """
    try:
        data = await request.json()
        freq = data.get('frequency')

        if freq is None:
            return web.json_response({'error': 'Frequency parameter is required'}, status=400)

        success = await server.run_in_executor(server.hamlib.set_frequency, freq)

        if success:
            return web.json_response({'status': 'success', 'frequency': freq})
        else:
            return web.json_response({'status': 'error', 'message': 'Failed to set frequency'}, status=500)

    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)


async def handle_get_mode(server: Any, request: web.Request) -> web.Response:
    """
    Handle get mode API requests.

    Args:
        server: The RigRanger server instance
        request: The HTTP request

    Returns:
        web.Response: Current mode and passband
    """
    try:
        mode_info = await server.run_in_executor(server.hamlib.get_mode)
        return web.json_response(mode_info)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)


async def handle_set_mode(server: Any, request: web.Request) -> web.Response:
    """
    Handle set mode API requests.

    Args:
        server: The RigRanger server instance
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

        success = await server.run_in_executor(server.hamlib.set_mode, mode, passband)

        if success:
            return web.json_response({'status': 'success', 'mode': mode, 'passband': passband})
        else:
            return web.json_response({'status': 'error', 'message': 'Failed to set mode'}, status=500)

    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)


async def handle_get_ptt(server: Any, request: web.Request) -> web.Response:
    """
    Handle get PTT API requests.

    Args:
        server: The RigRanger server instance
        request: The HTTP request

    Returns:
        web.Response: Current PTT status
    """
    try:
        ptt = await server.run_in_executor(server.hamlib.get_ptt)
        return web.json_response({'ptt': ptt})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)


async def handle_set_ptt(server: Any, request: web.Request) -> web.Response:
    """
    Handle set PTT API requests.

    Args:
        server: The RigRanger server instance
        request: The HTTP request

    Returns:
        web.Response: Success/failure response
    """
    try:
        data = await request.json()
        ptt = data.get('ptt')

        if ptt is None:
            return web.json_response({'error': 'PTT parameter is required'}, status=400)

        success = await server.run_in_executor(server.hamlib.set_ptt, ptt)

        if success:
            return web.json_response({'status': 'success', 'ptt': ptt})
        else:
            return web.json_response({'status': 'error', 'message': 'Failed to set PTT'}, status=500)

    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)


async def handle_get_config(server: Any, request: web.Request) -> web.Response:
    """
    Handle config API requests.

    Args:
        server: The RigRanger server instance
        request: The HTTP request

    Returns:
        web.Response: Current configuration
    """
    return web.json_response(server.config)


async def handle_update_config(server: Any, request: web.Request) -> web.Response:
    """
    Handle config update API requests.

    Args:
        server: The RigRanger server instance
        request: The HTTP request

    Returns:
        web.Response: Success/failure response
    """
    try:
        config = await request.json()
        if not isinstance(config, dict):
            return web.json_response({'error': 'Invalid config format'}, status=400)

        # Try to update the configuration
        success = server.update_config(config, 'config.json')

        if success:
            return web.json_response({
                'status': 'success',
                'message': 'Configuration updated successfully'
            })
        else:
            return web.json_response({
                'status': 'error',
                'message': 'Failed to save configuration'
            }, status=500)

    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)


def setup_api_routes(server: Any) -> None:
    """
    Set up HTTP API routes.

    Args:
        server: The RigRanger server instance
    """
    # Root and status routes
    server.app.router.add_get('/', lambda request: handle_root(server, request))
    server.app.router.add_get('/api/status', lambda request: handle_status(server, request))

    # Configuration routes
    server.app.router.add_get('/api/config', lambda request: handle_get_config(server, request))
    server.app.router.add_post('/api/config', lambda request: handle_update_config(server, request))

    # Radio control routes
    server.app.router.add_get('/api/radio/info', lambda request: handle_radio_info(server, request))
    server.app.router.add_get('/api/radio/frequency', lambda request: handle_get_frequency(server, request))
    server.app.router.add_post('/api/radio/frequency', lambda request: handle_set_frequency(server, request))
    server.app.router.add_get('/api/radio/mode', lambda request: handle_get_mode(server, request))
    server.app.router.add_post('/api/radio/mode', lambda request: handle_set_mode(server, request))
    server.app.router.add_get('/api/radio/ptt', lambda request: handle_get_ptt(server, request))
    server.app.router.add_post('/api/radio/ptt', lambda request: handle_set_ptt(server, request))
