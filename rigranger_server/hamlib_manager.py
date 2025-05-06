#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HamlibManager module for the RigRanger Server.

This module provides the HamlibManager class, which is responsible for managing
Hamlib's rigctld and interacting with it to control amateur radios.
"""

import os
import sys
import time
import socket
import subprocess
import threading
import logging
from typing import Dict, List, Optional, Union, Any, Callable

logger = logging.getLogger("rig_ranger.hamlib")

class HamlibManager:
    """
    A utility class for managing Hamlib's rigctld and interacting with it.

    This class is responsible for:
    - Finding and launching the rigctld program
    - Communicating with rigctld via a TCP socket
    - Providing high-level functions for radio control
    - Implementing error handling and reconnection logic
    - Emitting events for radio status changes
    """

    def __init__(self):
        """Initialize the HamlibManager."""
        self.rigctld_process = None
        self.socket = None
        self.connected = False
        self.port = 4532
        self.host = '127.0.0.1'
        self.model = 1  # Default model: Hamlib dummy/simulator
        self.device = None
        self.binary_path = self.find_rigctld_path()
        self.command_queue = []
        self.processing = False
        self.reconnect_timer = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2  # seconds
        self.event_callbacks = {
            'status': [],
            'data': [],
            'debug': []
        }
        self.socket_lock = threading.Lock()

    def find_rigctld_path(self) -> Optional[str]:
        """
        Find the path to the rigctld binary.

        Returns:
            Optional[str]: Path to rigctld or None if not found
        """
        # Default paths to look for the rigctld binary
        possible_paths = [
            # Windows
            r'C:\Program Files\Hamlib\bin\rigctld.exe',
            r'C:\Program Files (x86)\Hamlib\bin\rigctld.exe',

            # Linux
            '/usr/bin/rigctld',
            '/usr/local/bin/rigctld',

            # macOS
            '/usr/local/bin/rigctld',
            '/opt/homebrew/bin/rigctld',

            # Check in PATH
            'rigctld'
        ]

        # Check if running on a Raspberry Pi with GPIO
        try:
            import RPi.GPIO
            # Add Raspberry Pi specific paths
            possible_paths.append('/usr/local/bin/rigctld')
            possible_paths.append('/home/pi/hamlib/bin/rigctld')
        except ImportError:
            pass

        # Check if the paths exist and are executable
        for path in possible_paths:
            try:
                # For 'rigctld' in PATH, use 'which' command
                if path == 'rigctld':
                    try:
                        # On Windows, use where command
                        if sys.platform.startswith('win'):
                            which_result = subprocess.run(['where', 'rigctld'],
                                                     capture_output=True, text=True, check=False)
                        else:
                            which_result = subprocess.run(['which', 'rigctld'],
                                                    capture_output=True, text=True, check=False)
                        if which_result.returncode == 0:
                            return which_result.stdout.strip()
                    except Exception as e:
                        logger.debug(f"Error checking for rigctld in PATH: {e}")
                    continue

                if os.path.isfile(path) and os.access(path, os.X_OK):
                    return path
            except Exception as e:
                logger.debug(f"Error checking path {path}: {e}")
                continue

        logger.warning("rigctld not found. Please install Hamlib or specify the path manually.")
        return None

    def on(self, event: str, callback: Callable) -> None:
        """
        Register an event callback.

        Args:
            event (str): Event name ('status', 'data', 'debug')
            callback (Callable): Function to call when the event occurs
        """
        if event in self.event_callbacks:
            self.event_callbacks[event].append(callback)

    def emit(self, event: str, *args) -> None:
        """
        Emit an event to all registered callbacks.

        Args:
            event (str): Event name
            *args: Arguments to pass to the callbacks
        """
        if event in self.event_callbacks:
            for callback in self.event_callbacks[event]:
                try:
                    callback(*args)
                except Exception as e:
                    logger.error(f"Error in {event} callback: {e}")

    def start_rigctld(self, config: Dict[str, Any]) -> bool:
        """
        Start the rigctld process with the specified configuration.

        Args:
            config (dict): Configuration options for rigctld

        Returns:
            bool: True if started successfully, False otherwise
        """
        if not self.binary_path:
            self.emit('status', {'status': 'error', 'message': 'rigctld binary not found'})
            return False

        try:
            # Update configuration
            self.model = config.get('model', self.model)
            self.device = config.get('device')
            self.port = config.get('port', self.port)

            # Build command arguments
            cmd = [self.binary_path, '-m', str(self.model), '-t', str(self.port)]

            if self.device:
                cmd.extend(['-r', self.device])

            # Start the process
            logger.info(f"Starting rigctld with command: {' '.join(cmd)}")
            self.rigctld_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Give rigctld time to start
            time.sleep(1)

            # Check if rigctld is running
            if self.rigctld_process.poll() is not None:
                stderr = self.rigctld_process.stderr.read()
                error_msg = f'rigctld failed to start: {stderr}'
                logger.error(error_msg)
                self.emit('status', {
                    'status': 'error',
                    'message': error_msg
                })
                return False

            # Try to connect to rigctld
            if self.connect():
                self.emit('status', {
                    'status': 'connected',
                    'message': f'Connected to radio model {self.model} on port {self.port}'
                })
                return True
            else:
                return False

        except Exception as e:
            error_msg = f'Error starting rigctld: {str(e)}'
            logger.error(error_msg)
            self.emit('status', {'status': 'error', 'message': error_msg})
            return False

    def connect(self) -> bool:
        """
        Connect to the rigctld socket.

        Returns:
            bool: True if connected successfully, False otherwise
        """
        try:
            # Close existing socket if open
            if self.socket:
                try:
                    self.socket.close()
                except Exception as e:
                    logger.debug(f"Error closing existing socket: {e}")
                self.socket = None

            # Create a new socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # 5 second timeout
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info(f"Connected to rigctld at {self.host}:{self.port}")

            # Start listening for responses in a separate thread
            threading.Thread(target=self._listen, daemon=True).start()

            # Reset reconnect attempts
            self.reconnect_attempts = 0

            return True

        except Exception as e:
            self.connected = False
            error_msg = f'Connection error: {str(e)}'
            logger.error(error_msg)
            self.emit('status', {'status': 'error', 'message': error_msg})

            # Try to reconnect
            self._schedule_reconnect()

            return False

    def _listen(self) -> None:
        """Listen for data from the rigctld socket in a separate thread."""
        try:
            while self.connected and self.socket:
                try:
                    data = self.socket.recv(4096)
                    if not data:
                        # Connection closed
                        break

                    # Process data
                    decoded = data.decode('utf-8').strip()
                    if decoded:
                        logger.debug(f"Received data from rigctld: {decoded}")
                        self.emit('data', decoded)

                except socket.timeout:
                    # Socket timeout, just continue
                    continue
                except Exception as e:
                    logger.error(f"Socket error: {str(e)}")
                    self.emit('debug', f'Socket error: {str(e)}')
                    break

            # If we exit the loop, the connection is lost
            if self.connected:
                self.connected = False
                logger.warning("Connection to rigctld lost")
                self.emit('status', {'status': 'disconnected', 'message': 'Connection lost'})
                self._schedule_reconnect()

        except Exception as e:
            logger.error(f"Listen thread error: {str(e)}")
            self.emit('debug', f'Listen thread error: {str(e)}')

    def _schedule_reconnect(self) -> None:
        """Schedule a reconnection attempt."""
        if (self.reconnect_attempts < self.max_reconnect_attempts and
                self.reconnect_timer is None):

            self.reconnect_attempts += 1
            logger.info(f"Scheduling reconnect attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")
            self.emit('status', {
                'status': 'reconnecting',
                'message': f'Reconnecting (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})'
            })

            # Schedule reconnect
            self.reconnect_timer = threading.Timer(self.reconnect_delay, self._reconnect)
            self.reconnect_timer.daemon = True
            self.reconnect_timer.start()

    def _reconnect(self) -> None:
        """Attempt to reconnect to rigctld."""
        self.reconnect_timer = None
        if not self.connect() and self.reconnect_attempts < self.max_reconnect_attempts:
            self._schedule_reconnect()

    def execute_command(self, command: str) -> str:
        """
        Send a command to rigctld and get the response.

        Args:
            command (str): The command to send

        Returns:
            str: The response from rigctld

        Raises:
            Exception: If the connection is not established or the command fails
        """
        if not self.connected or not self.socket:
            raise Exception("Not connected to rigctld")

        try:
            with self.socket_lock:
                # Ensure command ends with newline
                if not command.endswith('\n'):
                    command += '\n'

                # Send the command
                logger.debug(f"Sending command to rigctld: {command.strip()}")
                self.socket.sendall(command.encode('utf-8'))

                # Get the response with timeout
                self.socket.settimeout(2)
                response = b''
                start_time = time.time()

                while True:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break

                    response += chunk

                    # Check if the response is complete (RPRT at the end)
                    if response.strip().endswith(b'RPRT 0') or response.strip().endswith(b'RPRT -1'):
                        break

                    # Timeout after 2 seconds
                    if time.time() - start_time > 2:
                        break

                result = response.decode('utf-8').strip()
                logger.debug(f"Received response from rigctld: {result}")
                return result

        except Exception as e:
            error_msg = f"Command execution failed: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the Hamlib connection.

        Returns:
            dict: Status information
        """
        return {
            'connected': self.connected,
            'model': self.model,
            'device': self.device,
            'port': self.port
        }

    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the connected radio.

        Returns:
            dict: Radio information

        Raises:
            Exception: If the connection is not established
        """
        if not self.connected:
            raise Exception("Not connected to rigctld")

        try:
            # Get model info
            response = self.execute_command('\\dump_state')

            # Parse the response
            info = {
                'model': self.model,
                'device': self.device
            }

            # Try to get frequency
            try:
                freq_response = self.execute_command('\\get_freq')
                if 'RPRT 0' in freq_response:
                    freq = float(freq_response.split('\n')[0].strip())
                    info['frequency'] = freq
            except Exception as e:
                logger.warning(f"Error getting frequency: {e}")

            # Try to get mode
            try:
                mode_response = self.execute_command('\\get_mode')
                if 'RPRT 0' in mode_response:
                    mode_parts = mode_response.split('\n')[0].strip().split()
                    info['mode'] = mode_parts[0]
                    if len(mode_parts) > 1:
                        info['passband'] = int(mode_parts[1])
            except Exception as e:
                logger.warning(f"Error getting mode: {e}")

            return info

        except Exception as e:
            error_msg = f"Failed to get radio info: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def get_frequency(self) -> float:
        """
        Get the current frequency of the radio.

        Returns:
            float: The frequency in Hz

        Raises:
            Exception: If the connection is not established or the command fails
        """
        if not self.connected:
            raise Exception("Not connected to rigctld")

        response = self.execute_command('\\get_freq')

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

    def set_frequency(self, freq: float) -> bool:
        """
        Set the frequency of the radio.

        Args:
            freq (float): The frequency in Hz

        Returns:
            bool: True if successful

        Raises:
            Exception: If the connection is not established or the command fails
        """
        if not self.connected:
            raise Exception("Not connected to rigctld")

        response = self.execute_command(f'\\set_freq {freq}')

        if 'RPRT 0' in response:
            return True
        else:
            error_msg = f"Failed to set frequency: {response}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def get_mode(self) -> Dict[str, Any]:
        """
        Get the current mode and passband of the radio.

        Returns:
            dict: A dictionary with 'mode' and 'passband' keys

        Raises:
            Exception: If the connection is not established or the command fails
        """
        if not self.connected:
            raise Exception("Not connected to rigctld")

        response = self.execute_command('\\get_mode')

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

    def set_mode(self, mode: str, passband: int = 0) -> bool:
        """
        Set the mode and passband of the radio.

        Args:
            mode (str): The mode to set
            passband (int, optional): The passband to set, 0 for default

        Returns:
            bool: True if successful

        Raises:
            Exception: If the connection is not established or the command fails
        """
        if not self.connected:
            raise Exception("Not connected to rigctld")

        response = self.execute_command(f'\\set_mode {mode} {passband}')

        if 'RPRT 0' in response:
            return True
        else:
            error_msg = f"Failed to set mode: {response}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def get_ptt(self) -> bool:
        """
        Get the PTT (Push To Talk) status of the radio.

        Returns:
            bool: True if PTT is on, False otherwise

        Raises:
            Exception: If the connection is not established or the command fails
        """
        if not self.connected:
            raise Exception("Not connected to rigctld")

        response = self.execute_command('\\get_ptt')

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

    def set_ptt(self, ptt: bool) -> bool:
        """
        Set the PTT (Push To Talk) status of the radio.

        Args:
            ptt (bool): True to enable PTT, False to disable

        Returns:
            bool: True if successful

        Raises:
            Exception: If the connection is not established or the command fails
        """
        if not self.connected:
            raise Exception("Not connected to rigctld")

        ptt_value = 1 if ptt else 0
        response = self.execute_command(f'\\set_ptt {ptt_value}')

        if 'RPRT 0' in response:
            return True
        else:
            error_msg = f"Failed to set PTT: {response}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def get_level(self, level_name: str) -> float:
        """
        Get a level value from the radio.

        Args:
            level_name (str): The name of the level to get (e.g., 'STRENGTH')

        Returns:
            float: The level value

        Raises:
            Exception: If the connection is not established or the command fails
        """
        if not self.connected:
            raise Exception("Not connected to rigctld")

        response = self.execute_command(f'\\get_level {level_name}')

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

    def set_level(self, level_name: str, level_value: float) -> bool:
        """
        Set a level value on the radio.

        Args:
            level_name (str): The name of the level to set
            level_value (float): The value to set

        Returns:
            bool: True if successful

        Raises:
            Exception: If the connection is not established or the command fails
        """
        if not self.connected:
            raise Exception("Not connected to rigctld")

        response = self.execute_command(f'\\set_level {level_name} {level_value}')

        if 'RPRT 0' in response:
            return True
        else:
            error_msg = f"Failed to set level {level_name}: {response}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def stop(self) -> None:
        """Stop the rigctld process and close the connection."""
        # Close the socket
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.debug(f"Error closing socket: {e}")
            self.socket = None

        # Terminate the rigctld process
        if self.rigctld_process:
            try:
                self.rigctld_process.terminate()
                self.rigctld_process.wait(timeout=2)
            except Exception as e:
                logger.debug(f"Error terminating rigctld process: {e}")
                try:
                    self.rigctld_process.kill()
                except Exception:
                    pass
            self.rigctld_process = None

        self.connected = False
        logger.info("Hamlib manager stopped")
        self.emit('status', {'status': 'disconnected', 'message': 'Manager stopped'})
