#!/usr/bin/env python3
"""
Check Audio Devices - List available microphones and speakers

Run this before starting the ANC system to verify audio hardware.
"""

import sys

try:
    import pyaudio
except ImportError:
    print("Error: PyAudio not installed")
    print("Install with: pip install pyaudio")
    sys.exit(1)


def check_audio_devices():
    """List all available audio input/output devices."""

    print("="*80)
    print("AUDIO DEVICE CHECK")
    print("="*80)

    p = pyaudio.PyAudio()

    # Get device count
    device_count = p.get_device_count()
    print(f"\nTotal devices found: {device_count}")

    # Default devices
    print("\n" + "="*80)
    print("DEFAULT DEVICES")
    print("="*80)

    try:
        default_input = p.get_default_input_device_info()
        print(f"\n✓ Default Input (Microphone):")
        print(f"  Name: {default_input['name']}")
        print(f"  Index: {default_input['index']}")
        print(f"  Channels: {default_input['maxInputChannels']}")
        print(f"  Sample Rate: {int(default_input['defaultSampleRate'])} Hz")
    except Exception as e:
        print(f"\n✗ No default input device: {e}")

    try:
        default_output = p.get_default_output_device_info()
        print(f"\n✓ Default Output (Speaker):")
        print(f"  Name: {default_output['name']}")
        print(f"  Index: {default_output['index']}")
        print(f"  Channels: {default_output['maxOutputChannels']}")
        print(f"  Sample Rate: {int(default_output['defaultSampleRate'])} Hz")
    except Exception as e:
        print(f"\n✗ No default output device: {e}")

    # All input devices
    print("\n" + "="*80)
    print("ALL INPUT DEVICES (MICROPHONES)")
    print("="*80)

    input_devices = []
    for i in range(device_count):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            input_devices.append(info)
            print(f"\n[{info['index']}] {info['name']}")
            print(f"     Channels: {info['maxInputChannels']}")
            print(f"     Sample Rate: {int(info['defaultSampleRate'])} Hz")
            print(f"     Host API: {p.get_host_api_info_by_index(info['hostApi'])['name']}")

    if not input_devices:
        print("\n⚠ No input devices found!")

    # All output devices
    print("\n" + "="*80)
    print("ALL OUTPUT DEVICES (SPEAKERS)")
    print("="*80)

    output_devices = []
    for i in range(device_count):
        info = p.get_device_info_by_index(i)
        if info['maxOutputChannels'] > 0:
            output_devices.append(info)
            print(f"\n[{info['index']}] {info['name']}")
            print(f"     Channels: {info['maxOutputChannels']}")
            print(f"     Sample Rate: {int(info['defaultSampleRate'])} Hz")
            print(f"     Host API: {p.get_host_api_info_by_index(info['hostApi'])['name']}")

    if not output_devices:
        print("\n⚠ No output devices found!")

    # Host APIs
    print("\n" + "="*80)
    print("HOST APIS")
    print("="*80)

    host_api_count = p.get_host_api_count()
    for i in range(host_api_count):
        api_info = p.get_host_api_info_by_index(i)
        print(f"\n[{i}] {api_info['name']}")
        print(f"    Device count: {api_info['deviceCount']}")
        print(f"    Default input: {api_info['defaultInputDevice']}")
        print(f"    Default output: {api_info['defaultOutputDevice']}")

    # Test audio capability
    print("\n" + "="*80)
    print("AUDIO CAPABILITY TEST")
    print("="*80)

    # Test input
    try:
        test_stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=44100,
            input=True,
            frames_per_buffer=1024
        )
        test_stream.close()
        print("\n✓ Input test PASSED - Can capture audio")
    except Exception as e:
        print(f"\n✗ Input test FAILED: {e}")

    # Test output
    try:
        test_stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=44100,
            output=True,
            frames_per_buffer=1024
        )
        test_stream.close()
        print("✓ Output test PASSED - Can play audio")
    except Exception as e:
        print(f"✗ Output test FAILED: {e}")

    # Cleanup
    p.terminate()

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    print(f"\nInput devices: {len(input_devices)}")
    print(f"Output devices: {len(output_devices)}")

    if input_devices and output_devices:
        print("\n✓ System ready for ANC")
        print("\nNext step: Run 'python main.py --mode core --duration 30'")
        return 0
    else:
        print("\n✗ System NOT ready - missing audio devices")
        print("\nTroubleshooting:")
        if not input_devices:
            print("  - Connect microphone")
            print("  - Enable microphone in system settings")
            print("  - Check microphone permissions")
        if not output_devices:
            print("  - Connect speakers/headphones")
            print("  - Enable audio output in system settings")
        return 1


if __name__ == "__main__":
    sys.exit(check_audio_devices())
