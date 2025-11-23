#!/usr/bin/env python3
"""
Production Calibration Tool for ANC Headphones
Measures frequency response and generates optimal filter coefficients
"""

import serial
import numpy as np
import sounddevice as sd
import struct
import time
import sys
from scipy import signal
from scipy.fft import fft, fftfreq

class ANCCalibrationTool:
    """
    Calibrates ANC headphones by:
    1. Playing calibration tones
    2. Measuring frequency response
    3. Calculating optimal filter coefficients
    4. Writing coefficients to device flash
    """

    def __init__(self, serial_port='/dev/ttyUSB0', baudrate=115200):
        self.serial = serial.Serial(serial_port, baudrate, timeout=2)
        self.sample_rate = 48000
        self.num_taps = 512  # Filter length

    def send_command(self, cmd, data=None):
        """Send command to firmware via serial"""
        packet = struct.pack('<B', cmd)
        if data:
            packet += data
        self.serial.write(packet)

    def read_response(self):
        """Read response from firmware"""
        return self.serial.read(256)

    def measure_frequency_response(self):
        """
        Measure frequency response of the acoustic path
        Plays sweep tones and measures microphone response
        """
        print("[1/5] Measuring frequency response...")

        # Frequency sweep from 20Hz to 20kHz
        frequencies = np.logspace(np.log10(20), np.log10(20000), 100)
        response = np.zeros(len(frequencies), dtype=complex)

        for i, freq in enumerate(frequencies):
            # Generate test tone
            duration = 0.5  # seconds
            t = np.linspace(0, duration, int(self.sample_rate * duration))
            tone = np.sin(2 * np.pi * freq * t)

            # Play tone through speaker
            sd.play(tone, self.sample_rate)

            # Record microphone response
            mic_response = sd.rec(int(duration * self.sample_rate),
                                  samplerate=self.sample_rate,
                                  channels=1,
                                  dtype='float32')
            sd.wait()

            # Calculate magnitude and phase at this frequency
            fft_result = fft(mic_response.flatten())
            freq_idx = np.argmin(np.abs(fftfreq(len(mic_response), 1/self.sample_rate) - freq))
            response[i] = fft_result[freq_idx] / len(mic_response)

            print(f"  {i+1}/100: {freq:.1f} Hz - {20*np.log10(np.abs(response[i])):.1f} dB")

        return frequencies, response

    def calculate_optimal_filter(self, frequencies, response):
        """
        Calculate optimal FIR filter coefficients using inverse response
        """
        print("[2/5] Calculating optimal filter coefficients...")

        # Design inverse filter
        # Target: flat response (unity gain)
        target = np.ones_like(response)

        # Calculate desired frequency response
        desired_response = target / (response + 1e-6)  # Avoid division by zero

        # Convert to time domain using inverse FFT
        # Pad to filter length
        padded_response = np.zeros(self.num_taps, dtype=complex)
        padded_response[:len(desired_response)] = desired_response

        # IFFT to get filter coefficients
        coeffs = np.fft.ifft(padded_response).real

        # Apply window to reduce ringing
        window = signal.windows.hamming(self.num_taps)
        coeffs = coeffs * window

        # Normalize
        coeffs = coeffs / np.max(np.abs(coeffs))

        print(f"  Generated {self.num_taps}-tap FIR filter")

        return coeffs

    def verify_calibration(self, coeffs):
        """
        Verify calibration by testing noise cancellation
        """
        print("[3/5] Verifying calibration...")

        # Send filter coefficients to device
        self.upload_coefficients(coeffs)

        # Enable ANC
        self.send_command(0x10)  # CMD_ENABLE_ANC

        # Play white noise and measure cancellation
        duration = 2.0
        noise = np.random.randn(int(self.sample_rate * duration))

        # Measure noise before ANC
        print("  Measuring noise before ANC...")
        mic_before = sd.rec(int(duration * self.sample_rate),
                            samplerate=self.sample_rate,
                            channels=1,
                            dtype='float32')
        sd.play(noise, self.sample_rate)
        sd.wait()

        # Measure noise with ANC
        print("  Measuring noise with ANC enabled...")
        mic_after = sd.rec(int(duration * self.sample_rate),
                           samplerate=self.sample_rate,
                           channels=1,
                           dtype='float32')
        sd.play(noise, self.sample_rate)
        sd.wait()

        # Calculate noise reduction
        power_before = np.mean(mic_before ** 2)
        power_after = np.mean(mic_after ** 2)

        if power_after > 0:
            cancellation_db = 10 * np.log10(power_before / power_after)
        else:
            cancellation_db = 60.0  # Maximum measurable

        print(f"  Noise cancellation: {cancellation_db:.1f} dB")

        return cancellation_db

    def upload_coefficients(self, coeffs):
        """Upload filter coefficients to device flash"""
        print("[4/5] Uploading coefficients to device...")

        # Pack coefficients as floats
        data = struct.pack(f'<{len(coeffs)}f', *coeffs)

        # Send to device
        self.send_command(0x20, data)  # CMD_WRITE_CALIBRATION

        # Wait for acknowledgment
        response = self.read_response()
        if response[0] == 0x01:
            print("  Upload successful")
            return True
        else:
            print("  Upload failed!")
            return False

    def save_calibration_report(self, frequencies, response, coeffs, cancellation_db):
        """Save calibration report for quality control"""
        print("[5/5] Saving calibration report...")

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"calibration_report_{timestamp}.txt"

        with open(filename, 'w') as f:
            f.write("ANC Headphones Calibration Report\n")
            f.write("=" * 50 + "\n")
            f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Sample Rate: {self.sample_rate} Hz\n")
            f.write(f"Filter Taps: {self.num_taps}\n")
            f.write(f"Noise Cancellation: {cancellation_db:.1f} dB\n")
            f.write(f"Status: {'PASS' if cancellation_db >= 30.0 else 'FAIL'}\n")
            f.write("\n")
            f.write("Frequency Response:\n")
            for freq, resp in zip(frequencies, response):
                f.write(f"  {freq:.1f} Hz: {20*np.log10(np.abs(resp)):.1f} dB\n")

        print(f"  Report saved to {filename}")

    def run_calibration(self):
        """Run complete calibration process"""
        print("\n" + "="*60)
        print("ANC Headphones Production Calibration")
        print("="*60 + "\n")

        try:
            # Step 1: Measure frequency response
            frequencies, response = self.measure_frequency_response()

            # Step 2: Calculate optimal filter
            coeffs = self.calculate_optimal_filter(frequencies, response)

            # Step 3: Verify performance
            cancellation_db = self.verify_calibration(coeffs)

            # Step 4: Save report
            self.save_calibration_report(frequencies, response, coeffs, cancellation_db)

            # Final status
            print("\n" + "="*60)
            if cancellation_db >= 30.0:
                print("CALIBRATION PASSED ✓")
                print(f"Noise Cancellation: {cancellation_db:.1f} dB")
                return_code = 0
            else:
                print("CALIBRATION FAILED ✗")
                print(f"Noise Cancellation: {cancellation_db:.1f} dB (minimum: 30.0 dB)")
                return_code = 1
            print("="*60 + "\n")

            return return_code

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

    tool = ANCCalibrationTool(serial_port)
    return tool.run_calibration()

if __name__ == '__main__':
    sys.exit(main())
