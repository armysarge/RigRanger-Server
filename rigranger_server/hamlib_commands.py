#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hamlib command implementation for RigRanger Server.

This module provides functions for executing specific Hamlib commands.
"""

import logging
from typing import Dict, Any, Optional, Union, Tuple

# Initialize logger
logger = logging.getLogger("rig_ranger.hamlib_commands")


def get_frequency(execute_command) -> float:
    """
    Get the current frequency of the radio.

    Args:
        execute_command: Function to execute the Hamlib command

    Returns:
        float: The frequency in Hz

    Raises:
        Exception: If the command fails
    """
    response = execute_command('\\get_freq')

    if 'RPRT 0' in response:
        try:
            freq = float(response.split('\n')[0].strip())
            return freq
        except Exception as e:
            error_msg = f"Failed to parse frequency: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    else:
        error_msg = f"Failed to get frequency: {response}"
        logger.error(error_msg)
        raise Exception(error_msg)


def set_frequency(execute_command, freq: float) -> bool:
    """
    Set the frequency of the radio.

    Args:
        execute_command: Function to execute the Hamlib command
        freq (float): The frequency in Hz

    Returns:
        bool: True if successful

    Raises:
        Exception: If the command fails
    """
    response = execute_command(f'\\set_freq {freq}')

    if 'RPRT 0' in response:
        return True
    else:
        error_msg = f"Failed to set frequency: {response}"
        logger.error(error_msg)
        raise Exception(error_msg)


def get_mode(execute_command) -> Dict[str, Any]:
    """
    Get the current mode and passband of the radio.

    Args:
        execute_command: Function to execute the Hamlib command

    Returns:
        dict: A dictionary with 'mode' and 'passband' keys

    Raises:
        Exception: If the command fails
    """
    response = execute_command('\\get_mode')

    if 'RPRT 0' in response:
        try:
            mode_parts = response.split('\n')[0].strip().split()
            result = {'mode': mode_parts[0]}
            if len(mode_parts) > 1:
                result['passband'] = int(mode_parts[1])
            else:
                result['passband'] = 0
            return result
        except Exception as e:
            error_msg = f"Failed to parse mode: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    else:
        error_msg = f"Failed to get mode: {response}"
        logger.error(error_msg)
        raise Exception(error_msg)


def set_mode(execute_command, mode: str, passband: int = 0) -> bool:
    """
    Set the mode and passband of the radio.

    Args:
        execute_command: Function to execute the Hamlib command
        mode (str): The mode to set
        passband (int, optional): The passband to set, 0 for default

    Returns:
        bool: True if successful

    Raises:
        Exception: If the command fails
    """
    response = execute_command(f'\\set_mode {mode} {passband}')

    if 'RPRT 0' in response:
        return True
    else:
        error_msg = f"Failed to set mode: {response}"
        logger.error(error_msg)
        raise Exception(error_msg)


def get_ptt(execute_command) -> bool:
    """
    Get the PTT (Push To Talk) status of the radio.

    Args:
        execute_command: Function to execute the Hamlib command

    Returns:
        bool: True if PTT is on, False otherwise

    Raises:
        Exception: If the command fails
    """
    response = execute_command('\\get_ptt')

    if 'RPRT 0' in response:
        try:
            ptt = int(response.split('\n')[0].strip())
            return ptt != 0
        except Exception as e:
            error_msg = f"Failed to parse PTT: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    else:
        error_msg = f"Failed to get PTT: {response}"
        logger.error(error_msg)
        raise Exception(error_msg)


def set_ptt(execute_command, ptt: bool) -> bool:
    """
    Set the PTT (Push To Talk) status of the radio.

    Args:
        execute_command: Function to execute the Hamlib command
        ptt (bool): True to enable PTT, False to disable

    Returns:
        bool: True if successful

    Raises:
        Exception: If the command fails
    """
    ptt_value = 1 if ptt else 0
    response = execute_command(f'\\set_ptt {ptt_value}')

    if 'RPRT 0' in response:
        return True
    else:
        error_msg = f"Failed to set PTT: {response}"
        logger.error(error_msg)
        raise Exception(error_msg)


def get_level(execute_command, level_name: str) -> float:
    """
    Get a level value from the radio.

    Args:
        execute_command: Function to execute the Hamlib command
        level_name (str): The name of the level to get (e.g., 'STRENGTH')

    Returns:
        float: The level value

    Raises:
        Exception: If the command fails
    """
    response = execute_command(f'\\get_level {level_name}')

    if 'RPRT 0' in response:
        try:
            level = float(response.split('\n')[0].strip())
            return level
        except Exception as e:
            error_msg = f"Failed to parse level {level_name}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    else:
        error_msg = f"Failed to get level {level_name}: {response}"
        logger.error(error_msg)
        raise Exception(error_msg)


def set_level(execute_command, level_name: str, level_value: float) -> bool:
    """
    Set a level value on the radio.

    Args:
        execute_command: Function to execute the Hamlib command
        level_name (str): The name of the level to set
        level_value (float): The value to set

    Returns:
        bool: True if successful

    Raises:
        Exception: If the command fails
    """
    response = execute_command(f'\\set_level {level_name} {level_value}')

    if 'RPRT 0' in response:
        return True
    else:
        error_msg = f"Failed to set level {level_name}: {response}"
        logger.error(error_msg)
        raise Exception(error_msg)


def get_info(execute_command, model: int, device: Optional[str]) -> Dict[str, Any]:
    """
    Get information about the connected radio.

    Args:
        execute_command: Function to execute the Hamlib command
        model: Radio model number
        device: Device path

    Returns:
        dict: Radio information

    Raises:
        Exception: If the command fails
    """
    try:
        # Get model info
        response = execute_command('\\dump_state')

        # Parse the response
        info = {
            'model': model,
            'device': device
        }

        # Try to get frequency
        try:
            freq = get_frequency(execute_command)
            info['frequency'] = freq
        except Exception as e:
            logger.warning(f"Error getting frequency: {e}")

        # Try to get mode
        try:
            mode_info = get_mode(execute_command)
            info['mode'] = mode_info.get('mode')
            info['passband'] = mode_info.get('passband')
        except Exception as e:
            logger.warning(f"Error getting mode: {e}")

        return info

    except Exception as e:
        error_msg = f"Failed to get radio info: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)
