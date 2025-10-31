#!/usr/bin/env bash
#
# Kasa Exporter Installation Script
# Installs kasa-exporter as a system service (systemd or launchd)
#
# Usage:
#   sudo ./install.sh                    # Interactive installation
#   sudo ./install.sh --user             # User-level installation (no sudo)
#   sudo KASA_USERNAME=x KASA_PASSWORD=y ./install.sh  # Non-interactive
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="${INSTALL_DIR:-/opt/kasa-exporter}"
SERVICE_USER="${SERVICE_USER:-kasa-exporter}"
SERVICE_GROUP="${SERVICE_GROUP:-kasa-exporter}"
USER_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --user)
            USER_MODE=true
            INSTALL_DIR="$HOME/.local/share/kasa-exporter"
            SERVICE_USER="$USER"
            SERVICE_GROUP="$(id -gn)"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --user        Install for current user only (no sudo required)"
            echo "  --help        Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  KASA_USERNAME    Kasa account username"
            echo "  KASA_PASSWORD    Kasa account password"
            echo "  INSTALL_DIR      Installation directory (default: /opt/kasa-exporter)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  ${GREEN}Kasa Exporter Installation${NC}                              ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}==>${NC} ${GREEN}$1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC}  $1"
}

print_success() {
    echo -e "${GREEN}✓${NC}  $1"
}

print_error() {
    echo -e "${RED}✗${NC}  $1"
}

check_requirements() {
    print_step "Checking requirements"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_info "Found Python $PYTHON_VERSION"

    # Check Poetry
    if ! command -v poetry &> /dev/null; then
        print_error "Poetry is not installed"
        print_info "Install with: curl -sSL https://install.python-poetry.org | python3 -"
        exit 1
    fi

    print_info "Found Poetry $(poetry --version | cut -d' ' -f3)"

    # Check sudo if not user mode
    if [ "$USER_MODE" = false ] && [ "$EUID" -ne 0 ]; then
        print_error "Please run as root or with sudo (or use --user flag)"
        exit 1
    fi

    print_success "All requirements met"
}

detect_platform() {
    print_step "Detecting platform"

    OS="$(uname -s)"
    case "${OS}" in
        Linux*)
            PLATFORM="linux"
            if command -v systemctl &> /dev/null; then
                SERVICE_MANAGER="systemd"
            else
                print_error "systemd not found. This installer currently only supports systemd on Linux."
                exit 1
            fi
            ;;
        Darwin*)
            PLATFORM="macos"
            SERVICE_MANAGER="launchd"
            ;;
        *)
            print_error "Unsupported operating system: ${OS}"
            exit 1
            ;;
    esac

    print_info "Platform: $PLATFORM"
    print_info "Service manager: $SERVICE_MANAGER"
    print_success "Platform detected"
}

get_credentials() {
    print_step "Configuring credentials"

    # Check if already set via environment
    if [ -n "$KASA_USERNAME" ] && [ -n "$KASA_PASSWORD" ]; then
        print_info "Using credentials from environment"
        return
    fi

    # Interactive prompt
    echo ""
    read -p "Enter Kasa username: " KASA_USERNAME
    read -sp "Enter Kasa password: " KASA_PASSWORD
    echo ""

    if [ -z "$KASA_USERNAME" ] || [ -z "$KASA_PASSWORD" ]; then
        print_error "Username and password are required"
        exit 1
    fi

    print_success "Credentials configured"
}

validate_credentials() {
    print_step "Validating Kasa credentials"

    # Get the repository root (two levels up from scripts/install)
    REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    print_info "Testing connection to Kasa cloud..."

    # Run validation script
    if cd "$REPO_ROOT" && KASA_USERNAME="$KASA_USERNAME" KASA_PASSWORD="$KASA_PASSWORD" \
        poetry run python "$SCRIPT_DIR/validate_credentials.py" 2>&1; then
        print_success "Credentials validated successfully"
        return 0
    else
        print_error "Credential validation failed"
        echo ""
        print_info "Please check:"
        echo "  1. Username and password are correct"
        echo "  2. Your Kasa account is active"
        echo "  3. Network connectivity to Kasa cloud services"
        echo ""
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        print_info "Continuing despite validation failure..."
    fi
}

create_user() {
    if [ "$USER_MODE" = true ]; then
        print_info "Skipping user creation (user mode)"
        return
    fi

    print_step "Creating service user"

    if [ "$PLATFORM" = "linux" ]; then
        if id "$SERVICE_USER" &>/dev/null; then
            print_info "User $SERVICE_USER already exists"
        else
            useradd --system --no-create-home --shell /bin/false "$SERVICE_USER"
            print_success "Created user: $SERVICE_USER"
        fi
    elif [ "$PLATFORM" = "macos" ]; then
        print_info "Skipping user creation on macOS (using current user)"
        SERVICE_USER="$USER"
        SERVICE_GROUP="$(id -gn)"
    fi
}

