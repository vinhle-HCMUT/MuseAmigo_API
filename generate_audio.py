#!/usr/bin/env python3
"""
Simple audio file generator for MuseAmigo project.
Uses Gemini 2.5 Flash REST API for BOTH STT and TTS natively.
"""

import os
import asyncio
import wave
from dotenv import load_dotenv

from google import genai
from google.genai import types

load_dotenv()

# Initialize standard Gemini Client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Use the standard 2.5 Flash model for both reading and speaking
MODEL = "gemini-2.5-flash"


# =========================
# WAV -> TEXT (STT)
# =========================
async def audio_to_text(file_path: str) -> str:
    """
    Uploads an audio file to Gemini and asks for a direct transcription.
    No sample rate conversion or chunking needed.
    """
    print(f"Uploading {file_path} to Gemini...")

    # 1. Upload the raw audio file to Google's servers
    uploaded_file = client.files.upload(file=file_path)

    # 2. Ask the 2.5 Flash model to transcribe it
    prompt = "You are a transcription assistant. Reply ONLY with the exact transcript of the audio."

    response = client.models.generate_content(
        model=MODEL,
        contents=[uploaded_file, prompt]
    )

    # 3. Clean up the file from Google's servers to save space
    client.files.delete(name=uploaded_file.name)

    return response.text.strip()


# =========================
# TEXT -> AUDIO (TTS)
# =========================
async def text_to_audio(text: str, output_file: str = "output.wav", voice_name: str = "Aoede") -> str:
    """
    Converts text to speech using Gemini's dedicated TTS model.
    Outputs as a WAV file.
    """
    print(f"Generating audio using Gemini Voice ({voice_name})...")

    # We MUST use the dedicated TTS model, not the standard 2.5 Flash
    TTS_MODEL = "gemini-3.1-flash-tts-preview"

    # Use the correct types wrapper for the speech config
    config = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice_name
                )
            )
        )
    )

    response = client.models.generate_content(
        model=TTS_MODEL,
        contents=text,
        config=config
    )

    # Extract the raw PCM audio bytes from the response
    audio_bytes = response.candidates[0].content.parts[0].inline_data.data

    # FIX: Use the 'wave' module to write the proper WAV headers so players can read it
    with wave.open(output_file, "wb") as wf:
        wf.setnchannels(1)      # 1 channel (Mono)
        wf.setsampwidth(2)      # 2 bytes per sample (16-bit PCM)
        wf.setframerate(24000)  # Gemini's native output is 24kHz
        wf.writeframes(audio_bytes)

    return output_file


# =========================
# TEST
# =========================
async def main():
    print("=== TEST STT ===")

    # Note: Just pass your RAW input file! No `audioop` conversions needed!
    input_audio = "input_test.wav"

    if not os.path.exists(input_audio):
        print(f"Error: {input_audio} not found. Please add an audio file to test.")
        return

    text = await audio_to_text(input_audio)
    print("\nTranscript Received:")
    print(text)
    print("-" * 30)

    print("\n=== TEST TTS ===")

    # Simulate your LLM's response
    llm_response = f"Say hello to MuseAmigo! This is a test of Gemini's native TTS capabilities using the {MODEL} model."

    output = await text_to_audio(
        text=llm_response,
        output_file="result.wav",
        voice_name="Aoede"  # Options: Aoede, Charon, Fenrir, Kore, Puck
    )

    print(f"\nSuccess! Audio saved as: {output}")


if __name__ == "__main__":
    asyncio.run(main())