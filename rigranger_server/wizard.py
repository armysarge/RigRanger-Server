#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration wizard for the RigRanger Server.

This module provides utilities for interactively configuring the RigRanger Server,
including selecting audio devices and setting up other configuration options.
"""

import os
import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("rig_ranger.wizard")

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {title} ".center(60, "="))
    print("=" * 60 + "\n")

def print_section(title: str):
    """Print a section title."""
    print("\n" + "-" * 60)
    print(f" {title} ")
    print("-" * 60)

def print_device_list(devices: List[Dict[str, Any]], device_type: str):
    """
    Print a formatted list of audio devices.

    Args:
        devices: List of device dictionaries
        device_type: 'input' or 'output'
    """
    if not devices:
        print(f"No {device_type} devices found.")
        return

    print(f"\nAvailable {device_type} devices:")
    print(f"{'#':<4} {'Name':<40} {'Channels':<10} {'Default':<8}")
    print("-" * 70)

    for i, device in enumerate(devices):
        is_default = ""
        if device_type == 'input' and device.get('is_default_input'):
            is_default = "✓"
        elif device_type == 'output' and device.get('is_default_output'):
            is_default = "✓"

        channels = device.get('max_input_channels', 0) if device_type == 'input' else device.get('max_output_channels', 0)

        print(f"{i:<4} {device.get('name', 'Unknown')[:38]:<40} {channels:<10} {is_default:<8}")

def get_input_devices(audio_manager) -> List[Dict[str, Any]]:
    """Get a filtered list of input devices without duplicates."""
    all_devices = audio_manager.get_devices()
    input_devices = [d for d in all_devices if d.get('max_input_channels', 0) > 0]

    # Filter out duplicates based on name
    unique_devices = []
    seen_names = set()

    for device in input_devices:
        name = device.get('name', '')
        if name and name not in seen_names:
            seen_names.add(name)
            unique_devices.append(device)

    return unique_devices

def get_output_devices(audio_manager) -> List[Dict[str, Any]]:
    """Get a filtered list of output devices without duplicates."""
    all_devices = audio_manager.get_devices()
    output_devices = [d for d in all_devices if d.get('max_output_channels', 0) > 0]

    # Filter out duplicates based on name
    unique_devices = []
    seen_names = set()

    for device in output_devices:
        name = device.get('name', '')
        if name and name not in seen_names:
            seen_names.add(name)
            unique_devices.append(device)

    return unique_devices

def select_device(devices: List[Dict[str, Any]], prompt: str, allow_default: bool = True) -> Optional[Dict[str, Any]]:
    """
    Let user select a device from a list.

    Args:
        devices: List of device dictionaries
        prompt: Text to show when prompting
        allow_default: Whether to allow selecting the default option

    Returns:
        The selected device or None if none selected
    """
    if not devices:
        return None

    while True:
        try:
            choice = input(f"\n{prompt} (0-{len(devices)-1}, d for default, q to disable): ").strip().lower()

            if choice == 'q':
                print("Device disabled.")
                return None

            if choice == 'd' and allow_default:
                # Find default device
                for device in devices:
                    if 'input' in prompt.lower() and device.get('is_default_input'):
                        print(f"Selected default device: {device.get('name', 'Unknown')}")
                        return device
                    elif 'output' in prompt.lower() and device.get('is_default_output'):
                        print(f"Selected default device: {device.get('name', 'Unknown')}")
                        return device

                print("No default device found, please select a device by number.")
                continue

            idx = int(choice)
            if 0 <= idx < len(devices):
                selected = devices[idx]
                print(f"Selected: {selected.get('name', 'Unknown')}")
                return selected
            else:
                print(f"Please enter a number between 0 and {len(devices)-1}, or 'd' for default.")
        except ValueError:
            print("Please enter a valid number, 'd' for default, or 'q' to disable.")

def configure_audio_wizard(audio_manager) -> Dict[str, Any]:
    """
    Interactive wizard for configuring audio devices.

    Args:
        audio_manager: An instance of AudioManager

    Returns:
        Dictionary with audio configuration
    """
    if not audio_manager.pyaudio_available:
        return {
            "enabled": False,
            "input_device": "default",
            "output_device": "default",
            "sample_rate": 48000,
            "channels": 1
        }

    clear_screen()
    print_header("RigRanger Server - Audio Configuration Wizard")

    print("""
