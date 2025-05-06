# Raspberry Pi Setup Guide for RigRanger Server

This guide will help you set up the RigRanger Server on a Raspberry Pi to control your amateur radio equipment.

## Requirements

- Raspberry Pi 3 or newer (Pi 4 recommended for best performance)
- Raspbian OS Lite or Full (Debian-based)
- Internet connection (for installation only)
- Serial USB adapter for radio connection (if your radio doesn't have Ethernet)

## Installation

### Method 1: Automatic Installation

The easiest way to install RigRanger Server on your Raspberry Pi is to use our installation script:

1. Download the RigRanger Server repository:
   ```bash
   git clone https://github.com/YourUsername/RigRanger-Server.git
   cd RigRanger-Server
   ```

2. Run the installation script:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. The script will:
   - Install all required dependencies (Python, Hamlib, etc.)
   - Set up RigRanger Server as a system service
   - Create a desktop shortcut (if running desktop environment)
   - Configure the server to start automatically on boot

### Method 2: Manual Installation

If you prefer to install manually, follow these steps:

1. Install required system packages:
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3 python3-pip libhamlib-utils
   ```

2. Clone the repository:
   ```bash
   git clone https://github.com/YourUsername/RigRanger-Server.git
   cd RigRanger-Server
   ```

3. Install Python dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

4. Test the server:
   ```bash
   python3 rigranger_python_server.py --help
   ```

5. To set up as a system service, create a file at `/etc/systemd/system/rigranger-server.service`:
   ```ini
   [Unit]
   Description=RigRanger Server
   After=network.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/RigRanger-Server
   ExecStart=/usr/bin/python3 /home/pi/RigRanger-Server/rigranger_python_server.py
   Restart=on-failure
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

6. Enable and start the service:
   ```bash
   sudo systemctl enable rigranger-server
   sudo systemctl start rigranger-server
   ```

## Serial Port Setup

To use your radio via serial:

1. Find your device:
   ```bash
   ls -l /dev/ttyUSB*
   ```

2. Add your user to the dialout group for serial port access:
   ```bash
   sudo usermod -a -G dialout $USER
   ```
   You'll need to log out and back in for this to take effect.

3. Start the server with your radio settings:
   ```bash
   python3 rigranger_python_server.py -d /dev/ttyUSB0 -m 2
   ```
   (Replace the model number with your radio's Hamlib model ID)

## GPIO Setup (Optional)

If you want to use GPIO pins for PTT or other functions:

1. Install RPi.GPIO:
   ```bash
   pip3 install RPi.GPIO
   ```

2. Run your server with sudo or set up udev rules to allow GPIO access.

## Optimizing Performance

For best performance on a Raspberry Pi:

1. Use a class 10 SD card or SSD for faster disk operations
2. Consider overclocking if you're experiencing performance issues
3. On Pi 4 with 4GB+ RAM, increase the swap space:
   ```bash
   sudo nano /etc/dphys-swapfile
   # Increase CONF_SWAPSIZE to 2048
   sudo dphys-swapfile setup
   sudo dphys-swapfile swapon
   ```

4. Close unnecessary processes and services

## Troubleshooting

### Common Issues

1. **Permission denied for serial port**
   - Make sure your user is in the dialout group
   - Check the permissions of the serial device: `ls -l /dev/ttyUSB0`
   - Try running with sudo (not recommended for production)

2. **Hamlib not finding radio**
   - Verify your radio is turned on and in remote control mode
   - Check cable connections
   - Try a different USB port
   - Verify the correct model number: `rigctl --list`

3. **Server not starting**
   - Check logs: `journalctl -u rigranger-server`
   - Verify Python 3.7+ is installed: `python3 --version`
   - Ensure all dependencies are installed

4. **Performance issues**
   - Reduce logging level by using `-v` option
   - Close other applications
   - Check CPU usage: `htop`

### Getting Help

If you encounter problems not covered here:

1. Check the Github Issues page
2. Join our amateur radio community forum
3. Submit a detailed bug report with your Raspberry Pi model, OS version, and exact error messages

## Running from Boot

To have RigRanger Server start automatically when your Raspberry Pi boots:

1. If you used the automatic installer or set up the systemd service above, it's already configured to run at boot.

2. Alternatively, add to crontab:
   ```bash
   crontab -e
   ```

   Add the line:
   ```
   @reboot sleep 30 && cd /path/to/RigRanger-Server && python3 rigranger_python_server.py
   ```

## Remote Management

Access your Raspberry Pi running RigRanger Server remotely:

1. Via SSH (for headless control):
   ```bash
   ssh pi@your-pi-ip-address
   ```

2. Via VNC (for GUI access) - if you've enabled VNC:
   - Install RealVNC Viewer on your computer
   - Connect to your Pi's IP address

## Next Steps

Now that your Raspberry Pi is running RigRanger Server:

1. Connect to it from the RigRanger Client on your main computer
2. Set up port forwarding on your router if you want to access it from outside your local network
3. Consider setting up a dynamic DNS service if your home IP changes frequently

## Resources

- [Hamlib Documentation](https://hamlib.github.io/)
- [Raspberry Pi Documentation](https://www.raspberrypi.org/documentation/)
- [RigRanger Client Repository](https://github.com/YourUsername/RigRanger-Client)