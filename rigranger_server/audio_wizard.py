#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audio Device Selection Wizard for RigRanger Server.

This module provides a user-friendly way to select audio devices for the RigRanger Server.
"""

import os
import sys
import json
import time
from typing import Dict, List, Optional, Union, Any, Tuple

def clear_screen() -> None:
    """Clear the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header() -> None:
    """Print the RigRanger Server wizard header."""
    clear_screen()
    print("=" * 70)
    print("                   RigRanger Server Audio Setup Wizard")
    print("=" * 70)
    print("This wizard will help you configure audio devices for your RigRanger Server.")
    print("The selected devices will be used for audio streaming to/from clients.")
    print()

def print_device_list(devices: List[Dict[str, Any]], device_type: str) -> None:
    """
    Print a list of audio devices.

    Args:
        devices: List of audio device dictionaries
        device_type: 'input' or 'output'
    """
    print(f"\nAvailable {device_type} devices:")
    print("-" * 70)

    # Filter devices based on type
    if device_type == 'input':
        filtered_devices = [d for d in devices if d['max_input_channels'] > 0]
    else:
        filtered_devices = [d for d in devices if d['max_output_channels'] > 0]

    # If no devices of this type, show message
    if not filtered_devices:
        print(f"No {device_type} devices found.")
        return

    # Print device list with index
    print(f"{'#':<3} {'Default':<10} {'Device Name':<50} {'Channels':<8}")
    print("-" * 70)

    for i, device in enumerate(filtered_devices):
        default_mark = "*" if (device_type == 'input' and device.get('is_default_input')) or \
                              (device_type == 'output' and device.get('is_default_output')) else ""

        channels = device.get('max_input_channels', 0) if device_type == 'input' else device.get('max_output_channels', 0)

        print(f"{i:<3} {default_mark:<10} {device['name'][:50]:<50} {channels:<8}")

    print()

def get_device_selection(devices: List[Dict[str, Any]], device_type: str) -> Tuple[Union[int, str], str]:
    """
    Get user selection for an audio device.

    Args:
        devices: List of audio device dictionaries
        device_type: 'input' or 'output'

    Returns:
        Tuple containing the device index/name and a description string
    """
    # Filter devices based on type
    if device_type == 'input':
        filtered_devices = [d for d in devices if d['max_input_channels'] > 0]
    else:
        filtered_devices = [d for d in devices if d['max_output_channels'] > 0]

    # If no devices, return default
    if not filtered_devices:
        return "default", "Default System Device"

    # Print the device list
    print_device_list(filtered_devices, device_type)

    # Ask for selection
    while True:
        print(f"Select {device_type} device (0-{len(filtered_devices)-1}, or 'd' for default): ", end="")
        selection = input().strip().lower()

        if selection == 'd':
            return "default", "Default System Device"

        try:
            idx = int(selection)
            if 0 <= idx < len(filtered_devices):
                device = filtered_devices[idx]
                return device['index'], device['name']
            else:
                print(f"Please enter a number between 0 and {len(filtered_devices)-1}")
        except ValueError:
            print("Please enter a valid number or 'd'")

