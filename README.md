# Chrysalis – AI Smart Mirror for Communication Coaching
A two-way smart mirror that coaches your speaking in real time. It shows live pace, filler words and pauses on your reflection, so you can prepare for interviews and presentations.

## Current prototype
A Raspberry Pi 4 speech coach that gives live feedback on an LED strip. This is the analysis engine behind the mirror display.

## How it works
Mic → Google Speech Recognition → word count, WPM (5 s window), filler and pause detection → LED colour

## LED feedback
| Colour | Meaning |
|---|---|
| Green | 120–160 WPM |
| Red | Below 120 WPM |
| Amber | Above 160 WPM |
| Blue | Pause (4 s of silence) |
| Purple | Filler word (um, uh, like, basically, you know) |
| White | Speech not understood |

At the end of a session (Ctrl+C) it prints total words, average WPM, pauses and fillers, then asks Groq for coaching tips.

## Hardware
- Raspberry Pi 4
- WS2812B LED strip (60 LEDs): 5V to Pin 2, GND to Pin 6, data to Pin 12 (GPIO18)
- Jabra SPEAK 510 USB mic
- Two-way mirror with display

## Run (Raspberry Pi)
source ledenv/bin/activate
pip install SpeechRecognition pyaudio rpi_ws281x groq
export GROQ_API_KEY=your_key
sudo -E ledenv/bin/python3 speechcoach.py

## QNX port (qnx/ folder)
Four C processes: speech analyser, LED controller, session logger and a watchdog. The watchdog restarts a killed process in about 1 second. Speech data is simulated and LED output is printed as text.

make
on -p62 ./watchdog

Demo: in a second terminal run `pidin`, then `kill -9 <speech_analyser PID>`. The watchdog logs the crash and restarts it.

## Status
- ✅ Speech analysis engine on the Pi (WPM, fillers, pauses), with LED feedback
- ✅ Mirror display
- ✅ QNX design verified in a VMware VM (speech analyser, LED controller, logger, watchdog)
- ✅ Groq AI feedback written and tested
- 🚧 QNX on the Raspberry Pi: boot issue being fixed
