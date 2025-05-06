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
import serial.tools.list_ports
from typing import Dict, List, Any, Optional, Tuple
from .config import DEFAULT_CONFIG, get_default_config_path, save_config, load_config

# Try to import AudioManager, but don't fail if it's not available
AudioManager = None
try:
    from .audio_manager import AudioManager
except ImportError:
    logger = logging.getLogger("rig_ranger.wizard")
    logger.warning("Could not import AudioManager. Audio features will be disabled.")

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
    # Consider a device as an input device if it has at least 1 input channel
    input_devices = [d for d in all_devices if d.get('max_input_channels', 0) > 0]
    logger.debug(f"Found {len(input_devices)} input devices before filtering")

    # Filter out duplicates based on name but keep the one with more channels
    # or the default device if channel counts are equal
    unique_devices = []
    seen_names = {}  # name -> (device, channels)

    for device in input_devices:
        name = device.get('name', '')
        channels = device.get('max_input_channels', 0)

        if name:
            if name not in seen_names:
                seen_names[name] = (device, channels)
            else:
                prev_device, prev_channels = seen_names[name]
                # Replace if this device has more channels or is default
                if channels > prev_channels or (channels == prev_channels and device.get('is_default_input')):
                    seen_names[name] = (device, channels)

    # Convert back to list
    unique_devices = [device for device, _ in seen_names.values()]
    logger.debug(f"Found {len(unique_devices)} unique input devices after filtering")

    # Sort devices: default first, then by name
    unique_devices.sort(key=lambda d: (not d.get('is_default_input', False), d.get('name', '')))

    return unique_devices

def get_output_devices(audio_manager) -> List[Dict[str, Any]]:
    """Get a filtered list of output devices without duplicates."""
    all_devices = audio_manager.get_devices()
    # Consider a device as an output device if it has at least 1 output channel
    output_devices = [d for d in all_devices if d.get('max_output_channels', 0) > 0]
    logger.debug(f"Found {len(output_devices)} output devices before filtering")

    # Filter out duplicates based on name but keep the one with more channels
    # or the default device if channel counts are equal
    unique_devices = []
    seen_names = {}  # name -> (device, channels)

    for device in output_devices:
        name = device.get('name', '')
        channels = device.get('max_output_channels', 0)

        if name:
            if name not in seen_names:
                seen_names[name] = (device, channels)
            else:
                prev_device, prev_channels = seen_names[name]
                # Replace if this device has more channels or is default
                if channels > prev_channels or (channels == prev_channels and device.get('is_default_output')):
                    seen_names[name] = (device, channels)

    # Convert back to list
    unique_devices = [device for device, _ in seen_names.values()]
    logger.debug(f"Found {len(unique_devices)} unique output devices after filtering")

    # Sort devices: default first, then by name
    unique_devices.sort(key=lambda d: (not d.get('is_default_output', False), d.get('name', '')))

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
    if not audio_manager or not audio_manager.pyaudio_available:
        logger.warning("PyAudio not available - audio will be disabled")
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

    # Get all devices first
    all_devices = audio_manager.get_devices()
    if not all_devices:
        print("\nNo audio devices were detected. Audio support will be disabled.")
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

    if not input_devices:
        print("\nNo input devices found. Using system default.")
        input_device = None
    else:
        print_device_list(input_devices, 'input')
        input_device = select_device(input_devices, "Select input device number:", True)

    # Get and display output devices
    print_section("Output Device Selection")
    output_devices = get_output_devices(audio_manager)

    if not output_devices:
        print("\nNo output devices found. Using system default.")
        output_device = None
    else:
        print_device_list(output_devices, 'output')
        output_device = select_device(output_devices, "Select output device number:", True)

    # If no devices were selected, disable audio
    if not input_device and not output_device:
        print("\nNo audio devices selected. Audio support will be disabled.")
        return {
            "enabled": False,
            "input_device": "default",
            "output_device": "default",
            "sample_rate": 48000,
            "channels": 1
        }

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

def get_serial_devices() -> List[str]:
    """
    Get a list of available serial devices.

    Returns:
        List of serial device paths
    """
    try:
        return [port.device for port in serial.tools.list_ports.comports()]
    except Exception as e:
        logger.error(f"Error scanning for serial devices: {e}")
        return []

