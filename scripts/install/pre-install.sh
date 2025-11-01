#!/usr/bin/env bash
#
# Kasa Exporter Pre-Installation Script
# Downloads the repository and runs the installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/TheBranchDriftCatalyst/kasa-exporter/main/scripts/install/pre-install.sh | bash
#   wget -qO- https://raw.githubusercontent.com/TheBranchDriftCatalyst/kasa-exporter/main/scripts/install/pre-install.sh | bash
#
# Options:
#   BRANCH=dev     - Install from a specific branch (default: main)
#   INSTALL_DIR    - Custom installation directory
#   NO_CLEANUP     - Keep cloned repository after installation
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/TheBranchDriftCatalyst/kasa-exporter.git"
BRANCH="${BRANCH:-main}"
TEMP_DIR=$(mktemp -d)
CLEANUP_ON_EXIT=true

# Parse NO_CLEANUP environment variable
if [ "${NO_CLEANUP}" = "true" ] || [ "${NO_CLEANUP}" = "1" ]; then
    CLEANUP_ON_EXIT=false
fi

# Cleanup function
cleanup() {
    if [ "$CLEANUP_ON_EXIT" = true ] && [ -d "$TEMP_DIR" ]; then
        echo -e "${BLUE}Cleaning up temporary files...${NC}"
        rm -rf "$TEMP_DIR"
    elif [ -d "$TEMP_DIR" ]; then
        echo -e "${YELLOW}Repository preserved at: ${TEMP_DIR}${NC}"
    fi
}

# Register cleanup on exit
trap cleanup EXIT

print_header() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}Kasa Exporter - Quick Install${NC}                           ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
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

    # Check git
    if ! command -v git &> /dev/null; then
        print_error "git is not installed"
        echo ""
        print_info "Install git:"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "  brew install git"
        else
            echo "  sudo apt-get install git    # Debian/Ubuntu"
            echo "  sudo yum install git        # RHEL/CentOS"
        fi
        exit 1
    fi

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi

    # Check Poetry
    if ! command -v poetry &> /dev/null; then
        print_error "Poetry is not installed"
        print_info "Install with: curl -sSL https://install.python-poetry.org | python3 -"
        exit 1
    fi

    print_success "All requirements met"
}

clone_repository() {
    print_step "Downloading kasa-exporter"

    print_info "Cloning from: $REPO_URL (branch: $BRANCH)"
    print_info "Temporary directory: $TEMP_DIR"

    if git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$TEMP_DIR/kasa-exporter" 2>&1; then
        print_success "Repository downloaded successfully"
    else
        print_error "Failed to clone repository"
        print_info "Check:"
        echo "  1. Network connectivity"
        echo "  2. Branch '$BRANCH' exists"
        echo "  3. Repository URL is accessible: $REPO_URL"
        exit 1
    fi
}

run_installer() {
    print_step "Running installer"
    echo ""

    cd "$TEMP_DIR/kasa-exporter/scripts/install"

    # Check if running with sudo
    if [ "$EUID" -eq 0 ]; then
        print_info "Running as root"
        ./install.sh "$@"
    else
        print_info "Installer requires root privileges"
        # Check if sudo is available
        if command -v sudo &> /dev/null; then
            sudo ./install.sh "$@"
        else
            print_error "sudo not available, please run with root privileges"
            exit 1
        fi
    fi
}

print_footer() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}  ${BLUE}Installation Complete!${NC}                                    ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Main execution
main() {
    print_header
    check_requirements
    clone_repository
    run_installer "$@"
    print_footer
}

# Run main with all arguments passed to script
main "$@"