This wizard will help you configure audio devices for RigRanger Server.
The server needs to know which audio devices to use to communicate with
the radio. These devices will be used for transmitting and receiving audio.

You can select input (microphone) and output (speaker) devices, or use
the default system devices.
""")

    # Ask if user wants to enable audio
    while True:
        enable = input("\nEnable audio support? (y/n): ").strip().lower()
        if enable in ('y', 'n'):
            break
        print("Please enter 'y' or 'n'.")

    if enable != 'y':
        print("\nAudio support disabled.")
        return {
            "enabled": False,
            "input_device": "default",
            "output_device": "default",
            "sample_rate": 48000,
            "channels": 1
        }

    # Get and display input devices
    print_section("Input Device Selection")
    input_devices = get_input_devices(audio_manager)
    print_device_list(input_devices, 'input')
    input_device = select_device(input_devices, "Select input device number:", True)

    # Get and display output devices
    print_section("Output Device Selection")
    output_devices = get_output_devices(audio_manager)
    print_device_list(output_devices, 'output')
    output_device = select_device(output_devices, "Select output device number:", True)

    # Configure sample rate
    print_section("Sample Rate Configuration")
    print("""
Common sample rates:
1. 48000 Hz (High quality, recommended)
2. 44100 Hz (CD quality)
3. 22050 Hz (Lower bandwidth)
4. 16000 Hz (Voice quality)
5. 8000 Hz (Low bandwidth)
""")

    sample_rate = 48000  # Default
    while True:
        try:
            rate_choice = input("\nSelect sample rate (1-5, Enter for default 48000 Hz): ").strip()
            if not rate_choice:
                break

            choice = int(rate_choice)
            if 1 <= choice <= 5:
                sample_rates = [48000, 44100, 22050, 16000, 8000]
                sample_rate = sample_rates[choice - 1]
                break
            else:
                print("Please enter a number between 1 and 5.")
        except ValueError:
            print("Please enter a valid number or press Enter for default.")

    # Configure channels
    print_section("Channel Configuration")
    print("""
Channel options:
1. Mono (1 channel, recommended for radio)
2. Stereo (2 channels)
""")

    channels = 1  # Default
    while True:
        try:
            channel_choice = input("\nSelect channels (1-2, Enter for default Mono): ").strip()
            if not channel_choice:
                break

            choice = int(channel_choice)
            if 1 <= choice <= 2:
                channels = choice
                break
            else:
                print("Please enter either 1 or 2.")
        except ValueError:
            print("Please enter a valid number or press Enter for default.")

    # Create configuration
    input_device_name = "default"
    if input_device:
        input_device_name = input_device.get('name', 'default')

    output_device_name = "default"
    if output_device:
        output_device_name = output_device.get('name', 'default')

    audio_config = {
        "enabled": True,
        "input_device": input_device_name,
        "output_device": output_device_name,
        "sample_rate": sample_rate,
        "channels": channels
    }

    print_section("Audio Configuration Summary")
    print(f"""
