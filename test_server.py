#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for RigRanger Server Python Implementation.

This script tests the basic functionality of the RigRanger Server
by simulating client connections and commands.
"""

import sys
import time
import socket
import socketio
import threading
import argparse
import json
from urllib.parse import urlparse

# Test configuration
DEFAULT_SERVER_URL = "http://localhost:8080"
DEFAULT_TIMEOUT = 10  # seconds

class RigRangerTester:
    """Test client for RigRanger Server."""

    def __init__(self, server_url, timeout=DEFAULT_TIMEOUT, verbose=False):
        """Initialize the tester with server URL and timeout."""
        self.server_url = server_url
        self.timeout = timeout
        self.verbose = verbose
        self.client = socketio.Client()
        self.connected = False
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []

        # Parse server URL for HTTP test
        url_parts = urlparse(server_url)
        self.host = url_parts.hostname or 'localhost'
        self.port = url_parts.port or 8080

    def log(self, message):
        """Print log message if verbose is enabled."""
        if self.verbose:
            print(f"[TEST] {message}")

    def setup(self):
        """Set up event handlers."""
        @self.client.event
        def connect():
            self.connected = True
            self.log("Connected to server")

        @self.client.event
        def disconnect():
            self.connected = False
            self.log("Disconnected from server")

        @self.client.event
        def server_status(data):
            self.log(f"Server status: {data}")

        @self.client.event
        def hamlib_status(data):
            self.log(f"Hamlib status: {data}")

        @self.client.event
        def hamlib_data(data):
            self.log(f"Hamlib data: {data}")

    def connect_to_server(self):
        """Connect to the RigRanger Server."""
        try:
            self.client.connect(
                self.server_url,
                transports=['websocket'],
                wait_timeout=self.timeout
            )
            return True
        except Exception as e:
            self.record_result("Connect to server", False, str(e))
            return False

    def disconnect(self):
        """Disconnect from the server."""
        if self.connected:
            self.client.disconnect()

    def record_result(self, test_name, passed, message=""):
        """Record test result."""
        if passed:
            self.tests_passed += 1
            status = "PASSED"
        else:
            self.tests_failed += 1
            status = "FAILED"

        self.test_results.append({
            "name": test_name,
            "status": status,
            "message": message
        })

        # Print result immediately
        color = "\033[92m" if passed else "\033[91m"  # Green for pass, red for fail
        end_color = "\033[0m"
        print(f"{color}[{status}]{end_color} {test_name}{': ' + message if message and not passed else ''}")

    def test_http_connection(self):
        """Test HTTP connection to the server."""
        test_name = "HTTP Connection"
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(self.timeout)
            conn.connect((self.host, self.port))
            conn.send(b"GET /status HTTP/1.1\r\nHost: " + self.host.encode() + b"\r\n\r\n")
            response = conn.recv(4096)
            conn.close()

            if response and b"200 OK" in response:
                self.record_result(test_name, True)
                return True
            else:
                self.record_result(test_name, False, "Invalid response")
                return False
        except Exception as e:
            self.record_result(test_name, False, str(e))
            return False

    def test_socket_connection(self):
        """Test Socket.IO connection to the server."""
        test_name = "Socket.IO Connection"
        if not self.connected:
            if not self.connect_to_server():
                self.record_result(test_name, False, "Failed to connect")
                return False

        self.record_result(test_name, self.connected)
        return self.connected

    def test_hamlib_dummy(self):
        """Test Hamlib dummy device functionality."""
        test_name = "Hamlib Dummy Test"
        if not self.connected:
            if not self.connect_to_server():
                self.record_result(test_name, False, "Not connected to server")
                return False

        try:
            # Call the get_frequency function
            response = self.client.call(
                "hamlib_function",
                {"function": "get_frequency", "args": []},
                timeout=self.timeout
            )

            if response and response.get("success"):
                self.record_result(test_name, True)
                return True
            else:
                error = response.get("error", "Unknown error") if response else "No response"
                self.record_result(test_name, False, error)
                return False
        except Exception as e:
            self.record_result(test_name, False, str(e))
            return False

    def test_set_frequency(self):
        """Test setting and getting frequency."""
        test_name = "Set/Get Frequency"
        if not self.connected:
            if not self.connect_to_server():
                self.record_result(test_name, False, "Not connected to server")
                return False

        try:
            # Set frequency to 14.200 MHz
            set_freq_response = self.client.call(
                "hamlib_function",
                {"function": "set_frequency", "args": [14200000]},
                timeout=self.timeout
            )

            if not set_freq_response or not set_freq_response.get("success"):
                error = set_freq_response.get("error", "Unknown error") if set_freq_response else "No response"
                self.record_result(test_name, False, f"Failed to set frequency: {error}")
                return False

            # Get frequency and verify
            get_freq_response = self.client.call(
                "hamlib_function",
                {"function": "get_frequency", "args": []},
                timeout=self.timeout
            )

            if not get_freq_response or not get_freq_response.get("success"):
                error = get_freq_response.get("error", "Unknown error") if get_freq_response else "No response"
                self.record_result(test_name, False, f"Failed to get frequency: {error}")
                return False

            # Check if the frequency is approximately what we set
            # Hamlib dummy might not return exactly the same value
            freq = get_freq_response.get("data", 0)
            if abs(freq - 14200000) < 1000:  # Within 1 kHz
                self.record_result(test_name, True)
                return True
            else:
                self.record_result(test_name, False, f"Frequency mismatch: set 14200000, got {freq}")
                return False
        except Exception as e:
            self.record_result(test_name, False, str(e))
            return False

    def test_set_mode(self):
        """Test setting and getting mode."""
        test_name = "Set/Get Mode"
        if not self.connected:
            if not self.connect_to_server():
                self.record_result(test_name, False, "Not connected to server")
                return False

        try:
            # Set mode to USB
            set_mode_response = self.client.call(
                "hamlib_function",
                {"function": "set_mode", "args": ["USB", 2700]},
                timeout=self.timeout
            )

            if not set_mode_response or not set_mode_response.get("success"):
                error = set_mode_response.get("error", "Unknown error") if set_mode_response else "No response"
                self.record_result(test_name, False, f"Failed to set mode: {error}")
                return False

            # Get mode and verify
            get_mode_response = self.client.call(
                "hamlib_function",
                {"function": "get_mode", "args": []},
                timeout=self.timeout
            )

            if not get_mode_response or not get_mode_response.get("success"):
                error = get_mode_response.get("error", "Unknown error") if get_mode_response else "No response"
                self.record_result(test_name, False, f"Failed to get mode: {error}")
                return False

            # Check if the mode is what we set
            mode_data = get_mode_response.get("data", {})
            mode = mode_data.get("mode", "")

            if mode == "USB":
                self.record_result(test_name, True)
                return True
            else:
                self.record_result(test_name, False, f"Mode mismatch: set USB, got {mode}")
                return False
        except Exception as e:
            self.record_result(test_name, False, str(e))
            return False

    def run_all_tests(self):
        """Run all tests."""
        print("\n==========================================")
        print("  RigRanger Server - Test Suite")
        print("==========================================\n")

        # Run tests
        self.test_http_connection()
        self.test_socket_connection()

        if self.connected:
            self.test_hamlib_dummy()
            self.test_set_frequency()
            self.test_set_mode()

        # Disconnect from server
        self.disconnect()

        # Print summary
        print("\n==========================================")
        print("  Test Summary")
        print("==========================================")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {self.tests_failed}")
        print(f"Total tests:  {self.tests_passed + self.tests_failed}")
        print("==========================================\n")

        return self.tests_failed == 0

def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description="Test RigRanger Server functionality")
    parser.add_argument("--url", default=DEFAULT_SERVER_URL,
                        help=f"Server URL (default: {DEFAULT_SERVER_URL})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose output")

    args = parser.parse_args()

    tester = RigRangerTester(args.url, args.timeout, args.verbose)
    tester.setup()

    # Run tests
    success = tester.run_all_tests()

    # Return exit code based on test results
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
