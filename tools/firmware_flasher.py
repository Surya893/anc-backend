#!/usr/bin/env python3
"""
Firmware Flasher Tool for ANC Headphones
Uploads firmware via ST-Link or DFU
"""

import subprocess
import sys
import os
import struct
import hashlib
from pathlib import Path

class FirmwareFlasher:
    """Flash firmware to STM32H7 via ST-Link"""

    def __init__(self, firmware_path):
        self.firmware_path = firmware_path
        self.flash_address = 0x08010000  # Main firmware partition

    def verify_firmware(self):
        """Verify firmware file integrity"""
        print("[1/4] Verifying firmware file...")

        if not os.path.exists(self.firmware_path):
            print(f"ERROR: Firmware file not found: {self.firmware_path}")
            return False

        file_size = os.path.getsize(self.firmware_path)
        max_size = 960 * 1024  # 960KB

        if file_size > max_size:
            print(f"ERROR: Firmware too large: {file_size} bytes (max: {max_size})")
            return False

        print(f"  File size: {file_size} bytes")
        print(f"  File: {self.firmware_path}")

        # Calculate checksum
        with open(self.firmware_path, 'rb') as f:
            firmware_data = f.read()
            sha256 = hashlib.sha256(firmware_data).hexdigest()
            print(f"  SHA256: {sha256}")

        return True

    def check_st_link(self):
        """Check if ST-Link is connected"""
        print("[2/4] Checking ST-Link connection...")

        try:
            result = subprocess.run(['st-info', '--probe'],
                                  capture_output=True,
                                  text=True,
                                  timeout=5)

            if result.returncode == 0:
                print("  ST-Link detected")
                print(result.stdout)
                return True
            else:
                print("  ERROR: ST-Link not found")
                return False

        except FileNotFoundError:
            print("  ERROR: st-info tool not found. Install stlink-tools:")
            print("  sudo apt-get install stlink-tools")
            return False
        except Exception as e:
            print(f"  ERROR: {e}")
            return False

    def erase_flash(self):
        """Erase flash memory"""
        print("[3/4] Erasing flash memory...")

        try:
            result = subprocess.run(['st-flash', 'erase'],
                                  capture_output=True,
                                  text=True,
                                  timeout=30)

            if result.returncode == 0:
                print("  Flash erased successfully")
                return True
            else:
                print("  ERROR: Flash erase failed")
                print(result.stderr)
                return False

        except Exception as e:
            print(f"  ERROR: {e}")
            return False

    def flash_firmware(self):
        """Flash firmware to device"""
        print("[4/4] Flashing firmware...")

        try:
            # Flash using st-flash
            cmd = [
                'st-flash',
                'write',
                self.firmware_path,
                f'{self.flash_address:#x}'
            ]

            print(f"  Command: {' '.join(cmd)}")

            result = subprocess.run(cmd,
                                  capture_output=True,
                                  text=True,
                                  timeout=60)

            if result.returncode == 0:
                print("  Firmware flashed successfully")
                print(result.stdout)
                return True
            else:
                print("  ERROR: Firmware flash failed")
                print(result.stderr)
                return False

        except Exception as e:
            print(f"  ERROR: {e}")
            return False

    def verify_flash(self):
        """Verify flashed firmware"""
        print("[5/5] Verifying flashed firmware...")

        # Read back flash and compare
        try:
            result = subprocess.run(['st-flash', 'read', '/tmp/readback.bin',
                                   f'{self.flash_address:#x}',
                                   str(os.path.getsize(self.firmware_path))],
                                  capture_output=True,
                                  text=True,
                                  timeout=30)

            if result.returncode == 0:
                # Compare files
                with open(self.firmware_path, 'rb') as f1:
                    original = f1.read()
                with open('/tmp/readback.bin', 'rb') as f2:
                    readback = f2.read()

                if original == readback:
                    print("  Verification PASSED ✓")
                    return True
                else:
                    print("  Verification FAILED ✗")
                    return False
            else:
                print("  ERROR: Could not read back firmware")
                return False

        except Exception as e:
            print(f"  ERROR: {e}")
            return False

    def flash(self):
        """Execute complete flashing procedure"""
        print("\n" + "="*60)
        print("ANC Firmware Flasher")
        print("="*60 + "\n")

        # Verify firmware file
        if not self.verify_firmware():
            return 1

        # Check ST-Link
        if not self.check_st_link():
            return 1

        # Erase flash
        if not self.erase_flash():
            return 1

        # Flash firmware
        if not self.flash_firmware():
            return 1

        # Verify
        if not self.verify_flash():
            return 1

        print("\n" + "="*60)
        print("FIRMWARE FLASHING COMPLETE ✓")
        print("="*60 + "\n")

        return 0

def main():
    if len(sys.argv) < 2:
        print("Usage: firmware_flasher.py <firmware.bin>")
        print("\nExample:")
        print("  ./firmware_flasher.py ../firmware/build/anc_firmware.bin")
        return 1

    firmware_path = sys.argv[1]
    flasher = FirmwareFlasher(firmware_path)
    return flasher.flash()

if __name__ == '__main__':
    sys.exit(main())
