#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audio Manager module for the RigRanger Server.

This module provides the AudioManager class, which is responsible for managing
audio devices and streaming audio between the server and clients.
"""

import os
import sys
import time
import asyncio
import logging
import threading
from typing import Dict, List, Optional, Union, Any, Callable

logger = logging.getLogger("rig_ranger.audio")

class AudioManager:
    """
    A utility class for managing audio devices and streaming audio.

    This class is responsible for:
    - Enumerating available audio devices
    - Configuring audio input/output
    - Streaming audio data to/from clients
    - Processing audio for radio operations
    """

    def __init__(self):
        """Initialize the AudioManager."""
        self.enabled = False
        self.input_device = "default"
        self.output_device = "default"
        self.sample_rate = 48000
        self.channels = 1
        self.input_stream = None
        self.output_stream = None
        self.audio_thread = None
        self.running = False
        self.clients = set()
        self.lock = threading.Lock()
        self.event_callbacks = {
            'status': [],
            'data': [],
            'debug': []
        }

        # Try to import pyaudio
        self.pyaudio_available = False
        try:
            import pyaudio
            self.pyaudio = pyaudio
            self.pa = pyaudio.PyAudio()
            self.pyaudio_available = True
        except ImportError:
            logger.warning("PyAudio not available. Audio functionality will be limited.")
            self.pa = None

    def on(self, event: str, callback: Callable) -> None:
        """
        Register an event callback.

        Args:
            event (str): Event name ('status', 'data', 'debug')
            callback (callable): Function to call when the event occurs
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

    def get_devices(self) -> List[Dict[str, Any]]:
        """
        Get a list of available audio devices.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries with device information
        """
        devices = []

        if not self.pyaudio_available:
            return devices

        try:
            # Get information about audio devices
            device_count = self.pa.get_device_count()
            default_input = self.pa.get_default_input_device_info()['index']
            default_output = self.pa.get_default_output_device_info()['index']

            for i in range(device_count):
                try:
                    device_info = self.pa.get_device_info_by_index(i)

                    # Create a sanitized version of the device info
                    device = {
                        'index': device_info['index'],
                        'name': device_info['name'],
                        'max_input_channels': device_info['maxInputChannels'],
                        'max_output_channels': device_info['maxOutputChannels'],
                        'default_sample_rate': device_info['defaultSampleRate'],
                        'is_default_input': device_info['index'] == default_input,
                        'is_default_output': device_info['index'] == default_output
                    }

                    devices.append(device)
                except Exception as e:
                    logger.debug(f"Error getting info for device {i}: {e}")
        except Exception as e:
            logger.error(f"Error enumerating audio devices: {e}")

        return devices

    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure the AudioManager with the specified configuration.

        Args:
            config (Dict[str, Any]): Configuration options for audio

        Returns:
            bool: True if configured successfully, False otherwise
        """
        try:
            self.enabled = config.get('enabled', False)

            if not self.enabled:
                logger.info("Audio disabled by configuration")
                return True

            if not self.pyaudio_available:
                logger.warning("Cannot enable audio: PyAudio not available")
                self.enabled = False
                return False

            self.input_device = config.get('input_device', 'default')
            self.output_device = config.get('output_device', 'default')
            self.sample_rate = int(config.get('sample_rate', 48000))
            self.channels = int(config.get('channels', 1))

            logger.info(f"Audio configured: input={self.input_device}, "
                       f"output={self.output_device}, "
                       f"sample_rate={self.sample_rate}, "
                       f"channels={self.channels}")

            # Emit status event
            self.emit('status', {
                'status': 'configured',
                'enabled': self.enabled,
                'input_device': self.input_device,
                'output_device': self.output_device,
                'sample_rate': self.sample_rate,
                'channels': self.channels
            })

            return True
        except Exception as e:
            logger.error(f"Error configuring audio: {e}")
            self.emit('status', {
                'status': 'error',
                'message': f"Error configuring audio: {str(e)}"
            })
            return False

    def start(self) -> bool:
        """
        Start audio processing.

        Returns:
            bool: True if started successfully, False otherwise
        """
        if not self.enabled or not self.pyaudio_available:
            return False

        if self.running:
            return True

        try:
            # Get device indices
            input_idx = self._get_device_index(self.input_device, 'input')
            output_idx = self._get_device_index(self.output_device, 'output')

            if input_idx is None or output_idx is None:
                logger.error("Invalid audio devices")
                return False

            # Start audio processing thread
            self.running = True
            self.audio_thread = threading.Thread(target=self._audio_process, daemon=True)
            self.audio_thread.start()

            logger.info("Audio processing started")
            self.emit('status', {
                'status': 'started',
                'message': 'Audio processing started'
            })

            return True

        except Exception as e:
            logger.error(f"Error starting audio: {e}")
            self.emit('status', {
                'status': 'error',
                'message': f"Error starting audio: {str(e)}"
            })
            return False

    def stop(self) -> None:
        """Stop audio processing."""
        if not self.running:
            return

        try:
            # Stop the audio processing
            self.running = False

            # Wait for thread to end
            if self.audio_thread and self.audio_thread.is_alive():
                self.audio_thread.join(timeout=2)

            # Close streams
            if self.input_stream:
                self.input_stream.stop_stream()
                self.input_stream.close()
                self.input_stream = None

            if self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
                self.output_stream = None

            logger.info("Audio processing stopped")
            self.emit('status', {
                'status': 'stopped',
                'message': 'Audio processing stopped'
            })

        except Exception as e:
            logger.error(f"Error stopping audio: {e}")

    def add_client(self, client_id: str) -> None:
        """
        Add a client to receive audio.

        Args:
            client_id (str): Client identifier
        """
        with self.lock:
            self.clients.add(client_id)
            logger.debug(f"Added audio client: {client_id}")

    def remove_client(self, client_id: str) -> None:
        """
        Remove a client from receiving audio.

        Args:
            client_id (str): Client identifier
        """
        with self.lock:
            if client_id in self.clients:
                self.clients.remove(client_id)
                logger.debug(f"Removed audio client: {client_id}")

    def send_audio(self, audio_data: bytes, client_id: Optional[str] = None) -> None:
        """
        Send audio data to clients.

        Args:
            audio_data (bytes): Audio data to send
            client_id (str, optional): Specific client to send to, or None for all
        """
        if not self.running:
            return

        try:
            # Emit to specific client or all clients
            if client_id:
                self.emit('data', {
                    'client': client_id,
                    'data': audio_data
                })
            else:
                with self.lock:
                    for client in self.clients:
                        self.emit('data', {
                            'client': client,
                            'data': audio_data
                        })
        except Exception as e:
            logger.error(f"Error sending audio: {e}")

    def _get_device_index(self, device: Union[str, int], direction: str) -> Optional[int]:
        """
        Get the device index for an audio device.

        Args:
            device (Union[str, int]): Device name or index
            direction (str): 'input' or 'output'

        Returns:
            Optional[int]: Device index or None if not found
        """
        if not self.pa:
            return None

        # If it's already an integer, use it directly
        if isinstance(device, int):
            return device

        # If it's "default", use the default device
        if device == "default":
            try:
                if direction == "input":
                    return self.pa.get_default_input_device_info()['index']
                else:
                    return self.pa.get_default_output_device_info()['index']
            except Exception as e:
                logger.error(f"Error getting default {direction} device: {e}")
                return None

        # Otherwise, search by name
        try:
            for i in range(self.pa.get_device_count()):
                device_info = self.pa.get_device_info_by_index(i)
                if device in device_info['name']:
                    # Check if the device supports the requested direction
                    if direction == "input" and device_info['maxInputChannels'] > 0:
                        return i
                    elif direction == "output" and device_info['maxOutputChannels'] > 0:
                        return i
        except Exception as e:
            logger.error(f"Error finding device {device}: {e}")

        return None

    def _audio_process(self) -> None:
        """Audio processing thread."""
        if not self.pa:
            return

        try:
            input_idx = self._get_device_index(self.input_device, 'input')
            output_idx = self._get_device_index(self.output_device, 'output')

            # Create input stream
            self.input_stream = self.pa.open(
                format=self.pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=input_idx,
                frames_per_buffer=1024,
                stream_callback=self._input_callback
            )

            # Create output stream
            self.output_stream = self.pa.open(
                format=self.pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                output_device_index=output_idx,
                frames_per_buffer=1024
            )

            # Start streams
            self.input_stream.start_stream()
            self.output_stream.start_stream()

            # Keep running until stopped
            while self.running:
                time.sleep(0.1)

        except Exception as e:
            logger.error(f"Error in audio process: {e}")
            self.emit('status', {
                'status': 'error',
                'message': f"Error in audio process: {str(e)}"
            })
            self.running = False

    def _input_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio input."""
        if status:
            logger.debug(f"Audio input status: {status}")

        # Send audio data to clients
        self.send_audio(in_data)

        # Continue streaming
        return (None, self.pyaudio.paContinue)

    def process_audio_data(self, audio_data: bytes) -> None:
        """
        Process incoming audio data from a client.

        Args:
            audio_data (bytes): Audio data to process
        """
        if not self.running or not self.output_stream:
            return

        try:
            # Send to output device
            self.output_stream.write(audio_data)
        except Exception as e:
            logger.error(f"Error processing audio data: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the AudioManager.

        Returns:
            Dict[str, Any]: Status information
        """
        return {
            'enabled': self.enabled,
            'running': self.running,
            'pyaudio_available': self.pyaudio_available,
            'input_device': self.input_device,
            'output_device': self.output_device,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'client_count': len(self.clients)
        }
