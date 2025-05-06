# Python Implementation Details

This document describes the design and implementation of the RigRanger Server Python application.

## Architecture Overview

RigRanger Server is built with a modular architecture consisting of the following components:

1. **HamlibManager** - Core class for interacting with amateur radios via Hamlib's `rigctld`
2. **RigRangerServer** - Web server and Socket.IO implementation for network communications
3. **Command-line interface** - For configuration and control

The application uses:
- **AsyncIO** - For asynchronous programming
- **Socket.IO** - For real-time communication with clients
- **AIOHTTP** - For the web server implementation
- **PySerial** - For serial port enumeration and configuration

## Class Structure

### HamlibManager

The `HamlibManager` class is responsible for:

- Finding and launching the Hamlib `rigctld` program
- Communicating with `rigctld` via a TCP socket
- Providing high-level functions for radio control
- Implementing error handling and reconnection logic
- Emitting events for radio status changes

```python
class HamlibManager:
    def __init__(self):
        """Initialize the HamlibManager."""
        # Initialize properties

    def find_rigctld_path(self) -> Optional[str]:
        """Find the path to the rigctld binary."""

    def on(self, event: str, callback: callable) -> None:
        """Register an event callback."""

    def emit(self, event: str, *args) -> None:
        """Emit an event to all registered callbacks."""

    def start_rigctld(self, config: Dict[str, Any]) -> bool:
        """Start the rigctld process with the specified configuration."""

    def connect(self) -> bool:
        """Connect to the rigctld socket."""

    def _listen(self) -> None:
        """Listen for data from the rigctld socket in a separate thread."""

    def _schedule_reconnect(self) -> None:
        """Schedule a reconnection attempt."""

    def _reconnect(self) -> None:
        """Attempt to reconnect to rigctld."""

    def execute_command(self, command: str) -> str:
        """Send a command to rigctld and get the response."""

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the Hamlib connection."""

    # Radio control methods
    def get_info(self) -> Dict[str, Any]:
        """Get information about the connected radio."""

    def get_frequency(self) -> float:
        """Get the current frequency of the radio."""

    def set_frequency(self, freq: float) -> bool:
        """Set the frequency of the radio."""

    def get_mode(self) -> Dict[str, Any]:
        """Get the current mode and passband of the radio."""

    def set_mode(self, mode: str, passband: int = 0) -> bool:
        """Set the mode and passband of the radio."""

    def get_ptt(self) -> bool:
        """Get the PTT (Push To Talk) status of the radio."""

    def set_ptt(self, ptt: bool) -> bool:
        """Set the PTT (Push To Talk) status of the radio."""

    def get_level(self, level_name: str) -> float:
        """Get a level value from the radio."""

    def set_level(self, level_name: str, level_value: float) -> bool:
        """Set a level value on the radio."""

    def stop(self) -> None:
        """Stop the rigctld process and close the connection."""
```

### RigRangerServer

The `RigRangerServer` class implements:

- A web server for HTTP API endpoints
- Socket.IO server for real-time communication
- Event handling for client connections
- Integration with the HamlibManager
- Static file serving for web interface

```python
class RigRangerServer:
    def __init__(self, config: Dict[str, Any]):
        """Initialize the RigRanger server."""

    def setup_routes(self) -> None:
        """Set up HTTP routes."""

    def setup_static_routes(self) -> None:
        """Set up routes for serving static files."""

    def create_minimal_ui(self, static_path: Path) -> None:
        """Create a minimal UI if the public directory doesn't exist."""

    # Various handler methods for HTTP requests
    async def handle_root(self, request: web.Request) -> web.Response:
        """Handle requests to the root URL."""

    async def handle_status(self, request: web.Request) -> web.Response:
        """Handle status API requests."""

    # More HTTP handlers...

    def setup_socket_events(self) -> None:
        """Set up Socket.IO event handlers."""

    async def run_in_executor(self, func, *args):
        """Run a blocking function in a thread executor."""

    def setup_hamlib(self) -> None:
        """Set up Hamlib with the current configuration."""

    # Event handlers
    def on_hamlib_status(self, status):
        """Handle Hamlib status events."""

    def on_hamlib_data(self, data):
        """Handle Hamlib data events."""

    def on_hamlib_debug(self, message):
        """Handle Hamlib debug events."""

    async def start(self):
        """Start the server."""

    def get_ip_addresses(self) -> List[str]:
        """Get all IP addresses of the server."""

    def stop(self):
        """Stop the server."""
```

## API Endpoints

The server exposes the following HTTP API endpoints:

| Endpoint                | Method | Description                   |
|-------------------------|--------|-------------------------------|
| `/api/status`           | GET    | Get server status             |
| `/api/radio/info`       | GET    | Get radio information         |
| `/api/radio/frequency`  | GET    | Get current frequency         |
| `/api/radio/frequency`  | POST   | Set frequency                 |
| `/api/radio/mode`       | GET    | Get current mode              |
| `/api/radio/mode`       | POST   | Set mode                      |

## Socket.IO Events

The server handles the following Socket.IO events:

| Event              | Direction      | Description                            |
|--------------------|----------------|----------------------------------------|
| `connect`          | Client→Server  | Client connection                      |
| `disconnect`       | Client→Server  | Client disconnection                   |
| `hamlib-command`   | Client→Server  | Direct Hamlib command execution        |
| `hamlib-function`  | Client→Server  | Call a HamlibManager function          |
| `server-status`    | Server→Client  | Server status update                   |
| `hamlib-status`    | Server→Client  | Hamlib status update                   |
| `hamlib-data`      | Server→Client  | Data received from Hamlib              |

## Initialization Flow

1. Parse command line arguments
2. Load configuration from file (if specified)
3. Create RigRangerServer instance
4. Setup HamlibManager
5. Start rigctld process
6. Connect to rigctld
7. Start web server
8. Wait for client connections

## Command Line Interface

The server supports the following command line arguments:

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

## Error Handling

The server implements robust error handling:

1. **Connection errors** - Automatic reconnection with exponential backoff
2. **Command errors** - Proper error reporting to clients
3. **Configuration errors** - Validation and sensible defaults
4. **Runtime errors** - Logging and graceful degradation

## Testing

The application includes a test script (`test_server.py`) that:

1. Launches the server with a dummy radio
2. Tests all HTTP API endpoints
3. Tests Socket.IO communication
4. Validates radio control functions

## Building Standalone Executables

The `build.py` script uses PyInstaller to create standalone executables:

1. Detects the platform (Windows, Linux, Raspberry Pi, macOS)
2. Installs required dependencies
3. Bundles all necessary files
4. Creates a single executable or directory

## Performance Considerations

For optimal performance on resource-constrained devices like Raspberry Pi:

1. Asynchronous I/O for non-blocking operation
2. Minimal dependencies
3. Low memory footprint
4. Efficient socket communication
5. Optional debug logging
