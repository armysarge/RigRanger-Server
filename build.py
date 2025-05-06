#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RigRanger Server - Build Script

This script builds a standalone executable of the RigRanger Server using PyInstaller.
It detects the platform and builds the appropriate executable.
"""

import os
import sys
import shutil
import platform
import subprocess
import argparse
from pathlib import Path

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Build RigRanger Server executable'
    )

    parser.add_argument('--clean', action='store_true',
                        help='Clean build directories before building')
    parser.add_argument('--debug', action='store_true',
                        help='Build with debug information')
    parser.add_argument('--console', action='store_true',
                        help='Build console app (no window hiding)')
    parser.add_argument('--onefile', action='store_true',
                        help='Build a single executable file')

    return parser.parse_args()

def detect_platform():
    """Detect the platform and return appropriate settings."""
    system = platform.system().lower()

    if system == 'windows':
        return {
            'platform': 'windows',
            'executable_name': 'rig_ranger_server.exe',
            'separator': '\\'
        }
    elif system == 'linux':
        # Check if running on Raspberry Pi
        try:
            with open('/proc/cpuinfo', 'r') as f:
                if 'Raspberry Pi' in f.read():
                    return {
                        'platform': 'raspberry_pi',
                        'executable_name': 'rig_ranger_server',
                        'separator': '/'
                    }
        except:
            pass

        return {
            'platform': 'linux',
            'executable_name': 'rig_ranger_server',
            'separator': '/'
        }
    elif system == 'darwin':
        return {
            'platform': 'macos',
            'executable_name': 'rig_ranger_server',
            'separator': '/'
        }
    else:
        return {
            'platform': 'unknown',
            'executable_name': 'rig_ranger_server',
            'separator': '/'
        }

def clean_build_directories():
    """Clean build directories."""
    print("Cleaning build directories...")

    # Remove build directory
    if os.path.exists('build'):
        shutil.rmtree('build')

    # Remove dist directory
    if os.path.exists('dist'):
        shutil.rmtree('dist')

    # Remove spec file
    if os.path.exists('rig_ranger_server.spec'):
        os.remove('rig_ranger_server.spec')

def install_requirements():
    """Install required packages."""
    print("Installing requirements...")

    requirements_file = Path('requirements.txt')
    if requirements_file.exists():
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    else:
        print("Requirements file not found. Installing basic requirements.")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "python-socketio", "aiohttp", "pyserial", "pyinstaller"
        ])

def build_executable(args, platform_info):
    """Build the executable."""
    print(f"Building executable for {platform_info['platform']}...")

    # Build from the right source file
    main_script = "rigranger_python_server.py"

    # Base command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "rig_ranger_server",
        "--clean"
    ]

    # Add debug flag if requested
    if args.debug:
        cmd.append("--debug")

    # Add console flag if requested
    if args.console:
        cmd.append("--console")
    else:
        # On Windows, use windowed mode (no console)
        if platform_info['platform'] == 'windows':
            cmd.append("--windowed")

    # Add onefile flag if requested
    if args.onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    # Add additional data files
    cmd.extend([
        "--add-data", f"public{platform_info['separator']}public",
    ])

    # Add the main script
    cmd.append(main_script)

    # Run PyInstaller
    subprocess.check_call(cmd)

    print("Build completed successfully.")
    print(f"Executable created in dist{platform_info['separator']}rig_ranger_server{platform_info['separator'] if not args.onefile else ''}")

def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()

    # Detect platform
    platform_info = detect_platform()

    # Print information
    print(f"Building RigRanger Server for {platform_info['platform']}")
    print(f"Python version: {platform.python_version()}")
    print(f"Platform: {platform.platform()}")

    # Create public directory if it doesn't exist
    if not os.path.exists('public'):
        os.makedirs('public')
        print("Created public directory for static files")

    # Clean build directories if requested
    if args.clean:
        clean_build_directories()

    # Install requirements
    install_requirements()

    # Build executable
    build_executable(args, platform_info)

    print("Build completed successfully!")

if __name__ == "__main__":
    main()