#!/bin/bash
# RigRanger Server for Raspberry Pi - Installation Script

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}   RigRanger Server Installation    ${NC}"
echo -e "${BLUE}====================================${NC}"

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root (sudo).${NC}"
  exit 1
fi

# Get the actual user (not root)
if [ -n "$SUDO_USER" ]; then
  USER_HOME=$(eval echo ~$SUDO_USER)
else
  USER_HOME=$HOME
fi

INSTALL_DIR="$USER_HOME/rigranger-server"

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Function to install package if not already installed
install_package() {
  if ! dpkg -l | grep -q "^ii  $1 "; then
    echo -e "${YELLOW}Installing $1...${NC}"
    apt-get install -y "$1"
  else
    echo -e "${GREEN}Package $1 is already installed.${NC}"
  fi
}

# Update package database
echo -e "${YELLOW}Updating package database...${NC}"
apt-get update

# Install required packages
echo -e "${YELLOW}Installing required packages...${NC}"
install_package "python3"
install_package "python3-pip"
install_package "git"

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
echo -e "${GREEN}Python version: $PYTHON_VERSION${NC}"

# Create installation directory
if [ ! -d "$INSTALL_DIR" ]; then
  echo -e "${YELLOW}Creating installation directory...${NC}"
  mkdir -p "$INSTALL_DIR"
  # Set the correct ownership
  chown -R $SUDO_USER:$SUDO_USER "$INSTALL_DIR"
else
  echo -e "${GREEN}Installation directory already exists.${NC}"
fi

# Clone or update repository
if [ ! -d "$INSTALL_DIR/.git" ]; then
  echo -e "${YELLOW}Cloning RigRanger Server repository...${NC}"
  # Clone repository as the actual user
  su - $SUDO_USER -c "git clone https://github.com/Armysarge/RigRanger-Server.git $INSTALL_DIR"
else
  echo -e "${YELLOW}Updating existing repository...${NC}"
  # Pull latest changes as the actual user
  su - $SUDO_USER -c "cd $INSTALL_DIR && git pull"
fi

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
su - $SUDO_USER -c "pip3 install --user -r $INSTALL_DIR/requirements.txt"

# Create desktop shortcut
echo -e "${YELLOW}Creating desktop shortcut...${NC}"
if [ -d "$USER_HOME/Desktop" ]; then
  DESKTOP_FILE="$USER_HOME/Desktop/RigRanger.desktop"
  cat > "$DESKTOP_FILE" <<EOL
[Desktop Entry]
Type=Application
Name=RigRanger Server
Comment=Amateur Radio Control Server
Exec=python3 $INSTALL_DIR/rigranger_python_server.py
Icon=$INSTALL_DIR/public/favicon.ico
Terminal=true
Categories=HamRadio;
EOL
  # Set correct permissions and ownership
  chmod +x "$DESKTOP_FILE"
  chown $SUDO_USER:$SUDO_USER "$DESKTOP_FILE"
  echo -e "${GREEN}Desktop shortcut created.${NC}"
else
  echo -e "${YELLOW}Desktop directory not found. Skipping desktop shortcut creation.${NC}"
fi

# Create systemd service
echo -e "${YELLOW}Creating systemd service...${NC}"
SERVICE_FILE="/etc/systemd/system/rigranger-server.service"
cat > "$SERVICE_FILE" <<EOL
[Unit]
Description=RigRanger Server
After=network.target

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/rigranger_python_server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd daemon
systemctl daemon-reload

# Ask to enable and start the service
echo
echo -e "${BLUE}Do you want to enable and start the RigRanger Server service at boot? (y/n)${NC}"
read -r START_SERVICE
if [[ "$START_SERVICE" =~ ^[Yy]$ ]]; then
  systemctl enable rigranger-server
  systemctl start rigranger-server
  echo -e "${GREEN}Service enabled and started. Check status with: sudo systemctl status rigranger-server${NC}"
else
  echo -e "${YELLOW}Service created but not enabled. You can start it manually with: sudo systemctl start rigranger-server${NC}"
fi

# Setup serial port permissions
echo
echo -e "${BLUE}Do you want to add your user to the dialout group for serial port access? (y/n)${NC}"
read -r SETUP_SERIAL
if [[ "$SETUP_SERIAL" =~ ^[Yy]$ ]]; then
  usermod -a -G dialout $SUDO_USER
  echo -e "${GREEN}User added to dialout group. You need to log out and back in for this to take effect.${NC}"
else
  echo -e "${YELLOW}Skipping serial port setup.${NC}"
fi

# List available radios
echo
echo -e "${BLUE}Available radios in Hamlib:${NC}"
rigctl -l | head -n 20
echo -e "${YELLOW}(Showing only first 20 radios. Run 'rigctl -l' to see all available radios)${NC}"

# Find available serial ports
echo
echo -e "${BLUE}Available serial ports:${NC}"
if command_exists ls; then
  ls -l /dev/ttyUSB* /dev/ttyACM* /dev/ttyS* 2>/dev/null || echo "No serial ports found."
fi

# Installation complete
echo
echo -e "${GREEN}=============================================================${NC}"
echo -e "${GREEN}  RigRanger Server installation complete!${NC}"
echo -e "${GREEN}  Installation directory: $INSTALL_DIR${NC}"
echo -e "${GREEN}  To run manually: python3 $INSTALL_DIR/rigranger_python_server.py${NC}"
echo -e "${GREEN}  To check service status: sudo systemctl status rigranger-server${NC}"
echo -e "${GREEN}=============================================================${NC}"

# Ask to test run the server
echo
echo -e "${BLUE}Do you want to test run the server now? (y/n)${NC}"
read -r TEST_RUN
if [[ "$TEST_RUN" =~ ^[Yy]$ ]]; then
  # Stop the service if running
  systemctl stop rigranger-server

  # Run the server as the user
  echo -e "${YELLOW}Running RigRanger Server in test mode...${NC}"
  echo -e "${YELLOW}Press Ctrl+C to stop the server.${NC}"
  su - $SUDO_USER -c "cd $INSTALL_DIR && python3 rigranger_python_server.py"
else
  echo -e "${YELLOW}You can run the server later with 'python3 $INSTALL_DIR/rigranger_python_server.py'${NC}"
fi

exit 0