Audio Enabled: Yes
Input Device:  {input_device_name}
Output Device: {output_device_name}
Sample Rate:   {sample_rate} Hz
Channels:      {channels}
""")

    return audio_config

def run_config_wizard(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Run the complete configuration wizard.

    Args:
        config_path: Path to save the configuration file

    Returns:
        Dictionary with the complete configuration
    """
    # Import here to avoid circular imports
    from rigranger_server.audio_manager import AudioManager
    from rigranger_server.utils import load_config

    # Start with default config or load existing
    if config_path and os.path.exists(config_path):
        config = load_config(config_path)
        print(f"Loaded existing configuration from {config_path}")
    else:
        config = load_config()

    clear_screen()
    print_header("RigRanger Server - Configuration Wizard")

    print("""
Welcome to the RigRanger Server configuration wizard.
This wizard will help you set up the server configuration.

You can configure:
- Server settings (port, host)
- Hamlib radio settings (model, device)
- Audio settings (input/output devices)
""")

    # Server configuration
    print_section("Server Configuration")

    # Port configuration
    current_port = config.get('server', {}).get('port', 8080)
    while True:
        try:
            port_input = input(f"\nEnter server port (current: {current_port}, Enter to keep): ")
            if not port_input.strip():
                break

            port = int(port_input)
            if 1024 <= port <= 65535:
                config['server']['port'] = port
                break
            else:
                print("Port must be between 1024 and 65535.")
        except ValueError:
            print("Please enter a valid port number.")

    # Hamlib configuration
    print_section("Hamlib Radio Configuration")
    print("\nYou can configure your radio model and connection here.")
    print("For a complete list of supported radios, run: rigctl -l")    # Show popular radio models
    print("\nPopular Radio Models:")
    print(f"{'Model ID':<10} {'Radio':<30}")
    print("-" * 40)
    popular_models = [
        (1, "Hamlib Dummy"),
        (2, "NET rigctl"),
        (1020, "Yaesu FT-817"),
        (1021, "Yaesu FT-857"),
        (1022, "Yaesu FT-897"),
        (229, "Kenwood TS-2000"),
        (2311, "Elecraft K3S"),
        (3001, "Icom IC-706"),
        (3073, "Icom IC-7300"),
        (2037, "Kenwood TS-480")
    ]
    for model_id, model_name in popular_models:
        print(f"{model_id:<10} {model_name:<30}")

    # Radio model
    current_model = config.get('hamlib', {}).get('model', 1)
    while True:
        try:
            model_input = input(f"\nEnter radio model number (current: {current_model}, Enter to keep): ")
            if not model_input.strip():
                break

            model = int(model_input)
            if model >= 0:
                config['hamlib']['model'] = model
                break
            else:
                print("Model number must be a positive integer.")
        except ValueError:
            print("Please enter a valid model number.")    # Radio device
    current_device = config.get('hamlib', {}).get('device', None)
    current_device_str = current_device if current_device else "None (uses default)"

    print("\nRadio Device Path:")
    print("This is the serial port where your radio is connected.")
    print("Examples:")
    print("  Windows: COM3, COM4, etc.")
    print("  Linux: /dev/ttyUSB0, /dev/ttyS0, etc.")
    print("  macOS: /dev/cu.usbserial, etc.")
    print("Leave empty to use the default device.")

    # Show detected serial ports
    from rigranger_server.utils import find_available_serial_ports
    serial_ports = find_available_serial_ports()
    if serial_ports:
        print("\nDetected Serial Devices:")
        print(f"{'Device':<20} {'Description':<40}")
        print("-" * 60)
        for port in serial_ports:
            device = port.get('device', 'Unknown')
            description = port.get('description', 'Unknown')
            print(f"{device:<20} {description[:40]:<40}")
    else:
        print("\nNo serial devices detected.")

    device_input = input(f"\nEnter radio device path (current: {current_device_str}, Enter to keep): ")
    if device_input.strip():
        config['hamlib']['device'] = device_input

    # Audio configuration
    print_section("Audio Configuration")

    # Create temporary AudioManager to enumerate devices
    audio_manager = AudioManager()

    # Run audio wizard
    while True:
        run_wizard = input("\nRun audio configuration wizard? (y/n): ").strip().lower()
        if run_wizard in ('y', 'n'):
            break
        print("Please enter 'y' or 'n'.")

    if run_wizard == 'y':
        config['audio'] = configure_audio_wizard(audio_manager)
    else:
        print("\nSkipping audio configuration. Using existing settings.")

    # Save configuration if path provided
    if config_path:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"\nConfiguration saved to {config_path}")
        except Exception as e:
            print(f"\nError saving configuration: {e}")

    return config

def should_run_wizard(args) -> Tuple[bool, Optional[str]]:
    """
    Determine if the wizard should run based on command line arguments
    and configuration file existence.

    Args:
        args: Command line arguments

    Returns:
        Tuple of (should_run_wizard, config_path)
    """
    # If --wizard flag is present, always run wizard
    if hasattr(args, 'wizard') and args.wizard:
        return True, args.config

    # If config file is specified but doesn't exist, run wizard
    if hasattr(args, 'config') and args.config and not os.path.exists(args.config):
        print(f"Configuration file not found: {args.config}")
        print("Running configuration wizard to create a new configuration file.")
        return True, args.config

    # If not config file is specified and default doesn't exist, run wizard
    default_config = os.path.join(os.path.expanduser("~"), ".rigranger", "config.json")
    if not hasattr(args, 'config') or not args.config:
        if not os.path.exists(default_config):
            print(f"No configuration file found. Will use default settings.")
            print("You can run with --wizard flag to create a configuration file.")
            return False, None

    return False, args.config if hasattr(args, 'config') and args.config else None

if __name__ == "__main__":
    # Testing the wizard
    config = run_config_wizard("config_test.json")
    print("\nConfiguration:")
    print(json.dumps(config, indent=2))