install_application() {
    print_step "Installing application"

    # Get the repository root (two levels up from scripts/install)
    REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

    # Validate we're in the right directory
    if [ ! -f "$REPO_ROOT/pyproject.toml" ] || [ ! -d "$REPO_ROOT/kasa_exporter" ]; then
        print_error "Invalid repository root: $REPO_ROOT"
        print_error "Expected to find pyproject.toml and kasa_exporter/ directory"
        exit 1
    fi

    print_info "Repository root: $REPO_ROOT"

    # Create installation directory
    if [ ! -d "$INSTALL_DIR" ]; then
        mkdir -p "$INSTALL_DIR"
        print_success "Created directory: $INSTALL_DIR"
    fi

    # Copy application files
    print_info "Copying application files from $REPO_ROOT to $INSTALL_DIR..."
    rsync -a --exclude='.git' --exclude='__pycache__' --exclude='.venv' \
        --exclude='.pytest_cache' --exclude='.ruff_cache' --exclude='.promdb' \
        --exclude='htmlcov' --exclude='.coverage' --exclude='coverage.json' \
        --exclude='.claude' --exclude='.scratch' --exclude='.vscode' \
        --exclude='tests' --exclude='docs' --exclude='.github' \
        --exclude='archive' --exclude='node_modules' \
        "$REPO_ROOT/" "$INSTALL_DIR/"

    # Set ownership
    if [ "$USER_MODE" = false ]; then
        chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
    fi

    # Install dependencies with Poetry
    print_info "Installing dependencies with Poetry..."
    cd "$INSTALL_DIR"

    if [ "$USER_MODE" = true ]; then
        poetry install --only main --no-interaction
    else
        sudo -u "$SERVICE_USER" poetry install --only main --no-interaction
    fi

    print_success "Application installed"
}

configure_environment() {
    print_step "Configuring environment"

    if [ "$PLATFORM" = "linux" ]; then
        # Create environment file for systemd
        ENV_FILE="/etc/kasa-exporter/env"

        if [ "$USER_MODE" = false ]; then
            mkdir -p /etc/kasa-exporter
            cat > "$ENV_FILE" <<EOF
# Kasa Exporter Configuration
KASA_USERNAME=$KASA_USERNAME
KASA_PASSWORD=$KASA_PASSWORD
TZ=${TZ:-America/Los_Angeles}
LOG_LEVEL=${LOG_LEVEL:-INFO}
METRICS_PORT=${METRICS_PORT:-9200}
EOF
            chmod 600 "$ENV_FILE"
            print_success "Created environment file: $ENV_FILE"
        else
            # User mode - use systemd user directory
            mkdir -p "$HOME/.config/kasa-exporter"
            ENV_FILE="$HOME/.config/kasa-exporter/env"
            cat > "$ENV_FILE" <<EOF
# Kasa Exporter Configuration
KASA_USERNAME=$KASA_USERNAME
KASA_PASSWORD=$KASA_PASSWORD
TZ=${TZ:-America/Los_Angeles}
LOG_LEVEL=${LOG_LEVEL:-INFO}
METRICS_PORT=${METRICS_PORT:-9200}
EOF
            chmod 600 "$ENV_FILE"
            print_success "Created environment file: $ENV_FILE"
        fi
    elif [ "$PLATFORM" = "macos" ]; then
        # For launchd, we'll embed credentials in the plist
        print_info "Credentials will be embedded in launchd plist"
    fi
}

install_service() {
    print_step "Installing service"

    VENV_PATH="$INSTALL_DIR/.venv"

    if [ "$SERVICE_MANAGER" = "systemd" ]; then
        if [ "$USER_MODE" = true ]; then
            # User service
            SERVICE_FILE="$HOME/.config/systemd/user/kasa-exporter.service"
            mkdir -p "$HOME/.config/systemd/user"

            # Copy and modify service file
            sed -e "s|User=kasa-exporter|User=$SERVICE_USER|g" \
                -e "s|Group=kasa-exporter|Group=$SERVICE_GROUP|g" \
                -e "s|WorkingDirectory=/opt/kasa-exporter|WorkingDirectory=$INSTALL_DIR|g" \
                -e "s|Environment=\"PATH=/opt/kasa-exporter/.venv|Environment=\"PATH=$VENV_PATH|g" \
                -e "s|EnvironmentFile=-/etc/kasa-exporter/env|EnvironmentFile=-$HOME/.config/kasa-exporter/env|g" \
                -e "s|ExecStart=/opt/kasa-exporter/.venv|ExecStart=$VENV_PATH|g" \
                -e "s|ReadWritePaths=/opt/kasa-exporter|ReadWritePaths=$INSTALL_DIR|g" \
                "$REPO_ROOT/scripts/install/kasa-exporter.service" > "$SERVICE_FILE"

            systemctl --user daemon-reload
            systemctl --user enable kasa-exporter.service
            print_success "Installed systemd user service"
        else
            # System service
            SERVICE_FILE="/etc/systemd/system/kasa-exporter.service"

            # Copy and modify service file
            sed -e "s|/opt/kasa-exporter|$INSTALL_DIR|g" \
                -e "s|/opt/kasa-exporter/.venv|$VENV_PATH|g" \
                "$REPO_ROOT/scripts/install/kasa-exporter.service" > "$SERVICE_FILE"

            systemctl daemon-reload
            systemctl enable kasa-exporter.service
            print_success "Installed systemd service"
        fi

    elif [ "$SERVICE_MANAGER" = "launchd" ]; then
        PLIST_FILE="$HOME/Library/LaunchAgents/com.kasa-exporter.plist"
        mkdir -p "$HOME/Library/LaunchAgents"
        mkdir -p "$INSTALL_DIR/logs"

        # Create plist from template
        sed -e "s|VENV_PATH|$VENV_PATH|g" \
            -e "s|INSTALL_PATH|$INSTALL_DIR|g" \
            "$REPO_ROOT/scripts/install/com.kasa-exporter.plist" > "$PLIST_FILE"

        # Add credentials to plist
        /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:KASA_USERNAME string $KASA_USERNAME" "$PLIST_FILE" 2>/dev/null || \
        /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:KASA_USERNAME $KASA_USERNAME" "$PLIST_FILE"

        /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:KASA_PASSWORD string $KASA_PASSWORD" "$PLIST_FILE" 2>/dev/null || \
        /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:KASA_PASSWORD $KASA_PASSWORD" "$PLIST_FILE"

        print_success "Installed launchd service"
    fi
}

