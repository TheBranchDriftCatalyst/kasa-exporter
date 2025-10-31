#!/usr/bin/env bash
#
# Kasa Exporter Update Script
# Updates an existing kasa-exporter installation with new version/changes
#
# Usage:
#   sudo ./update.sh                    # Update system installation
#   ./update.sh --user                  # Update user installation
#   ./update.sh --no-restart            # Update without restarting service
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
NO_RESTART=false

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
        --no-restart)
            NO_RESTART=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --user        Update user installation"
            echo "  --no-restart  Update without restarting service"
            echo "  --help        Show this help message"
            echo ""
            echo "Environment variables:"
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
    echo -e "${BLUE}║${NC}  ${GREEN}Kasa Exporter Update${NC}                                    ${BLUE}║${NC}"
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

check_installation() {
    print_step "Checking existing installation"

    if [ ! -d "$INSTALL_DIR" ]; then
        print_error "Installation not found at: $INSTALL_DIR"
        print_info "Use install.sh to perform initial installation"
        exit 1
    fi

    print_info "Found installation at: $INSTALL_DIR"
    print_success "Installation check passed"
}

check_requirements() {
    print_step "Checking requirements"

    # Check Poetry
    if ! command -v poetry &> /dev/null; then
        print_error "Poetry is not installed"
        print_info "Install with: curl -sSL https://install.python-poetry.org | python3 -"
        exit 1
    fi

    print_info "Found Poetry $(poetry --version | cut -d' ' -f3)"

    # Check permissions
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
                print_error "systemd not found"
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

stop_service() {
    print_step "Stopping service"

    if [ "$SERVICE_MANAGER" = "systemd" ]; then
        if [ "$USER_MODE" = true ]; then
            if systemctl --user is-active --quiet kasa-exporter.service; then
                systemctl --user stop kasa-exporter.service
                print_success "Service stopped"
            else
                print_info "Service is not running"
            fi
        else
            if systemctl is-active --quiet kasa-exporter.service; then
                systemctl stop kasa-exporter.service
                print_success "Service stopped"
            else
                print_info "Service is not running"
            fi
        fi
    elif [ "$SERVICE_MANAGER" = "launchd" ]; then
        if launchctl list | grep -q com.kasa-exporter; then
            launchctl unload "$HOME/Library/LaunchAgents/com.kasa-exporter.plist"
            print_success "Service stopped"
        else
            print_info "Service is not running"
        fi
    fi
}

backup_config() {
    print_step "Backing up configuration"

    BACKUP_DIR="$INSTALL_DIR/.backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    # Backup .env files if they exist
    if [ -f "$INSTALL_DIR/.env" ]; then
        cp "$INSTALL_DIR/.env" "$BACKUP_DIR/"
        print_info "Backed up .env"
    fi

    # Backup config files
    if [ -d "$INSTALL_DIR/etc" ]; then
        cp -r "$INSTALL_DIR/etc" "$BACKUP_DIR/" 2>/dev/null || true
        print_info "Backed up etc/ directory"
    fi

    print_success "Configuration backed up to: $BACKUP_DIR"
}

update_application() {
    print_step "Updating application"

    # Get the repository root (prefer env var, fallback to path calculation)
    if [ -z "$REPO_ROOT" ]; then
        REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    fi

    # Validate we're in the right directory
    if [ ! -f "$REPO_ROOT/pyproject.toml" ] || [ ! -d "$REPO_ROOT/kasa_exporter" ]; then
        print_error "Invalid repository root: $REPO_ROOT"
        print_error "Expected to find pyproject.toml and kasa_exporter/ directory"
        exit 1
    fi

    print_info "Repository root: $REPO_ROOT"

    # Get current version
    if [ -f "$INSTALL_DIR/VERSION" ]; then
        OLD_VERSION=$(cat "$INSTALL_DIR/VERSION")
        print_info "Current version: $OLD_VERSION"
    else
        print_info "Current version: unknown"
    fi

    # Detect current ownership before updating
    if [ "$USER_MODE" = false ] && [ -d "$INSTALL_DIR" ]; then
        CURRENT_OWNER=$(stat -f "%Su" "$INSTALL_DIR" 2>/dev/null || stat -c "%U" "$INSTALL_DIR" 2>/dev/null)
        CURRENT_GROUP=$(stat -f "%Sg" "$INSTALL_DIR" 2>/dev/null || stat -c "%G" "$INSTALL_DIR" 2>/dev/null)
        print_info "Detected ownership: $CURRENT_OWNER:$CURRENT_GROUP"
    fi

    # Copy application files
    print_info "Copying updated files from $REPO_ROOT to $INSTALL_DIR..."
    rsync -a --exclude='.git' --exclude='__pycache__' --exclude='.venv' \
        --exclude='.pytest_cache' --exclude='.ruff_cache' --exclude='.promdb' \
        --exclude='htmlcov' --exclude='.coverage' --exclude='coverage.json' \
        --exclude='.claude' --exclude='.scratch' --exclude='.vscode' \
        --exclude='tests' --exclude='docs' --exclude='.github' \
        --exclude='archive' --exclude='node_modules' \
        --exclude='.env' --exclude='logs' \
        "$REPO_ROOT/" "$INSTALL_DIR/"

    # Set ownership to match existing installation
    if [ "$USER_MODE" = false ] && [ -n "$CURRENT_OWNER" ] && [ -n "$CURRENT_GROUP" ]; then
        print_info "Restoring ownership to $CURRENT_OWNER:$CURRENT_GROUP"
        chown -R "$CURRENT_OWNER:$CURRENT_GROUP" "$INSTALL_DIR"
    fi

    # Get new version
    if [ -f "$INSTALL_DIR/VERSION" ]; then
        NEW_VERSION=$(cat "$INSTALL_DIR/VERSION")
        print_info "New version: $NEW_VERSION"
    fi

    print_success "Application files updated"
}

update_dependencies() {
    print_step "Updating dependencies"

    cd "$INSTALL_DIR"

    print_info "Installing/updating dependencies with Poetry..."
    if [ "$USER_MODE" = true ]; then
        poetry install --only main --no-interaction --sync
    else
        # Run as detected owner if not standard service user, otherwise use current user
        if [ -n "$CURRENT_OWNER" ] && id "$CURRENT_OWNER" &>/dev/null && [ "$CURRENT_OWNER" != "root" ]; then
            print_info "Running poetry as $CURRENT_OWNER"
            sudo -u "$CURRENT_OWNER" poetry install --only main --no-interaction --sync
        else
            # Fall back to current user if owner is root or doesn't exist
            print_info "Running poetry as current user"
            poetry install --only main --no-interaction --sync
        fi
    fi

    print_success "Dependencies updated"
}

start_service() {
    if [ "$NO_RESTART" = true ]; then
        print_info "Skipping service restart (--no-restart flag)"
        return
    fi

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
    echo -e "${GREEN}║${NC}  ${BLUE}Update Complete!${NC}                                         ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ "$NO_RESTART" = true ]; then
        print_info "Remember to restart the service manually:"
        if [ "$SERVICE_MANAGER" = "systemd" ]; then
            if [ "$USER_MODE" = true ]; then
                echo "  systemctl --user restart kasa-exporter"
            else
                echo "  sudo systemctl restart kasa-exporter"
            fi
        elif [ "$SERVICE_MANAGER" = "launchd" ]; then
            echo "  launchctl unload ~/Library/LaunchAgents/com.kasa-exporter.plist"
            echo "  launchctl load ~/Library/LaunchAgents/com.kasa-exporter.plist"
        fi
    else
        print_info "Service is running with the updated version"
    fi

    echo ""
    print_info "Check service status:"
    if [ "$SERVICE_MANAGER" = "systemd" ]; then
        if [ "$USER_MODE" = true ]; then
            echo "  systemctl --user status kasa-exporter"
        else
            echo "  sudo systemctl status kasa-exporter"
        fi
    elif [ "$SERVICE_MANAGER" = "launchd" ]; then
        echo "  launchctl list | grep kasa-exporter"
    fi
    echo ""
}

# Main update flow
main() {
    print_header
    check_installation
    check_requirements
    detect_platform
    stop_service
    backup_config
    update_application
    update_dependencies
    start_service
    print_completion_message
}

# Run main
main