def run_config_wizard(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Run the configuration wizard.

    Args:
        config_path: Optional path to configuration file

    Returns:
        Dictionary containing configuration
    """
    if not config_path:
        config_path = get_default_config_path()

    # Start with default config
    config = DEFAULT_CONFIG.copy()

    # Create config directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)

    clear_screen()
    print_header("RigRanger Server Configuration Wizard")

    # Server configuration
    print_section("Server Configuration")

    port = input(f"\nEnter server port (current: {config['server']['port']}, Enter to keep): ")
    if port.strip():
        try:
            config['server']['port'] = int(port)
        except ValueError:
            print("Invalid port number, keeping current value.")

    host = input(f"\nEnter server host (current: {config['server']['host']}, Enter to keep): ")
    if host.strip():
        config['server']['host'] = host

    # Hamlib configuration
    print_section("Hamlib Configuration")

    # Show popular radio models
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
    model_ids = [m[0] for m in popular_models]
    for model_id, model_name in popular_models:
        print(f"{model_id:<10} {model_name:<30}")

    while True:
        model = input(f"\nEnter radio model number (current: {config['hamlib']['model']}, Enter to keep): ")
        if not model.strip():
            break
        try:
            model_num = int(model)
            if model_num in model_ids:
                config['hamlib']['model'] = model_num
                break
            else:
                print("Warning: Model ID not in the list of popular models.")
                confirm = input("Are you sure you want to use this model? (y/n): ").strip().lower()
                if confirm == 'y':
                    config['hamlib']['model'] = model_num
                    break
        except ValueError:
            print("Invalid model number, please enter a valid number.")

    current_device_str = config['hamlib']['device'] if config['hamlib']['device'] else "Not set"

    # Show available serial devices
    print("\nScanning for serial devices...")
    devices = get_serial_devices()
    if devices:
        print("\nAvailable serial devices:")
        for i, device in enumerate(devices):
            print(f"{i}: {device}")
    else:
        print("\nNo serial devices detected.")

    while True:
        device_input = input(f"\nEnter radio device path or number (current: {current_device_str}, Enter to keep): ")
        if not device_input.strip():
            break

        try:
            # Check if input is a number (index)
            idx = int(device_input)
            if 0 <= idx < len(devices):
                config['hamlib']['device'] = devices[idx]
                break
            else:
                print(f"Please enter a number between 0 and {len(devices)-1}, or a valid device path.")
        except ValueError:
            # Input is not a number, check if it's a valid device path
            if device_input in devices:
                config['hamlib']['device'] = device_input
                break
            else:
                print("Warning: Device path not found in available devices.")
                confirm = input("Are you sure you want to use this device path? (y/n): ").strip().lower()
                if confirm == 'y':
                    config['hamlib']['device'] = device_input
                    break    # Audio configuration
    print_section("Audio Configuration")

    # Check if AudioManager is available
    if AudioManager is None:
        print("\nPyAudio is not installed. Audio support will be disabled.")
        config['audio'] = {
            "enabled": False,
            "input_device": "default",
            "output_device": "default",
            "sample_rate": 48000,
            "channels": 1
        }
    else:
        try:
            audio_manager = AudioManager()
        except Exception as e:
            print(f"\nError initializing audio: {e}. Audio support will be disabled.")
            config['audio'] = {
                "enabled": False,
                "input_device": "default",
                "output_device": "default",
                "sample_rate": 48000,
                "channels": 1
            }
            return config

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

    # Ask user if they want to save the configuration
    while True:
        save_prompt = input("\nDo you want to save this configuration? (y/n): ").strip().lower()
        if save_prompt in ('y', 'n'):
            break
        print("Please enter 'y' or 'n'.")

    if save_prompt == 'y':
        # Ask for save location
        suggested_path = os.path.abspath(config_path)
        save_path = input(f"\nEnter path to save configuration (Enter to use {suggested_path}): ").strip()

        if not save_path:
            save_path = suggested_path

        # Ensure the directory exists
        save_dir = os.path.dirname(os.path.abspath(save_path))
        os.makedirs(save_dir, exist_ok=True)

        # Save configuration using the config module's save_config function
        if save_config(config, save_path):
            print(f"\nConfiguration saved to {save_path}")
            # Verify the save by attempting to load it
            try:
                loaded_config = load_config(save_path)
                if loaded_config == config:
                    print("Configuration verified successfully.")
                else:
                    print("Warning: Saved configuration may not be correct. Please verify the settings.")
            except Exception as e:
                print(f"Warning: Could not verify saved configuration: {e}")
        else:
            print("\nFailed to save configuration")
    else:
        print("\nConfiguration was not saved. Using settings in memory only.")

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
