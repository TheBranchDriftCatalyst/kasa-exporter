#!/usr/bin/env bash
#
# Kasa Exporter Uninstallation Script
# Removes kasa-exporter service and optionally removes application files
#
# Usage:
#   sudo ./uninstall.sh                    # System-wide uninstall
#   ./uninstall.sh --user                  # User-level uninstall
#   ./uninstall.sh --keep-data             # Keep data but remove service
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
INSTALL_DIR="/opt/kasa-exporter"
SERVICE_USER="kasa-exporter"
USER_MODE=false
KEEP_DATA=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --user)
            USER_MODE=true
            INSTALL_DIR="$HOME/.local/share/kasa-exporter"
            shift
            ;;
        --keep-data)
            KEEP_DATA=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --user        Uninstall user-level installation"
            echo "  --keep-data   Keep installation directory and data"
            echo "  --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Helper functions
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

print_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

detect_platform() {
    OS="$(uname -s)"
    case "${OS}" in
        Linux*)
            PLATFORM="linux"
            SERVICE_MANAGER="systemd"
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
}

stop_service() {
    print_step "Stopping service"

    if [ "$SERVICE_MANAGER" = "systemd" ]; then
        if [ "$USER_MODE" = true ]; then
            if systemctl --user is-active --quiet kasa-exporter.service 2>/dev/null; then
                systemctl --user stop kasa-exporter.service
                print_success "Service stopped"
            else
                print_info "Service not running"
            fi
        else
            if systemctl is-active --quiet kasa-exporter.service 2>/dev/null; then
                systemctl stop kasa-exporter.service
                print_success "Service stopped"
            else
                print_info "Service not running"
            fi
        fi

    elif [ "$SERVICE_MANAGER" = "launchd" ]; then
        PLIST_FILE="$HOME/Library/LaunchAgents/com.kasa-exporter.plist"
        if [ -f "$PLIST_FILE" ]; then
            launchctl unload "$PLIST_FILE" 2>/dev/null || true
            print_success "Service stopped"
        else
            print_info "Service not found"
        fi
    fi
}

remove_service() {
    print_step "Removing service"

    if [ "$SERVICE_MANAGER" = "systemd" ]; then
        if [ "$USER_MODE" = true ]; then
            SERVICE_FILE="$HOME/.config/systemd/user/kasa-exporter.service"
            ENV_FILE="$HOME/.config/kasa-exporter/env"

            if systemctl --user is-enabled --quiet kasa-exporter.service 2>/dev/null; then
                systemctl --user disable kasa-exporter.service
            fi

            if [ -f "$SERVICE_FILE" ]; then
                rm "$SERVICE_FILE"
                print_success "Removed service file"
            fi

            if [ -f "$ENV_FILE" ]; then
                rm "$ENV_FILE"
                rmdir "$(dirname "$ENV_FILE")" 2>/dev/null || true
                print_success "Removed environment file"
            fi

            systemctl --user daemon-reload

        else
            SERVICE_FILE="/etc/systemd/system/kasa-exporter.service"
            ENV_FILE="/etc/kasa-exporter/env"

            if systemctl is-enabled --quiet kasa-exporter.service 2>/dev/null; then
                systemctl disable kasa-exporter.service
            fi

            if [ -f "$SERVICE_FILE" ]; then
                rm "$SERVICE_FILE"
                print_success "Removed service file"
            fi

            if [ -f "$ENV_FILE" ]; then
                rm "$ENV_FILE"
                rmdir /etc/kasa-exporter 2>/dev/null || true
                print_success "Removed environment file"
            fi

            systemctl daemon-reload
        fi

    elif [ "$SERVICE_MANAGER" = "launchd" ]; then
        PLIST_FILE="$HOME/Library/LaunchAgents/com.kasa-exporter.plist"

        if [ -f "$PLIST_FILE" ]; then
            rm "$PLIST_FILE"
            print_success "Removed launchd plist"
        fi
    fi
}

remove_data() {
    if [ "$KEEP_DATA" = true ]; then
        print_info "Keeping installation directory: $INSTALL_DIR"
        return
    fi

    print_step "Removing installation directory"

    if [ -d "$INSTALL_DIR" ]; then
        read -p "Remove $INSTALL_DIR? This will delete all data. (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
            print_success "Removed installation directory"
        else
            print_info "Kept installation directory"
        fi
    else
        print_info "Installation directory not found"
    fi
}

remove_user() {
    if [ "$USER_MODE" = true ] || [ "$PLATFORM" = "macos" ]; then
        return
    fi

    print_step "Removing service user"

    if id "$SERVICE_USER" &>/dev/null; then
        read -p "Remove user $SERVICE_USER? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            userdel "$SERVICE_USER" 2>/dev/null || true
            print_success "Removed user: $SERVICE_USER"
        else
            print_info "Kept user: $SERVICE_USER"
        fi
    fi
}

print_completion_message() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}  ${BLUE}Uninstallation Complete!${NC}                                 ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ "$KEEP_DATA" = true ]; then
        print_info "Service removed but data preserved at: $INSTALL_DIR"
    else
        print_success "Kasa Exporter has been completely removed"
    fi

    echo ""
}

# Main uninstallation flow
main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  ${YELLOW}Kasa Exporter Uninstallation${NC}                            ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    detect_platform

    # Check permissions
    if [ "$USER_MODE" = false ] && [ "$EUID" -ne 0 ]; then
        print_error "Please run as root or with sudo (or use --user flag)"
        exit 1
    fi

    stop_service
    remove_service
    remove_data
    remove_user
    print_completion_message
}

# Run main
main
