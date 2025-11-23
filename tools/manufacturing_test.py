#!/usr/bin/env python3
"""
Manufacturing Test Suite for ANC Headphones
Comprehensive testing for quality assurance
"""

import serial
import struct
import time
import sys

class ManufacturingTest:
    """
    Production test suite that verifies:
    - Hardware functionality
    - Audio quality
    - ANC performance
    - Bluetooth connectivity
    - Battery operation
    - Button responsiveness
    """

    def __init__(self, serial_port='/dev/ttyUSB0'):
        self.serial = serial.Serial(serial_port, 115200, timeout=2)
        self.test_results = {}

    def send_command(self, cmd, data=None):
        """Send test command to device"""
        packet = struct.pack('<B', cmd)
        if data:
            packet += data
        self.serial.write(packet)

    def read_response(self):
        """Read response from device"""
        response = self.serial.read(256)
        return response

    def test_power_on(self):
        """Test 1: Power-on self-test"""
        print("\n[Test 1/10] Power-On Self-Test...")

        # Send power-on test command
        self.send_command(0x01)
        response = self.read_response()

        if len(response) > 0 and response[0] == 0x01:
            print("  ✓ Device responds")
            self.test_results['power_on'] = True
            return True
        else:
            print("  ✗ Device not responding")
            self.test_results['power_on'] = False
            return False

    def test_audio_codec(self):
        """Test 2: Audio codec initialization"""
        print("\n[Test 2/10] Audio Codec Test...")

        self.send_command(0x02)  # TEST_AUDIO_CODEC
        response = self.read_response()

        if response[0] == 0x01:
            print("  ✓ Audio codec initialized")
            self.test_results['audio_codec'] = True
            return True
        else:
            print("  ✗ Audio codec failed")
            self.test_results['audio_codec'] = False
            return False

    def test_microphones(self):
        """Test 3: Microphone input"""
        print("\n[Test 3/10] Microphone Test...")

        self.send_command(0x03)  # TEST_MICROPHONES
        time.sleep(1)  # Allow time for measurement
        response = self.read_response()

        # Response contains microphone levels
        ff_level = struct.unpack('<f', response[1:5])[0]
        fb_level = struct.unpack('<f', response[5:9])[0]

        print(f"  Feedforward mic: {ff_level:.2f} dB")
        print(f"  Feedback mic: {fb_level:.2f} dB")

        # Check levels are reasonable (not silent, not clipping)
        if -60 < ff_level < -10 and -60 < fb_level < -10:
            print("  ✓ Microphones working")
            self.test_results['microphones'] = True
            return True
        else:
            print("  ✗ Microphone levels out of range")
            self.test_results['microphones'] = False
            return False

    def test_speakers(self):
        """Test 4: Speaker output"""
        print("\n[Test 4/10] Speaker Test...")

        self.send_command(0x04)  # TEST_SPEAKERS
        print("  Playing test tone...")
        time.sleep(2)

        print("  Did you hear the test tone? (y/n): ", end='')
        response = input().lower()

        result = (response == 'y')
        self.test_results['speakers'] = result

        if result:
            print("  ✓ Speakers working")
        else:
            print("  ✗ Speakers failed")

        return result

    def test_anc_performance(self):
        """Test 5: ANC noise cancellation"""
        print("\n[Test 5/10] ANC Performance Test...")

        self.send_command(0x05)  # TEST_ANC
        time.sleep(3)  # Measure for 3 seconds
        response = self.read_response()

        cancellation_db = struct.unpack('<f', response[1:5])[0]

        print(f"  Noise cancellation: {cancellation_db:.1f} dB")

        # Require at least 30dB cancellation
        if cancellation_db >= 30.0:
            print("  ✓ ANC performance acceptable")
            self.test_results['anc_performance'] = True
            return True
        else:
            print(f"  ✗ ANC below minimum (30 dB required)")
            self.test_results['anc_performance'] = False
            return False

    def test_bluetooth(self):
        """Test 6: Bluetooth connectivity"""
        print("\n[Test 6/10] Bluetooth Test...")

        self.send_command(0x06)  # TEST_BLUETOOTH
        time.sleep(5)  # Allow time for BT discovery
        response = self.read_response()

        if response[0] == 0x01:
            print("  ✓ Bluetooth module working")
            self.test_results['bluetooth'] = True
            return True
        else:
            print("  ✗ Bluetooth module failed")
            self.test_results['bluetooth'] = False
            return False

    def test_battery(self):
        """Test 7: Battery and charging"""
        print("\n[Test 7/10] Battery Test...")

        self.send_command(0x07)  # TEST_BATTERY
        response = self.read_response()

        voltage = struct.unpack('<H', response[1:3])[0]  # millivolts
        level = response[3]  # percent

        print(f"  Battery voltage: {voltage} mV")
        print(f"  Battery level: {level}%")

        # Check voltage is in valid range
        if 3300 <= voltage <= 4200:
            print("  ✓ Battery OK")
            self.test_results['battery'] = True
            return True
        else:
            print("  ✗ Battery voltage out of range")
            self.test_results['battery'] = False
            return False

    def test_buttons(self):
        """Test 8: Button functionality"""
        print("\n[Test 8/10] Button Test...")
        print("  Press each button when prompted:")

        buttons = ['ANC Mode', 'Power', 'Volume Up', 'Volume Down']
        all_passed = True

        for i, button in enumerate(buttons):
            print(f"  Press {button} button...", end='', flush=True)

            # Wait for button press
            self.send_command(0x08, struct.pack('<B', i))
            response = self.read_response()

            if response[0] == 0x01:
                print(" ✓")
            else:
                print(" ✗")
                all_passed = False

        self.test_results['buttons'] = all_passed
        return all_passed

    def test_leds(self):
        """Test 9: LED indicators"""
        print("\n[Test 9/10] LED Test...")

        leds = ['Status', 'Bluetooth', 'Battery']

        for i, led in enumerate(leds):
            self.send_command(0x09, struct.pack('<B', i))
            print(f"  Is the {led} LED blinking? (y/n): ", end='')
            response = input().lower()

            if response != 'y':
                self.test_results['leds'] = False
                return False

        print("  ✓ All LEDs working")
        self.test_results['leds'] = True
        return True

    def test_calibration_data(self):
        """Test 10: Verify calibration data is present"""
        print("\n[Test 10/10] Calibration Data Test...")

        self.send_command(0x0A)  # TEST_CALIBRATION
        response = self.read_response()

        if response[0] == 0x01:
            print("  ✓ Calibration data present")
            self.test_results['calibration'] = True
            return True
        else:
            print("  ✗ Device not calibrated")
            self.test_results['calibration'] = False
            return False

    def print_results(self):
        """Print final test results"""
        print("\n" + "="*60)
        print("MANUFACTURING TEST RESULTS")
        print("="*60)

        for test, result in self.test_results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"  {test.replace('_', ' ').title():<30} {status}")

        print("="*60)

        all_passed = all(self.test_results.values())

        if all_passed:
            print("OVERALL: PASS ✓")
            print("Device ready for shipping")
            return 0
        else:
            print("OVERALL: FAIL ✗")
            print("Device requires rework")
            return 1

    def run_tests(self):
        """Run complete test suite"""
        print("\n" + "="*60)
        print("ANC HEADPHONES - MANUFACTURING TEST SUITE")
        print("="*60)

        try:
            # Run all tests
            self.test_power_on()
            self.test_audio_codec()
            self.test_microphones()
            self.test_speakers()
            self.test_anc_performance()
            self.test_bluetooth()
            self.test_battery()
            self.test_buttons()
            self.test_leds()
            self.test_calibration_data()

            # Print results
            return self.print_results()

        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
            return 1

        finally:
            self.serial.close()

def main():
    if len(sys.argv) > 1:
        serial_port = sys.argv[1]
    else:
        serial_port = '/dev/ttyUSB0'

    tester = ManufacturingTest(serial_port)
    return tester.run_tests()

if __name__ == '__main__':
    sys.exit(main())