def configure_audio(audio_manager) -> Dict[str, Any]:
    """
    Run the audio configuration wizard.

    Args:
        audio_manager: An instance of AudioManager

    Returns:
        Dict with audio configuration
    """
    # Default config
    config = {
        'enabled': True,
        'input_device': "default",
        'output_device': "default",
        'sample_rate': 48000,
        'channels': 1
    }

    if not audio_manager.pyaudio_available:
        print("\nPyAudio is not available. Audio functionality will be limited.")
        print("Please install PyAudio to enable audio streaming.")
        print("\nPress Enter to continue...")
        input()
        return {'enabled': False}

    # Get device list
    devices = audio_manager.get_devices()

    print_header()

    # Configure if audio should be enabled
    print("Do you want to enable audio streaming? (y/n) [y]: ", end="")
    enable_audio = input().strip().lower()
    if enable_audio == 'n':
        return {'enabled': False}

    # Input device selection
    print_header()
    print("Step 1: Select Audio Input Device")
    print("The input device is used to capture audio from your radio or microphone.")
    input_idx, input_name = get_device_selection(devices, 'input')
    config['input_device'] = input_idx

    # Output device selection
    print_header()
    print("Step 2: Select Audio Output Device")
    print("The output device is used to play audio to your radio or speakers.")
    output_idx, output_name = get_device_selection(devices, 'output')
    config['output_device'] = output_idx

    # Sample rate selection
    print_header()
    print("Step 3: Configure Audio Parameters")
    print("The sample rate determines the audio quality (higher = better quality but more bandwidth).")
    print("\nCommon sample rates:")
    print("1) 8000 Hz (Low quality, low bandwidth)")
    print("2) 16000 Hz (Medium quality)")
    print("3) 44100 Hz (CD quality)")
    print("4) 48000 Hz (High quality, recommended)")
    print("5) Custom")

    while True:
        print("\nSelect sample rate [4]: ", end="")
        sample_rate_choice = input().strip()

        if sample_rate_choice == "":
            sample_rate_choice = "4"

        if sample_rate_choice == "1":
            config['sample_rate'] = 8000
            break
        elif sample_rate_choice == "2":
            config['sample_rate'] = 16000
            break
        elif sample_rate_choice == "3":
            config['sample_rate'] = 44100
            break
        elif sample_rate_choice == "4":
            config['sample_rate'] = 48000
            break
        elif sample_rate_choice == "5":
            try:
                print("Enter custom sample rate in Hz: ", end="")
                custom_rate = int(input().strip())
                if 8000 <= custom_rate <= 192000:
                    config['sample_rate'] = custom_rate
                    break
                else:
                    print("Sample rate must be between 8000 and 192000 Hz")
            except ValueError:
                print("Please enter a valid number")
        else:
            print("Please select a valid option")

    # Channels selection
    print("\nNumber of audio channels:")
    print("1) Mono (1 channel, recommended for most amateur radio applications)")
    print("2) Stereo (2 channels)")

    while True:
        print("\nSelect number of channels [1]: ", end="")
        channels_choice = input().strip()

        if channels_choice == "":
            channels_choice = "1"

        if channels_choice == "1":
            config['channels'] = 1
            break
        elif channels_choice == "2":
            config['channels'] = 2
            break
        else:
            print("Please select a valid option")

    # Summary
    print_header()
    print("Audio Configuration Summary:")
    print(f"Input Device: {input_name}")
    print(f"Output Device: {output_name}")
    print(f"Sample Rate: {config['sample_rate']} Hz")
    print(f"Channels: {config['channels']}")

    print("\nPress Enter to save this configuration...")
    input()

    return config

def update_config_file(config_path: str, audio_config: Dict[str, Any]) -> bool:
    """
    Update the config file with new audio settings.

    Args:
        config_path: Path to the config file
        audio_config: Audio configuration dictionary

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load existing config or create new one
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                full_config = json.load(f)
        else:
            full_config = {
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
                "logging": {
                    "level": "info",
                    "file": "rig_ranger_server.log",
                    "console": True
                }
            }

        # Update audio configuration
        full_config["audio"] = audio_config

        # Write config to file
        with open(config_path, 'w') as f:
            json.dump(full_config, f, indent=2)

        return True
    except Exception as e:
        print(f"Error updating config file: {e}")
        return False

def run_wizard(audio_manager, config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Run the audio setup wizard.

    Args:
        audio_manager: An instance of AudioManager
        config_path: Optional path to config file

    Returns:
        Dict with audio configuration
    """
    print_header()

    print("This wizard will help you configure audio devices for RigRanger Server.")
    print("You can press Ctrl+C at any time to cancel the wizard.\n")

    try:
        # Run configuration
        audio_config = configure_audio(audio_manager)

        # Update config file if path provided
        if config_path:
            if update_config_file(config_path, audio_config):
                print(f"\nConfiguration saved to {config_path}")
            else:
                print("\nFailed to save configuration to file.")

        print("\nAudio configuration complete!")
        return audio_config

    except KeyboardInterrupt:
        print("\n\nWizard cancelled. Using default audio settings.")
        return {'enabled': False}
