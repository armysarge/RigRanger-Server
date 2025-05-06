#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utility functions for the RigRanger Server.
"""

import os
import sys
import json
import socket
import platform
import subprocess
from typing import List, Dict, Any, Optional

def find_available_serial_ports() -> List[Dict[str, str]]:
    """
    Find available serial ports on the system.

    Returns:
        List[Dict[str, str]]: A list of dicts with 'device' and 'description' keys
    """
    ports = []

    try:
        import serial.tools.list_ports
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description
            })
    except ImportError:
        # Fall back to system-specific methods if pyserial is not available
        if sys.platform.startswith('win'):
            try:
                import winreg
                reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
                key = winreg.OpenKey(reg, r'HARDWARE\DEVICEMAP\SERIALCOMM')
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        ports.append({
                            'device': value,
                            'description': name
                        })
                        i += 1
                    except OSError:
                        break
            except:
                pass
        elif sys.platform.startswith('linux'):
            # Try to find serial devices on Linux
            devices = []
            for dev in os.listdir('/dev'):
                if dev.startswith('ttyS') or dev.startswith('ttyUSB') or dev.startswith('ttyACM'):
                    devices.append(f'/dev/{dev}')

            for device in devices:
                ports.append({
                    'device': device,
                    'description': device
                })
        elif sys.platform.startswith('darwin'):
            # Try to find serial devices on macOS
            devices = []
            for dev in os.listdir('/dev'):
                if dev.startswith('tty.') or dev.startswith('cu.'):
                    devices.append(f'/dev/{dev}')

            for device in devices:
                ports.append({
                    'device': device,
                    'description': device
                })

    return ports

def get_hamlib_model_list() -> List[Dict[str, Any]]:
    """
    Get a list of common Hamlib radio models.

    Returns:
        List[Dict[str, Any]]: A list of dicts with model info
    """
    # Try to run 'rigctl -l' to get a list of supported models
    models = []
    try:
        proc = subprocess.run(['rigctl', '-l'],
                               capture_output=True, text=True, check=False)

        if proc.returncode == 0:
            lines = proc.stdout.splitlines()

            # Parse the output
            for line in lines:
                if not line.strip() or line.startswith('Hamlib') or 'Backend' in line:
                    continue

                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    model_id, model_name = parts

                    try:
                        model_id = int(model_id)
                        models.append({
                            'id': model_id,
                            'name': model_name.strip()
                        })
                    except ValueError:
                        pass
    except Exception:
        # If we can't run rigctl, return a predefined list of common models
        models = [
            {'id': 1, 'name': 'Dummy'},
            {'id': 2, 'name': 'NET rigctl'},
            {'id': 1020, 'name': 'Yaesu FT-817'},
            {'id': 1021, 'name': 'Yaesu FT-857'},
            {'id': 1022, 'name': 'Yaesu FT-897'},
            {'id': 1023, 'name': 'Yaesu FT-100'},
            {'id': 1024, 'name': 'Yaesu FT-990'},
            {'id': 1026, 'name': 'Yaesu FT-747GX'},
            {'id': 1027, 'name': 'Yaesu FT-757GX'},
            {'id': 1028, 'name': 'Yaesu FT-757GXII'},
            {'id': 1029, 'name': 'Yaesu FT-767GX'},
            {'id': 1030, 'name': 'Yaesu FT-736R'},
            {'id': 1031, 'name': 'Yaesu FT-840'},
            {'id': 1032, 'name': 'Yaesu FT-890'},
            {'id': 1033, 'name': 'Yaesu FT-900'},
            {'id': 1034, 'name': 'Yaesu FT-920'},
            {'id': 1042, 'name': 'Yaesu FT-991'},
            {'id': 1043, 'name': 'Yaesu FT-891'},
            {'id': 1044, 'name': 'Yaesu FT-991A'},
            {'id': 1045, 'name': 'Yaesu FT-DX10'},
            {'id': 1046, 'name': 'Yaesu FT-710'},
            {'id': 103, 'name': 'Kenwood TS-850'},
            {'id': 204, 'name': 'Kenwood TS-950SDX'},
            {'id': 205, 'name': 'Kenwood TS-50S'},
            {'id': 206, 'name': 'Kenwood TS-60S'},
            {'id': 207, 'name': 'Kenwood TS-570D'},
            {'id': 208, 'name': 'Kenwood TS-870S'},
            {'id': 229, 'name': 'Kenwood TS-2000'},
            {'id': 231, 'name': 'Kenwood TS-590S'},
            {'id': 233, 'name': 'Kenwood TS-990S'},
            {'id': 3001, 'name': 'Icom IC-706'},
            {'id': 3002, 'name': 'Icom IC-706MkII'},
            {'id': 3003, 'name': 'Icom IC-706MkIIG'},
            {'id': 3005, 'name': 'Icom IC-7000'},
            {'id': 3006, 'name': 'Icom IC-7100'},
            {'id': 3073, 'name': 'Icom IC-7300'},
            {'id': 3074, 'name': 'Icom IC-7610'},
            {'id': 3075, 'name': 'Icom IC-7200'},
            {'id': 3076, 'name': 'Icom IC-9700'},
            {'id': 3077, 'name': 'Icom IC-705'},
            {'id': 3078, 'name': 'Icom IC-R30'},
            {'id': 3079, 'name': 'Icom IC-R8600'},
            {'id': 2301, 'name': 'Elecraft K2'},
            {'id': 2310, 'name': 'Elecraft K3'},
            {'id': 2311, 'name': 'Elecraft K3S'},
            {'id': 2312, 'name': 'Elecraft KX2'},
            {'id': 2313, 'name': 'Elecraft KX3'},
            {'id': 2314, 'name': 'Elecraft K4'},
        ]

    return models

def get_ip_addresses() -> List[str]:
    """
    Get all IP addresses for the current machine.

    Returns:
        List[str]: A list of IP addresses
    """
    ips = []

    try:
        # Get hostname
        hostname = socket.gethostname()

        # Get IP from hostname
        host_ip = socket.gethostbyname(hostname)
        if host_ip and host_ip != '127.0.0.1':
            ips.append(host_ip)

        # Try to get all network interfaces
        for iface in socket.getaddrinfo(socket.gethostname(), None):
            addr = iface[4][0]
            if addr != '127.0.0.1' and not addr.startswith('fe80::') and ':' not in addr:
                if addr not in ips:
                    ips.append(addr)
    except Exception:
        pass

    # If we couldn't find any IPs, use a more platform-specific approach
    if not ips:
        try:
            if platform.system() == 'Windows':
                # On Windows, use ipconfig
                output = subprocess.check_output(
                    'ipconfig', stderr=subprocess.STDOUT, universal_newlines=True)

                for line in output.split('\n'):
                    if 'IPv4 Address' in line:
                        ip = line.strip().split(':')[-1].strip()
                        if ip != '127.0.0.1' and ip not in ips:
                            ips.append(ip)
            else:
                # On Unix systems, try using 'ip' or 'ifconfig'
                try:
                    # Try 'ip' command first
                    output = subprocess.check_output(
                        ['ip', 'addr'], stderr=subprocess.STDOUT, universal_newlines=True)
                except:
                    # Fall back to 'ifconfig'
                    output = subprocess.check_output(
                        ['ifconfig'], stderr=subprocess.STDOUT, universal_newlines=True)

                import re
                # Look for IP addresses in the output
                for ip in re.findall(r'inet (?:addr:)?(\d+\.\d+\.\d+\.\d+)', output):
                    if ip != '127.0.0.1' and ip not in ips:
                        ips.append(ip)
        except Exception:
            pass

    # If we still don't have any IPs, default to localhost
    if not ips:
        ips.append('127.0.0.1')

    return ips

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.

    Args:
        config_path (str, optional): Path to the configuration file

    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    # Default configuration
    default_config = {
        "server": {
            "port": 8080,
            "host": "0.0.0.0",
            "static_files_path": "public"
        },
        "hamlib": {
            "model": 1,
            "device": None,
            "baud": 19200,
            "retry_interval": 5,
            "reconnect_attempts": 5
        },
        "audio": {
            "enabled": False,
            "input_device": "default",
            "output_device": "default",
            "sample_rate": 48000,
            "channels": 1
        },
        "logging": {
            "level": "info",
            "file": "rig_ranger_server.log",
            "console": True
        }
    }

    # If no config path specified, return default config
    if not config_path:
        return default_config

    try:
        with open(config_path, 'r') as f:
            user_config = json.load(f)

        # Merge user config with default config
        merged_config = default_config
        for section in user_config:
            if section in merged_config:
                if isinstance(merged_config[section], dict) and isinstance(user_config[section], dict):
                    # Deep merge for dictionaries
                    for key, value in user_config[section].items():
                        merged_config[section][key] = value
                else:
                    # Simple replacement for non-dict values
                    merged_config[section] = user_config[section]

        return merged_config
    except Exception as e:
        print(f"Error loading config file: {e}")
        return default_config
