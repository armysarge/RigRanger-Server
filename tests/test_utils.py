#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RigRanger Server - Unit Tests for Utility Functions

This file contains unit tests for the utility functions in utils.py.
"""

import os
import sys
import json
import unittest
import tempfile
from unittest.mock import MagicMock, patch

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rigranger_server.utils import find_available_serial_ports, get_hamlib_model_list, get_ip_addresses, load_config


class TestUtils(unittest.TestCase):
    """Test cases for utility functions."""

    @patch('serial.tools.list_ports.comports')
    def test_find_available_serial_ports_with_pyserial(self, mock_comports):
        """Test finding serial ports using pyserial."""
        # Mock a serial port
        mock_port = MagicMock()
        mock_port.device = '/dev/ttyUSB0'
        mock_port.description = 'USB Serial Device'

        # Set up the mock to return a list with our mock port
        mock_comports.return_value = [mock_port]

        # Call the function
        ports = find_available_serial_ports()

        # Check that it returns the expected result
        self.assertEqual(len(ports), 1)
        self.assertEqual(ports[0]['device'], '/dev/ttyUSB0')
        self.assertEqual(ports[0]['description'], 'USB Serial Device')

    @patch('subprocess.run')
    def test_get_hamlib_model_list_success(self, mock_run):
        """Test getting Hamlib model list when rigctl succeeds."""
        # Mock subprocess.run to return a sample output
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """Hamlib 4.4 supported models
1	Dummy
2	NET rigctl
3073	IC-7300
"""
        mock_run.return_value = mock_process

        # Call the function
        models = get_hamlib_model_list()

        # Check that it returns the expected results
        self.assertEqual(len(models), 3)
        self.assertEqual(models[0]['id'], 1)
        self.assertEqual(models[0]['name'], 'Dummy')
        self.assertEqual(models[2]['id'], 3073)
        self.assertEqual(models[2]['name'], 'IC-7300')

    @patch('subprocess.run')
    def test_get_hamlib_model_list_failure(self, mock_run):
        """Test getting Hamlib model list when rigctl fails."""
        # Mock subprocess.run to raise an exception
        mock_run.side_effect = Exception("Command failed")

        # Call the function
        models = get_hamlib_model_list()

        # Check that it returns the fallback list
        self.assertTrue(len(models) > 0)
        # Check that certain common models are in the fallback list
        model_ids = [model['id'] for model in models]
        self.assertIn(1, model_ids)  # Dummy
        self.assertIn(3073, model_ids)  # IC-7300

    @patch('socket.gethostname')
    @patch('socket.gethostbyname')
    def test_get_ip_addresses(self, mock_gethostbyname, mock_gethostname):
        """Test getting IP addresses."""
        # Mock socket functions
        mock_gethostname.return_value = 'testhost'
        mock_gethostbyname.return_value = '192.168.1.100'

        # Call the function
        ips = get_ip_addresses()

        # Check that it returns at least one IP
        self.assertTrue(len(ips) > 0)
        # Check that the expected IP is in the list
        self.assertIn('192.168.1.100', ips)

    def test_load_config_default(self):
        """Test loading the default configuration."""
        # Call the function with no config path
        config = load_config()

        # Check that it returns the default config
        self.assertEqual(config['server']['port'], 8080)
        self.assertEqual(config['hamlib']['model'], 1)
        self.assertEqual(config['audio']['enabled'], False)
        self.assertEqual(config['logging']['level'], 'info')

    def test_load_config_from_file(self):
        """Test loading configuration from a file."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            json.dump({
                'server': {
                    'port': 9090
                },
                'hamlib': {
                    'model': 3073
                }
            }, f)
            config_path = f.name

        try:
            # Call the function with the temp file path
            config = load_config(config_path)

            # Check that it merges the config correctly
            self.assertEqual(config['server']['port'], 9090)  # From file
            self.assertEqual(config['hamlib']['model'], 3073)  # From file
            self.assertEqual(config['audio']['enabled'], False)  # Default
            self.assertEqual(config['logging']['level'], 'info')  # Default
        finally:
            # Clean up the temporary file
            os.unlink(config_path)


if __name__ == "__main__":
    unittest.main()
