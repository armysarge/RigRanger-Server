#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RigRanger Server - Unit Tests for HamlibManager

This file contains unit tests for the HamlibManager class.
"""

import os
import sys
import unittest
import tempfile
import json
from unittest.mock import MagicMock, patch

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rigranger_server.hamlib_manager import HamlibManager


class TestHamlibManager(unittest.TestCase):
    """Test cases for the HamlibManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.hamlib = HamlibManager()
        # Mock the socket for testing
        self.hamlib.socket = MagicMock()
        self.hamlib.connected = True

    @patch('subprocess.Popen')
    def test_start_rigctld(self, mock_popen):
        """Test starting the rigctld process."""
        # Set up the mock to return a process with poll() that returns None (still running)
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        # Mock the connect method
        self.hamlib.connect = MagicMock(return_value=True)
        self.hamlib.binary_path = "mock_path_to_rigctld"

        # Test with minimal config
        result = self.hamlib.start_rigctld({"model": 1})

        # Check that the method returns True
        self.assertTrue(result)

        # Check that Popen was called with the expected arguments
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        self.assertEqual(args[0], "mock_path_to_rigctld")
        self.assertEqual(args[1], "-m")
        self.assertEqual(args[2], "1")

    def test_execute_command(self):
        """Test executing a command through the socket."""
        # Set up the mock socket
        self.hamlib.socket.sendall = MagicMock()
        self.hamlib.socket.recv = MagicMock(return_value=b"Test response\nRPRT 0")

        # Test the execute_command method
        response = self.hamlib.execute_command("\\get_freq")

        # Check that sendall was called with the correct command
        self.hamlib.socket.sendall.assert_called_once_with(b"\\get_freq\n")

        # Check that the response is what we expect
        self.assertEqual(response, "Test response\nRPRT 0")

    def test_get_frequency(self):
        """Test getting the radio frequency."""
        # Mock the execute_command method
        self.hamlib.execute_command = MagicMock(return_value="14250000\nRPRT 0")

        # Test the get_frequency method
        frequency = self.hamlib.get_frequency()

        # Check that execute_command was called with the correct command
        self.hamlib.execute_command.assert_called_once_with("\\get_freq")

        # Check that the frequency is what we expect
        self.assertEqual(frequency, 14250000.0)

    def test_set_frequency(self):
        """Test setting the radio frequency."""
        # Mock the execute_command method
        self.hamlib.execute_command = MagicMock(return_value="RPRT 0")

        # Test the set_frequency method
        result = self.hamlib.set_frequency(14250000.0)

        # Check that execute_command was called with the correct command
        self.hamlib.execute_command.assert_called_once_with("\\set_freq 14250000.0")

        # Check that the method returns True
        self.assertTrue(result)

    def test_get_mode(self):
        """Test getting the radio mode."""
        # Mock the execute_command method
        self.hamlib.execute_command = MagicMock(return_value="USB 2400\nRPRT 0")

        # Test the get_mode method
        mode = self.hamlib.get_mode()

        # Check that execute_command was called with the correct command
        self.hamlib.execute_command.assert_called_once_with("\\get_mode")

        # Check that the mode is what we expect
        self.assertEqual(mode, {"mode": "USB", "passband": 2400})

    def test_set_mode(self):
        """Test setting the radio mode."""
        # Mock the execute_command method
        self.hamlib.execute_command = MagicMock(return_value="RPRT 0")

        # Test the set_mode method
        result = self.hamlib.set_mode("USB", 2400)

        # Check that execute_command was called with the correct command
        self.hamlib.execute_command.assert_called_once_with("\\set_mode USB 2400")

        # Check that the method returns True
        self.assertTrue(result)

    def test_get_ptt(self):
        """Test getting the PTT status."""
        # Mock the execute_command method
        self.hamlib.execute_command = MagicMock(return_value="0\nRPRT 0")

        # Test the get_ptt method
        ptt = self.hamlib.get_ptt()

        # Check that execute_command was called with the correct command
        self.hamlib.execute_command.assert_called_once_with("\\get_ptt")

        # Check that the PTT status is what we expect (False for 0)
        self.assertFalse(ptt)

    def test_set_ptt(self):
        """Test setting the PTT status."""
        # Mock the execute_command method
        self.hamlib.execute_command = MagicMock(return_value="RPRT 0")

        # Test the set_ptt method (True)
        result_true = self.hamlib.set_ptt(True)

        # Check that execute_command was called with the correct command
        self.hamlib.execute_command.assert_called_once_with("\\set_ptt 1")

        # Check that the method returns True
        self.assertTrue(result_true)

        # Reset the mock
        self.hamlib.execute_command.reset_mock()

        # Test the set_ptt method (False)
        result_false = self.hamlib.set_ptt(False)

        # Check that execute_command was called with the correct command
        self.hamlib.execute_command.assert_called_once_with("\\set_ptt 0")

        # Check that the method returns True
        self.assertTrue(result_false)


if __name__ == "__main__":
    unittest.main()
