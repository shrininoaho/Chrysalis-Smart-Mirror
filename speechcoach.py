#!/usr/bin/env python3
"""
Chrysalis Speech Coach (Raspberry Pi 4)

Real-time public speaking coach. You speak, and a WS2812B LED strip gives
live colour feedback on your delivery.

Hardware:
  - Raspberry Pi 4
  - WS2812B strip, 60 LEDs: Pin 2 (5V), Pin 6 (GND), Pin 12 (GPIO18 data)
  - Jabra SPEAK 510 USB mic

LED colours:
  Green  = 120-160 WPM          Blue   = pause (4 s of silence)
  Red    = below 120 WPM        Purple = filler word (1 s)
  Amber  = above 160 WPM        White  = speech not understood

Run (LED strip needs root; -E keeps your GROQ_API_KEY):
  sudo -E ledenv/bin/python3 speechcoach.py

Install (inside the venv):
  pip install SpeechRecognition pyaudio rpi_ws281x requests
"""

import os
import re
import sys
import time
from collections import deque

import requests
import speech_recognition as sr
from rpi_ws281x import PixelStrip, Color

# ---------------- LED strip ----------------
LED_COUNT = 60
LED_PIN = 18            # GPIO18 (physical pin 12)
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 80     # 0-255, keep low to limit current draw
LED_INVERT = False
LED_CHANNEL = 0

GREEN = Color(0, 255, 0)
RED = Color(255, 0, 0)
AMBER = Color(255, 140, 0)
BLUE = Color(0, 0, 255)
PURPLE = Color(160, 0, 255)
WHITE = Color(255, 255, 255)
OFF = Color(0, 0, 0)

# ---------------- Coaching settings ----------------
WINDOW_SECONDS = 5          # WPM is measured over this sliding window
PHRASE_LIMIT = 5            # max seconds per transcribed phrase
PAUSE_SECONDS = 4           # silence longer than this counts as a pause
SLOW_WPM = 120
FAST_WPM = 160
FILLER_FLASH_SECONDS = 1.0
UNCLEAR_FLASH_SECONDS = 1.0
FILLERS = ["um", "uh", "like", "basically", "you know"]
MIC_NAME_HINT = "jabra"     # picks the Jabra SPEAK 510 if present

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


class LedStrip:
    def __init__(self):
        self.strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                                LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
        self.strip.begin()
        self.current = None

    def fill(self, colour):
        if colour == self.current:
            return
        for i in range(LED_COUNT):
            self.strip.setPixelColor(i, colour)
        self.strip.show()
        self.current = colour

    def off(self):
        self.fill(OFF)


def find_mic_index():
    """Return the index of the Jabra mic, or None to use the default."""
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        if MIC_NAME_HINT in name.lower():
            return index
    return None


def count_fillers(text):
    text = text.lower()
    total = 0
    for filler in FILLERS:
        total += len(re.findall(r"\b" + re.escape(filler) + r"\b", text))
    return total


def wpm_colour(wpm):
    if wpm < SLOW_WPM:
        return RED
    if wpm > FAST_WPM:
        return AMBER
    return GREEN


def groq_feedback(stats, transcript):
    """Ask Groq for short coaching feedback. Needs GROQ_API_KEY."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return "(Set GROQ_API_KEY to get AI coaching feedback.)"
    prompt = (
        "You are a public speaking coach. Give 3 short, specific tips based "
        "on this session.\n"
        f"Total words: {stats['words']}\n"
        f"Average WPM: {stats['avg_wpm']:.0f} (ideal 120-160)\n"
        f"Pauses (4 s+): {stats['pauses']}\n"
        f"Filler words: {stats['fillers']}\n"
        f"Transcript: {transcript[:3000]}"
    )
    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": GROQ_MODEL,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # network or API problems should not crash
        return f"(Could not get AI feedback: {exc})"


def print_summary(stats, transcript):
    elapsed = max(time.time() - stats["start"], 1)
    stats["avg_wpm"] = stats["words"] / (elapsed / 60)
    print("\n========== SESSION SUMMARY ==========")
    print(f"Total words : {stats['words']}")
    print(f"Average WPM : {stats['avg_wpm']:.0f}")
    print(f"Pauses      : {stats['pauses']}")
    print(f"Fillers     : {stats['fillers']}")
    print("=====================================")
    if stats["words"] > 0:
        print("\nAI coaching feedback:")
        print(groq_feedback(stats, transcript))


def main():
    leds = LedStrip()
    recogniser = sr.Recognizer()
    mic_index = find_mic_index()
    print("Using mic:", "Jabra" if mic_index is not None else "default device")

    stats = {"start": time.time(), "words": 0, "pauses": 0, "fillers": 0}
    transcript_parts = []
    word_times = deque()          # timestamps of recent words
    last_speech = time.time()
    in_pause = False
    override_colour = None        # temporary colour (filler / unclear)
    override_until = 0.0
    base_colour = BLUE

    try:
        with sr.Microphone(device_index=mic_index) as source:
            print("Calibrating for background noise...")
            recogniser.adjust_for_ambient_noise(source, duration=1)
            print("Listening. Speak now! Press Ctrl+C to finish.")

            while True:
                now = time.time()

                # Drop words older than the WPM window
                while word_times and now - word_times[0] > WINDOW_SECONDS:
                    word_times.popleft()

                # Pause detection
                if now - last_speech >= PAUSE_SECONDS:
                    if not in_pause:
                        in_pause = True
                        stats["pauses"] += 1
                        print("[pause]")
                    base_colour = BLUE

                # Show temporary override, otherwise the base colour
                if override_colour is not None and now < override_until:
                    leds.fill(override_colour)
                else:
                    override_colour = None
                    leds.fill(base_colour)

                # Listen for a phrase (returns quickly if nobody speaks)
                try:
                    audio = recogniser.listen(source, timeout=1,
                                              phrase_time_limit=PHRASE_LIMIT)
                except sr.WaitTimeoutError:
                    continue

                try:
                    text = recogniser.recognize_google(audio)
                except sr.UnknownValueError:
                    print("[not understood]")
                    override_colour = WHITE
                    override_until = time.time() + UNCLEAR_FLASH_SECONDS
                    continue
                except sr.RequestError as exc:
                    print(f"[speech service error: {exc}]")
                    override_colour = WHITE
                    override_until = time.time() + UNCLEAR_FLASH_SECONDS
                    continue

                # Update stats
                now = time.time()
                words = text.split()
                stats["words"] += len(words)
                transcript_parts.append(text)
                word_times.extend([now] * len(words))
                last_speech = now
                in_pause = False

                # WPM over the sliding window
                wpm = len(word_times) * (60 / WINDOW_SECONDS)
                base_colour = wpm_colour(wpm)

                # Filler words
                fillers = count_fillers(text)
                if fillers:
                    stats["fillers"] += fillers
                    override_colour = PURPLE
                    override_until = now + FILLER_FLASH_SECONDS

                print(f'"{text}"  | WPM: {wpm:.0f} | fillers: {fillers}')

    except KeyboardInterrupt:
        pass
    finally:
        leds.off()
        print_summary(stats, " ".join(transcript_parts))


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Run with sudo: the LED strip needs root access.")
        sys.exit(1)
    main()
