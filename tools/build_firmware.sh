#!/bin/bash
##############################################################################
# Build Script for ANC Firmware
# Builds, tests, and packages firmware for production
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories
FIRMWARE_DIR="../firmware"
BUILD_DIR="$FIRMWARE_DIR/build"
DIST_DIR="./dist"

print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Step 1: Clean previous build
print_header "Step 1: Clean Previous Build"
cd "$FIRMWARE_DIR"
make clean 2>/dev/null || true
print_success "Build directory cleaned"

# Step 2: Build firmware
print_header "Step 2: Build Firmware"
echo ""
make -j$(nproc)
echo ""

if [ -f "$BUILD_DIR/anc_firmware.elf" ]; then
    print_success "Firmware compiled successfully"
else
    print_error "Firmware compilation failed"
    exit 1
fi

# Step 3: Generate firmware package
print_header "Step 3: Generate Firmware Package"

# Get firmware version from git or default
VERSION=$(git describe --tags --always 2>/dev/null || echo "1.0.0")
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create dist directory
cd ..
mkdir -p "$DIST_DIR"

# Copy firmware files
cp "$BUILD_DIR/anc_firmware.bin" "$DIST_DIR/anc_firmware_${VERSION}.bin"
cp "$BUILD_DIR/anc_firmware.hex" "$DIST_DIR/anc_firmware_${VERSION}.hex"
cp "$BUILD_DIR/anc_firmware.elf" "$DIST_DIR/anc_firmware_${VERSION}.elf"

# Calculate checksums
cd "$DIST_DIR"
sha256sum anc_firmware_${VERSION}.bin > anc_firmware_${VERSION}.sha256
md5sum anc_firmware_${VERSION}.bin > anc_firmware_${VERSION}.md5

print_success "Firmware package created: anc_firmware_${VERSION}.bin"

# Step 4: Generate size report
print_header "Step 4: Size Report"
cd ../firmware
arm-none-eabi-size --format=berkeley "$BUILD_DIR/anc_firmware.elf"

# Get detailed section sizes
echo ""
echo "Detailed Memory Usage:"
arm-none-eabi-size -A "$BUILD_DIR/anc_firmware.elf" | grep -E "\.text|\.data|\.bss|\.dtcm|\.sram"

# Step 5: Disassembly (optional)
print_header "Step 5: Generate Disassembly"
arm-none-eabi-objdump -d "$BUILD_DIR/anc_firmware.elf" > "$BUILD_DIR/anc_firmware.asm"
print_success "Disassembly saved to build/anc_firmware.asm"

# Step 6: Create release package
print_header "Step 6: Create Release Package"
cd ..
RELEASE_NAME="anc_firmware_${VERSION}_${TIMESTAMP}"
RELEASE_DIR="$DIST_DIR/$RELEASE_NAME"

mkdir -p "$RELEASE_DIR"

# Copy firmware files
cp "$DIST_DIR/anc_firmware_${VERSION}"* "$RELEASE_DIR/"

# Create release notes
cat > "$RELEASE_DIR/RELEASE_NOTES.txt" << EOF
ANC Firmware Release Package
============================

Version: $VERSION
Build Date: $(date)
Git Commit: $(git rev-parse HEAD 2>/dev/null || echo "N/A")

Files Included:
- anc_firmware_${VERSION}.bin - Binary firmware image
- anc_firmware_${VERSION}.hex - Intel HEX format
- anc_firmware_${VERSION}.elf - ELF with debug symbols
- anc_firmware_${VERSION}.sha256 - SHA256 checksum
- anc_firmware_${VERSION}.md5 - MD5 checksum

Flashing Instructions:
----------------------
1. Connect ST-Link programmer to device
2. Run: st-flash write anc_firmware_${VERSION}.bin 0x08010000
3. Verify successful flash
4. Power cycle device

Changelog:
----------
- Initial production release
- ANC algorithms: LMS, NLMS, RLS
- Bluetooth audio support
- OTA firmware update capability
- Calibration system
- Power management

System Requirements:
-------------------
- ARM Cortex-M7 @ 480MHz
- 2MB Flash, 1MB RAM
- I2S audio codec
- Bluetooth module
- Battery management

EOF

# Create archive
cd "$DIST_DIR"
tar -czf "${RELEASE_NAME}.tar.gz" "$RELEASE_NAME"
print_success "Release package: ${RELEASE_NAME}.tar.gz"

# Step 7: Final summary
print_header "Build Summary"

FIRMWARE_SIZE=$(stat -f%z "$RELEASE_DIR/anc_firmware_${VERSION}.bin" 2>/dev/null || stat -c%s "$RELEASE_DIR/anc_firmware_${VERSION}.bin")
FIRMWARE_SIZE_KB=$((FIRMWARE_SIZE / 1024))

echo ""
echo "Version:      $VERSION"
echo "Build Date:   $(date)"
echo "Firmware Size: $FIRMWARE_SIZE_KB KB"
echo "Package:      ${RELEASE_NAME}.tar.gz"
echo ""

print_success "Build complete!"
echo ""
echo "Next steps:"
echo "  1. Flash firmware: ./firmware_flasher.py $DIST_DIR/$RELEASE_NAME/anc_firmware_${VERSION}.bin"
echo "  2. Run calibration: ./calibration_tool.py"
echo "  3. Run manufacturing test: ./manufacturing_test.py"
echo ""