start_service() {
    print_step "Starting service"

    if [ "$SERVICE_MANAGER" = "systemd" ]; then
        if [ "$USER_MODE" = true ]; then
            systemctl --user start kasa-exporter.service
        else
            systemctl start kasa-exporter.service
        fi

        sleep 2

        if [ "$USER_MODE" = true ]; then
            if systemctl --user is-active --quiet kasa-exporter.service; then
                print_success "Service started successfully"
            else
                print_error "Service failed to start. Check logs with: journalctl --user -u kasa-exporter -n 50"
                exit 1
            fi
        else
            if systemctl is-active --quiet kasa-exporter.service; then
                print_success "Service started successfully"
            else
                print_error "Service failed to start. Check logs with: journalctl -u kasa-exporter -n 50"
                exit 1
            fi
        fi

    elif [ "$SERVICE_MANAGER" = "launchd" ]; then
        launchctl load "$HOME/Library/LaunchAgents/com.kasa-exporter.plist"
        sleep 2

        if launchctl list | grep -q com.kasa-exporter; then
            print_success "Service started successfully"
        else
            print_error "Service failed to start. Check logs in: $INSTALL_DIR/logs/"
            exit 1
        fi
    fi
}

print_completion_message() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}  ${BLUE}Installation Complete!${NC}                                    ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    print_info "Service is running and will start automatically on boot"
    echo ""

    if [ "$SERVICE_MANAGER" = "systemd" ]; then
        if [ "$USER_MODE" = true ]; then
            print_info "Useful commands:"
            echo "  systemctl --user status kasa-exporter    # Check status"
            echo "  systemctl --user stop kasa-exporter      # Stop service"
            echo "  systemctl --user start kasa-exporter     # Start service"
            echo "  systemctl --user restart kasa-exporter   # Restart service"
            echo "  journalctl --user -u kasa-exporter -f    # View logs"
        else
            print_info "Useful commands:"
            echo "  sudo systemctl status kasa-exporter      # Check status"
            echo "  sudo systemctl stop kasa-exporter        # Stop service"
            echo "  sudo systemctl start kasa-exporter       # Start service"
            echo "  sudo systemctl restart kasa-exporter     # Restart service"
            echo "  sudo journalctl -u kasa-exporter -f      # View logs"
        fi
    elif [ "$SERVICE_MANAGER" = "launchd" ]; then
        print_info "Useful commands:"
        echo "  launchctl list | grep kasa-exporter      # Check status"
        echo "  launchctl unload ~/Library/LaunchAgents/com.kasa-exporter.plist  # Stop"
        echo "  launchctl load ~/Library/LaunchAgents/com.kasa-exporter.plist    # Start"
        echo "  tail -f $INSTALL_DIR/logs/kasa-exporter.log  # View logs"
    fi

    echo ""
    print_info "Access the exporter:"
    echo "  Dashboard: http://localhost:${METRICS_PORT:-9200}"
    echo "  Metrics:   http://localhost:${METRICS_PORT:-9200}/metrics"
    echo ""

    print_info "To uninstall:"
    echo "  cd $REPO_ROOT/scripts/install"
    if [ "$USER_MODE" = true ]; then
        echo "  ./uninstall.sh --user"
    else
        echo "  sudo ./uninstall.sh"
    fi
    echo ""
}

# Main installation flow
main() {
    print_header
    check_requirements
    detect_platform
    get_credentials
    validate_credentials
    create_user
    install_application
    configure_environment
    install_service
    start_service
    print_completion_message
}

# Run main
main
