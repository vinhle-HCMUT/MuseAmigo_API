#!/usr/bin/env python3
"""
Simple audio file generator for MuseAmigo project.
Creates two sample WAV audio files for artifact descriptions.
"""

import wave
import struct
import math
import os

def generate_sine_wave_audio(filename, duration=3, frequency=440, sample_rate=44100):
    """
    Generate a simple sine wave audio file (WAV format).
    
    Args:
        filename: Output file path
        duration: Duration in seconds
        frequency: Frequency in Hz (440 Hz = A note)
        sample_rate: Sample rate in Hz
    """
    num_samples = duration * sample_rate
    
    # Create audio data
    audio_data = []
    for i in range(num_samples):
        # Generate sine wave
        sample = int(32767.0 * 0.3 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
        audio_data.append(struct.pack('<h', sample))
    
    # Write WAV file
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(audio_data))
    
    print(f"✓ Created: {filename} ({duration}s, {frequency}Hz)")


def generate_artifact_audio_files():
    """Generate sample audio files for the Flutter project."""
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(
        os.path.dirname(__file__), 
        '..', 'MuseFront', 'assets', 'audio'
    )
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("🎵 Generating sample audio files...\n")
    
    # Generate two different tone samples
    # artifact_001.mp3 - Lower tone (simulating historical narration)
    generate_sine_wave_audio(
        os.path.join(output_dir, 'artifact_001.wav'),
        duration=3,
        frequency=330  # E note
    )
    
    # artifact_002.mp3 - Higher tone (simulating museum guide)
    generate_sine_wave_audio(
        os.path.join(output_dir, 'artifact_002.wav'),
        duration=3,
        frequency=494  # B note
    )
    
    print(f"\n✓ Audio files created in: {output_dir}")
    print("  - artifact_001.wav (3 seconds)")
    print("  - artifact_002.wav (3 seconds)")
    print("\nNote: These are placeholder sine wave tones.")
    print("Replace them with actual audio narrations for production use.")


if __name__ == '__main__':
    generate_artifact_audio_files()
