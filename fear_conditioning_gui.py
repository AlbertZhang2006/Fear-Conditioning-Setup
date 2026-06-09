import os
import tkinter as tk
import serial
import time
import random
import csv
import winsound
import threading
from datetime import datetime

# ---------------------------
# CONFIG
# ---------------------------
ARDUINO_PORT = "COM5"   # change this
BAUD = 115200

# Windows-only built-in audio playback for WAV files or fallback beep tones
tone_freqs = {
    "A": 440,
    "B": 550,
    "C": 660
}

ser = serial.Serial(ARDUINO_PORT, BAUD, timeout=1)
time.sleep(2)  # allow Arduino reset

# ---------------------------
# EXPERIMENT PARAMETERS (editable later via GUI)
# ---------------------------
tone_files = {
    "A": "Tones/ToneA.wav",
    "B": "Tones/ToneB.wav",
    "C": "Tones/ToneC.wav"
}

tone_duration = 2
shock_delay = 0
shock_duration = 2

# Example sequence (you can randomize this)
sequence = ["A", "B", "A", "B", "A", "A"]

# ---------------------------
# LOGGING
# ---------------------------
log_file = f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

with open(log_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["time", "event", "trial", "stimulus"])

def log(event, trial, stim):
    with open(log_file, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([time.time(), event, trial, stim])

# ---------------------------
# ARDUINO CONTROL
# ---------------------------
def shock_on():
    ser.write(b"SHOCK_ON\n")

def shock_off():
    ser.write(b"SHOCK_OFF\n")

# ---------------------------
# STIMULUS CONTROL
# ---------------------------
def play_tone(stim):
    tone_file = tone_files.get(stim)
    if tone_file and os.path.exists(tone_file):
        winsound.PlaySound(tone_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
    else:
        frequency = tone_freqs.get(stim, 440)
        winsound.Beep(frequency, int(tone_duration * 1000))

def run_experiment():
    log("START", "", "")

    for i, stim in enumerate(sequence):

        log("TRIAL_START", i, stim)

        play_tone(stim)
        log("TONE_ON", i, stim)

        start = time.time()

        # If Tone A → schedule shock
        if stim == "A":
            while time.time() - start < shock_delay:
                time.sleep(0.01)

            shock_on()
            log("SHOCK_ON", i, stim)

            time.sleep(shock_duration)

            shock_off()
            log("SHOCK_OFF", i, stim)

        else:
            time.sleep(tone_duration)

        log("TRIAL_END", i, stim)

        # inter-trial interval
        iti = random.uniform(2, 3)
        time.sleep(iti)

    log("END", "", "")

# ---------------------------
# GUI FUNCTIONS
# ---------------------------

def start_experiment():

    global tone_duration
    global shock_delay
    global shock_duration
    global sequence
    global iti_min
    global iti_max

    try:
        tone_duration = float(tone_duration_entry.get())
        shock_delay = float(shock_delay_entry.get())
        shock_duration = float(shock_duration_entry.get())

        iti_min = float(iti_min_entry.get())
        iti_max = float(iti_max_entry.get())

        sequence = [
            x.strip().upper()
            for x in sequence_entry.get().split(",")
        ]

        status_label.config(
            text=f"Running {len(sequence)} trials..."
        )

        threading.Thread(
            target=run_experiment,
            daemon=True
        ).start()

    except Exception as e:
        status_label.config(text=f"Error: {e}")


# ---------------------------
# GUI
# ---------------------------

root = tk.Tk()
root.title("Fear Conditioning Controller")

# Tone Duration
tk.Label(root, text="Tone Duration (s)").grid(
    row=0, column=0, padx=5, pady=5
)

tone_duration_entry = tk.Entry(root)
tone_duration_entry.insert(0, "30")
tone_duration_entry.grid(row=0, column=1)

# Shock Delay
tk.Label(root, text="Shock Delay (s)").grid(
    row=1, column=0, padx=5, pady=5
)

shock_delay_entry = tk.Entry(root)
shock_delay_entry.insert(0, "28")
shock_delay_entry.grid(row=1, column=1)

# Shock Duration
tk.Label(root, text="Shock Duration (s)").grid(
    row=2, column=0, padx=5, pady=5
)

shock_duration_entry = tk.Entry(root)
shock_duration_entry.insert(0, "2")
shock_duration_entry.grid(row=2, column=1)

# ITI Min
tk.Label(root, text="ITI Min (s)").grid(
    row=3, column=0, padx=5, pady=5
)

iti_min_entry = tk.Entry(root)
iti_min_entry.insert(0, "60")
iti_min_entry.grid(row=3, column=1)

# ITI Max
tk.Label(root, text="ITI Max (s)").grid(
    row=4, column=0, padx=5, pady=5
)

iti_max_entry = tk.Entry(root)
iti_max_entry.insert(0, "120")
iti_max_entry.grid(row=4, column=1)

# Sequence
tk.Label(root, text="Sequence").grid(
    row=5, column=0, padx=5, pady=5
)

sequence_entry = tk.Entry(root, width=40)
sequence_entry.insert(0, "A,B,A,B,A,C")
sequence_entry.grid(row=5, column=1)

# Status
status_label = tk.Label(root, text="Ready")
status_label.grid(
    row=7,
    column=0,
    columnspan=2,
    pady=10
)

# Start Button
start_btn = tk.Button(
    root,
    text="Start Experiment",
    command=start_experiment
)

start_btn.grid(
    row=6,
    column=0,
    columnspan=2,
    pady=10
)

root.mainloop()
