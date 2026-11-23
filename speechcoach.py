import speech_recognition as sr
import os
import time
from groq import Groq
from rpi_ws281x import PixelStrip, Color

# Set your key in the shell first: export GROQ_API_KEY=your_key (run with sudo -E)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# LED setup
LED_COUNT = 60
LED_PIN = 18
strip = PixelStrip(LED_COUNT, LED_PIN, 800000, 10, False, 50, 0)
strip.begin()

session = {
    "words": 0,
    "pauses": 0,
    "fillers": 0,
    "start_time": time.time(),
    "running": True
}

window_words = 0
window_start = time.time()
WINDOW_SECONDS = 5

FILLER_WORDS = ["um", "uh", "like", "basically", "you know"]

def set_all(color):
    for i in range(LED_COUNT):
        strip.setPixelColor(i, color)
    strip.show()

def get_overall_wpm():
    elapsed = (time.time() - session["start_time"]) / 60
    if elapsed < 0.1:
        return 0
    return int(session["words"] / elapsed)

def update_leds_by_wpm(wpm):
    if wpm < 120:
        set_all(Color(255, 0, 0))
        print(f"LED: RED (WPM {wpm} < 120)")
    elif wpm > 160:
        set_all(Color(255, 165, 0))
        print(f"LED: AMBER (WPM {wpm} > 160)")
    else:
        set_all(Color(0, 255, 0))
        print(f"LED: GREEN (WPM {wpm} is 120-160)")

def get_ai_feedback():
    try:
        client = Groq(api_key=GROQ_API_KEY)
        duration = int(time.time() - session["start_time"])
        prompt = f"""You are an expert public speaking coach. A student just completed a speaking session.

Session results:
- Duration: {duration} seconds
- Total words spoken: {session['words']}
- Average WPM: {get_overall_wpm()} (ideal is 120-160 WPM)
- Pauses detected: {session['pauses']}
- Filler words used: {session['fillers']} times (um, uh, like, basically, you know)

Give 3 specific, encouraging coaching tips in 5-6 sentences. Be warm, direct and motivating."""
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI feedback unavailable: {e}"

r = sr.Recognizer()
r.energy_threshold = 300
r.dynamic_energy_threshold = False
r.pause_threshold = 0.8
r.non_speaking_duration = 0.5

mic = sr.Microphone(device_index=1)   # Jabra: confirm index after each reboot

print("=" * 50)
print("   REAL-TIME PUBLIC SPEAKING COACH")
print("=" * 50)
print("Green=good | Red=slow | Amber=fast | Blue=pause | Purple=filler | White=unclear")

set_all(Color(0, 255, 0))

try:
    with mic as source:
        while session["running"]:
            try:
                print("Listening...")
                audio = r.listen(source, timeout=4, phrase_time_limit=5)
                print("Processing...")
                text = r.recognize_google(audio).lower()
                words = text.split()
                word_count = len(words)

                session["words"] += word_count
                window_words += word_count

                now = time.time()
                window_elapsed = now - window_start
                window_wpm = int((window_words / window_elapsed) * 60)

                if window_elapsed >= WINDOW_SECONDS:
                    window_words = 0
                    window_start = now

                filler_found = False
                for word in words:
                    if word in FILLER_WORDS:
                        session["fillers"] += 1
                        filler_found = True
                        print(f"Filler word: {word}")

                if filler_found:
                    set_all(Color(148, 0, 211))
                    print("LED: PURPLE (filler word!)")
                    time.sleep(1)

                update_leds_by_wpm(window_wpm)

                elapsed = int(time.time() - session["start_time"])
                print(f"Window WPM: {window_wpm} | Words: {session['words']} | Fillers: {session['fillers']} | Time: {elapsed}s")
                print(f"You said: {text}")

            except sr.WaitTimeoutError:
                session["pauses"] += 1
                print(f"Pause detected (total: {session['pauses']})")
                set_all(Color(0, 0, 255))
                window_words = 0
                window_start = time.time()

            except sr.UnknownValueError:
                print("Could not understand - speak louder!")
                set_all(Color(255, 255, 255))
                time.sleep(0.5)
                set_all(Color(0, 255, 0))

            except Exception as e:
                print(f"Error: {e}")

except KeyboardInterrupt:
    session["running"] = False
    set_all(Color(0, 0, 0))
    print("\nSESSION COMPLETE!")
    print(f"Total words : {session['words']}")
    print(f"Average WPM : {get_overall_wpm()}")
    print(f"Pauses      : {session['pauses']}")
    print(f"Filler words: {session['fillers']}")
    print("\nGetting AI coaching feedback...")
    print("-" * 50)
    print(get_ai_feedback())
    print("-" * 50)
