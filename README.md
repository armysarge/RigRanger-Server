# RigRanger Server

A lightweight Python-based API server for controlling amateur radios over the network using RigRanger Client.
Audio streaming, recording, and playback features are also included. This server is designed to be easy to set up and use, with a focus on performance and low resource usage. Hamlib is used for radio control, and the server can be run on a variety of platforms including Windows, macOS, Linux, and Raspberry Pi.

## Features

- **RigRanger Client Integration** - Control a wide variety of amateur radios using the RigRanger Client
- **RESTful API** - HTTP API endpoints for easy integration
- **Socket.IO API** - Real-time communication for responsive control
- **Cross Platform** - Runs on Windows, macOS, Linux, and Raspberry Pi
- **Lightweight** - Minimal resource usage, perfect for embedded devices
- **Standalone** - Can be built as a standalone executable with no dependencies

## Requirements

- Python 3.7 or higher
- Hamlib (for radio control)
- For audio functionality: appropriate audio drivers for your platform

## Installation

### Windows

1. Download the latest release from the [Releases page](https://github.com/Armysarge/RigRanger-Server/releases)
2. Extract the ZIP file to a location of your choice
3. Install Hamlib if not already installed:
   - Download from [Hamlib Releases](https://github.com/Hamlib/Hamlib/releases)
   - Add the Hamlib `bin` directory to your PATH
4. Run `rig_ranger_server.exe`

### Linux / Raspberry Pi

Automatic installation:

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/Armysarge/RigRanger-Server.git
cd RigRanger-Server
chmod +x install.sh
sudo ./install.sh
```

Manual installation:

```bash
# Install required packages
sudo apt-get update
sudo apt-get install -y python3 python3-pip libhamlib-utils

# Clone the repository
git clone https://github.com/Armysarge/RigRanger-Server.git
cd RigRanger-Server

# Install Python dependencies
pip3 install -r requirements.txt

# Run the server
python3 rigranger_python_server.py
```

### macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required packages
brew install python3 hamlib

# Clone the repository
git clone https://github.com/Armysarge/RigRanger-Server.git
cd RigRanger-Server

# Install Python dependencies
pip3 install -r requirements.txt

# Run the server
python3 rigranger_python_server.py
```

## Building from Source

You can build a standalone executable using the included build script:

```bash
python build.py --onefile --clean
```

This will create a single executable file in the `dist` directory.

Options:
- `--clean`: Clean build directories before building
- `--debug`: Include debug information in the build
- `--console`: Build a console application (shows console window on Windows)
- `--onefile`: Build a single executable file (default is a directory)

## Usage

Basic usage:

```bash
python rigranger_python_server.py
```

This will start the server with default settings (port 8080, using the Hamlib dummy radio).

Command-line options:

```
usage: rigranger_python_server.py [-h] [-p PORT] [-d DEVICE] [-m MODEL] [-c CONFIG] [--list-models] [--list-devices] [-v]

RigRanger Server - Lightweight console application for radio control

options:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  Server port number (default: 8080)
  -d DEVICE, --device DEVICE
                        Serial device path (e.g., /dev/ttyUSB0 or COM3)
  -m MODEL, --model MODEL
                        Hamlib radio model number (default: 1 - Dummy)
  -c CONFIG, --config CONFIG
                        Path to configuration file
  --list-models         List common Hamlib radio models
  --list-devices        List available serial devices
  -v, --verbose         Enable verbose logging
```

Examples:

```bash
# Start with an ICOM IC-7300 on COM3 (Windows)
python rigranger_python_server.py -m 3073 -d COM3

# Start with a Yaesu FT-991 on /dev/ttyUSB0 (Linux)
python rigranger_python_server.py -m 1042 -d /dev/ttyUSB0

# Use a custom port number
python rigranger_python_server.py -p 8090

# Use a configuration file
python rigranger_python_server.py -c config.json
```

## API Reference

### HTTP API Endpoints

| Endpoint                | Method | Description                   | Response                          |
|------------------------|---------|-------------------------------|------------------------------------|
| `/api/status`          | GET     | Get server status            | Server status, addresses, ports    |
| `/api/radio/info`      | GET     | Get radio information        | Model, capabilities, status       |
| `/api/radio/frequency` | GET     | Get current frequency        | Current frequency in Hz           |
| `/api/radio/frequency` | POST    | Set frequency                | Success/failure, new frequency    |
| `/api/radio/mode`      | GET     | Get current mode            | Current mode and passband         |
| `/api/radio/mode`      | POST    | Set mode                    | Success/failure, new mode         |
| `/api/radio/ptt`       | GET     | Get PTT status              | Current PTT state                 |
| `/api/radio/ptt`       | POST    | Set PTT state               | Success/failure, new PTT state    |
| `/api/config`          | GET     | Get server configuration    | Current server configuration      |
| `/api/config`          | POST    | Update configuration        | Success/failure, new config       |

### Socket.IO Events

| Event              | Direction      | Description                            |
|--------------------|----------------|----------------------------------------|
| `connect`          | Client→Server  | Client connection                      |
| `disconnect`       | Client→Server  | Client disconnection                   |
| `hamlib-command`   | Client→Server  | Direct Hamlib command execution        |
| `hamlib-function`  | Client→Server  | Call a HamlibManager function          |
| `server-status`    | Server→Client  | Server status update                   |
| `hamlib-status`    | Server→Client  | Hamlib status update                   |
| `hamlib-data`      | Server→Client  | Data received from Hamlib              |

## Configuration File

You can use a JSON configuration file with the `-c` option to specify server settings:

```json
{
  "server": {
    "port": 8080,
    "host": "0.0.0.0"
  },
  "hamlib": {
    "model": 3073,          // Hamlib model number (e.g., 3073 for IC-7300)
    "device": "/dev/ttyUSB0", // Serial device path
    "baud": 19200,          // Serial baud rate
    "retry_interval": 5     // Seconds between retry attempts
  },
  "audio": {
    "enabled": false,       // Audio features enabled/disabled
    "input_device": "default", // Audio input device (e.g., microphone)
    "output_device": "default", // Audio output device (e.g., speakers)
    "sample_rate": 48000    // Audio sample rate in Hz
  },
  "logging": {
    "level": "info",        // Logging level (debug, info, warning, error)
    "file": "rig_ranger_server.log"  // Log file path
  }
}
```

## Supported Radios

RigRanger Server supports all radios that are supported by Hamlib. You can view a list of supported radio models using:

```bash
python rigranger_python_server.py --list-models
```

Or directly with Hamlib:

```bash
rigctl --list
```

Common supported radios include:

- ICOM: IC-7300, IC-7100, IC-7851, IC-9700, etc.
- Yaesu: FT-991, FT-817, FT-857, FT-DX10, etc.
- Kenwood: TS-590, TS-2000, TS-990, etc.
- Elecraft: K3, KX3, K4, etc.
- FlexRadio: Flex-6000 series

## Documentation

- [Raspberry Pi Setup Guide](docs/raspberry_pi_setup.md)
- [Python Implementation Details](docs/python_implementation.md)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Hamlib](https://github.com/Hamlib/Hamlib) - Provides the radio control functionality
- [Socket.IO](https://socket.io/) - For real-time communication
- [AIOHTTP](https://docs.aiohttp.org/) - For the web server
- [PyInstaller](https://www.pyinstaller.org/) - For building standalone executables

## Contact

Project Link: [https://github.com/Armysarge/RigRanger-Server](https://github.com/Armysarge/RigRanger-Server)

## Security Considerations

- The server does not implement authentication by default. It is recommended to:
  - Run the server on a secure local network
  - Use a firewall to restrict access to the API ports
  - Implement authentication if exposing to the internet (see docs/security.md)
- Validate all inputs from API clients
- Keep your Python packages and Hamlib installation up to date

---

Made with ❤️ for Amateur Radio Operators
