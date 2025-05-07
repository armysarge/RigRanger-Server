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
import shutil
import platform
import zipfile
import tarfile
import re
import json
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable

# Try to import requests, but fall back to urllib if not available
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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

        # Check if Hamlib is installed or download it if needed
        self.hamlib_app_path = self._ensure_hamlib_installed()
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
        # Default paths to look for the rigctld binary based on platform
        possible_paths = []

        # Add our local app directory paths first
        app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")

        if sys.platform.startswith('win'):
            # Windows paths
            # Check our local app installation first
            for root, dirs, files in os.walk(app_dir):
                if 'bin' in dirs:
                    bin_dir = os.path.join(root, 'bin')
                    if os.path.exists(os.path.join(bin_dir, 'rigctld.exe')):
                        possible_paths.append(os.path.join(bin_dir, 'rigctld.exe'))
                elif 'rigctld.exe' in files:
                    possible_paths.append(os.path.join(root, 'rigctld.exe'))

            # Standard Windows paths
            possible_paths.extend([
                r'C:\Program Files\Hamlib\bin\rigctld.exe',
                r'C:\Program Files (x86)\Hamlib\bin\rigctld.exe',
                'rigctld.exe'  # Check in PATH
            ])
        else:
            # Unix-like systems (Linux, macOS)
            # Check our local app installation first
            for root, dirs, files in os.walk(app_dir):
                if 'bin' in dirs:
                    bin_dir = os.path.join(root, 'bin')
                    if os.path.exists(os.path.join(bin_dir, 'rigctld')):
                        possible_paths.append(os.path.join(bin_dir, 'rigctld'))
                elif 'rigctld' in files:
                    possible_paths.append(os.path.join(root, 'rigctld'))

            # Standard Unix paths
            possible_paths.extend([
                '/usr/bin/rigctld',
                '/usr/local/bin/rigctld',
                '/opt/homebrew/bin/rigctld',  # macOS homebrew
                'rigctld'  # Check in PATH
            ])

            # Check if running on a Raspberry Pi
            try:
                # Just check if we're on a Raspberry Pi without importing GPIO
                with open('/proc/cpuinfo', 'r') as f:
                    if 'Raspberry Pi' in f.read():
                        possible_paths.append('/home/pi/hamlib/bin/rigctld')
            except:
                pass

        # Check if the paths exist and are executable
        for path in possible_paths:
            try:
                # For 'rigctld' in PATH, use 'which' command
                if path == 'rigctld' or path == 'rigctld.exe':
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
        Get the current status of the Hamlib manager.

        Returns:
            Dict[str, Any]: Status dictionary
        """
        return {
            'connected': self.connected,
            'port': self.port,
            'host': self.host,
            'model': self.model,
            'device': self.device,
            'binary_path': self.binary_path,
            'reconnect_attempts': self.reconnect_attempts,
            'max_reconnect_attempts': self.max_reconnect_attempts,
            'rigctld_running': self.rigctld_process is not None and self.rigctld_process.poll() is None
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

    def _ensure_hamlib_installed(self) -> Optional[str]:
        """
        Ensure that Hamlib is installed on the system.
        If it's not found in common locations, download and extract it.

        Returns:
            Optional[str]: Path to the Hamlib installation directory
        """
        # First check if rigctld is available in common locations
        rigctld_path = self.find_rigctld_path()
        if rigctld_path:
            logger.info(f"Found existing Hamlib installation at: {rigctld_path}")
            return os.path.dirname(os.path.dirname(rigctld_path))

        # If not found, prepare to download
        logger.info("Hamlib not found. Will download and install it.")

        # Create app directory if it doesn't exist
        app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
        os.makedirs(app_dir, exist_ok=True)

        # Check if we already have a downloaded version
        if os.path.exists(app_dir):
            # Look for bin directory with rigctld
            for root, dirs, files in os.walk(app_dir):
                if sys.platform.startswith('win'):
                    if "rigctld.exe" in files:
                        return app_dir
                else:
                    if "rigctld" in files:
                        return app_dir

        # Download the latest release
        try:
            downloaded_path = self._download_latest_hamlib()
            if downloaded_path:
                # Extract the downloaded file
                extracted_dir = self._extract_hamlib(downloaded_path, app_dir)
                if extracted_dir:
                    logger.info(f"Successfully installed Hamlib to {extracted_dir}")
                    return extracted_dir
        except Exception as e:
            logger.error(f"Failed to download and install Hamlib: {e}")

        return None

    def _download_latest_hamlib(self) -> Optional[str]:
        """
        Download the latest Hamlib release from GitHub.

        Returns:
            Optional[str]: Path to the downloaded file or None if failed
        """
        try:
            # Determine which version to download based on platform
            if sys.platform.startswith('win'):
                arch = 'w64' if platform.architecture()[0] == '64bit' else 'w32'
                file_pattern = f"hamlib-{arch}"
                ext = ".zip"
            else:
                file_pattern = "hamlib"
                ext = ".tar.gz"

            # Get GitHub API URL for latest release
            api_url = "https://api.github.com/repos/Hamlib/Hamlib/releases/latest"

            # Fetch latest release info
            try:
                # Try to use requests if available
                if HAS_REQUESTS:
                    import requests
                    response = requests.get(api_url)
                    release_info = response.json()
                else:
                    # Fall back to urllib
                    with urllib.request.urlopen(api_url) as response:
                        release_info = json.loads(response.read().decode('utf-8'))
            except Exception as e:
                logger.error(f"Error fetching release info: {e}")

                # If GitHub API fails, try to use a direct link to the latest known release
                if sys.platform.startswith('win'):
                    # Direct link to a known good release from GitHub
                    arch = 'w64' if platform.architecture()[0] == '64bit' else 'w32'
                    download_url = f"https://github.com/Hamlib/Hamlib/releases/download/4.6.2/hamlib-{arch}-4.6.2.zip"
                    download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
                    os.makedirs(download_dir, exist_ok=True)
                    file_name = os.path.join(download_dir, os.path.basename(download_url))

                    logger.info(f"Downloading Hamlib from direct link: {download_url}")
                    urllib.request.urlretrieve(download_url, file_name)
                    logger.info(f"Download completed: {file_name}")
                    return file_name
                return None

            # Find the appropriate asset to download
            download_url = None
            for asset in release_info['assets']:
                if file_pattern in asset['name'] and asset['name'].endswith(ext):
                    download_url = asset['browser_download_url']
                    break

            if not download_url:
                logger.error(f"Could not find suitable Hamlib download for this platform")
                return None

            # Download the file
            download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
            os.makedirs(download_dir, exist_ok=True)

            file_name = os.path.join(download_dir, os.path.basename(download_url))
            logger.info(f"Downloading Hamlib from {download_url}")

            if HAS_REQUESTS:
                import requests
                with requests.get(download_url, stream=True) as r:
                    r.raise_for_status()
                    with open(file_name, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
            else:
                # Fall back to urllib if requests is not available
                urllib.request.urlretrieve(download_url, file_name)

            logger.info(f"Download completed: {file_name}")
            return file_name

        except Exception as e:
            logger.error(f"Error downloading Hamlib: {e}")
            return None

    def _extract_hamlib(self, file_path: str, dest_dir: str) -> Optional[str]:
        """
        Extract downloaded Hamlib archive to destination directory.

        Args:
            file_path (str): Path to the downloaded archive
            dest_dir (str): Destination directory

        Returns:
            Optional[str]: Path to the extracted directory or None if failed
        """
        try:
            logger.info(f"Extracting {file_path} to {dest_dir}")

            # Clear destination directory if it exists
            if os.path.exists(dest_dir):
                for item in os.listdir(dest_dir):
                    item_path = os.path.join(dest_dir, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)

            # Extract the archive
            if file_path.endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(dest_dir)
            elif file_path.endswith('.tar.gz'):
                with tarfile.open(file_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(dest_dir)            # Find the extracted directory (some archives have a root directory)
            extracted_dir = dest_dir
            contents = os.listdir(dest_dir)
            if len(contents) == 1 and os.path.isdir(os.path.join(dest_dir, contents[0])):
                extracted_dir = os.path.join(dest_dir, contents[0])

            # Clean up the downloads folder
            download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
            if os.path.exists(download_dir):
                try:
                    shutil.rmtree(download_dir)
                    logger.info(f"Cleaned up downloads directory: {download_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up downloads directory: {e}")

            logger.info(f"Extraction completed to {extracted_dir}")
            return extracted_dir

        except Exception as e:
            logger.error(f"Error extracting Hamlib: {e}")
            return None
