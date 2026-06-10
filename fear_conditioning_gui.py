import tkinter as tk
import threading
import serial
import time
import random
import csv
import os
import winsound
from datetime import datetime

# ---------------------------
# CONFIG
# ---------------------------

ARDUINO_PORT = "COM5"
BAUD = 115200

# Put WAV files in SAME folder as this script
tone_files = {
    "A": "WhiteNoise,SR=50k,F=4K-20K.wav",
    "B": "BrownNoise,SR=50k,F=4K-8K.wav",
    "C": "BlueNoise,SR=50k,F=12K-20K.wav"
}

# ---------------------------
# ARDUINO SETUP
# ---------------------------

try:
    ser = serial.Serial(ARDUINO_PORT, BAUD, timeout=1)
    time.sleep(2)
    arduino_connected = True
except Exception as e:
    print("Arduino not connected:", e)
    arduino_connected = False

# ---------------------------
# PARAMETERS
# ---------------------------

tone_duration = 5
shock_delay = 2
shock_duration = 2

iti_min = 1
iti_max = 3

sequence = ["A", "B", "A", "B", "A", "C"]

# ---------------------------
# LOGGING
# ---------------------------

log_file = f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

with open(log_file, "w", newline="") as f:
    csv.writer(f).writerow(["time", "event", "trial", "stimulus"])

def log(event, trial, stim):
    with open(log_file, "a", newline="") as f:
        csv.writer(f).writerow([time.time(), event, trial, stim])

# ---------------------------
# ARDUINO CONTROL
# ---------------------------

def shock_on():
    if arduino_connected:
        ser.write(b"SHOCK_ON\n")

def shock_off():
    if arduino_connected:
        ser.write(b"SHOCK_OFF\n")

# ---------------------------
# AUDIO (DEBUG SAFE)
# ---------------------------

def play_tone(file):
    try:
        path = os.path.abspath(file)
        print("Playing:", path)

        if not os.path.exists(path):
            print("ERROR: FILE NOT FOUND ->", path)
            return

        # stop any previous sound
        winsound.PlaySound(None, winsound.SND_PURGE)

        # BLOCKING playback (IMPORTANT for debugging reliability)
        winsound.PlaySound(path, winsound.SND_FILENAME)

    except Exception as e:
        print("AUDIO ERROR:", e)

# ---------------------------
# EXPERIMENT LOOP
# ---------------------------

def run_experiment():
    status_label.config(text="Running...")

    log("START", "", "")

    for i, stim in enumerate(sequence):

        status_label.config(text=f"Trial {i+1}/{len(sequence)}: {stim}")
        log("TRIAL_START", i, stim)

        play_tone(tone_files[stim])
        log("TONE_ON", i, stim)

        start = time.time()

        if stim == "A":

            while time.time() - start < shock_delay:
                time.sleep(0.01)

            shock_on()
            log("SHOCK_ON", i, stim)

            time.sleep(shock_duration)

            shock_off()
            log("SHOCK_OFF", i, stim)

            remaining = tone_duration - (shock_delay + shock_duration)
            if remaining > 0:
                time.sleep(remaining)

        else:
            time.sleep(tone_duration)

        log("TRIAL_END", i, stim)

        iti = random.uniform(iti_min, iti_max)
        log(f"ITI_{iti:.1f}", i, stim)

        time.sleep(iti)

    log("END", "", "")
    status_label.config(text="Done")

# ---------------------------
# START EXPERIMENT
# ---------------------------

def start_experiment():

    global tone_duration, shock_delay, shock_duration
    global iti_min, iti_max, sequence

    tone_duration = float(tone_entry.get())
    shock_delay = float(shock_entry.get())
    shock_duration = float(shockdur_entry.get())

    iti_min = float(itimin_entry.get())
    iti_max = float(itimax_entry.get())

    sequence = [
        x.strip().upper()
        for x in seq_entry.get().split(",")
    ]

    threading.Thread(
        target=run_experiment,
        daemon=True
    ).start()

# ---------------------------
# GUI
# ---------------------------

root = tk.Tk()
root.title("Fear Conditioning Controller")

tk.Label(root, text="Tone Duration").grid(row=0, column=0)
tone_entry = tk.Entry(root)
tone_entry.insert(0, "30")
tone_entry.grid(row=0, column=1)

tk.Label(root, text="Shock Delay").grid(row=1, column=0)
shock_entry = tk.Entry(root)
shock_entry.insert(0, "28")
shock_entry.grid(row=1, column=1)

tk.Label(root, text="Shock Duration").grid(row=2, column=0)
shockdur_entry = tk.Entry(root)
shockdur_entry.insert(0, "2")
shockdur_entry.grid(row=2, column=1)

tk.Label(root, text="ITI Min").grid(row=3, column=0)
itimin_entry = tk.Entry(root)
itimin_entry.insert(0, "60")
itimin_entry.grid(row=3, column=1)

tk.Label(root, text="ITI Max").grid(row=4, column=0)
itimax_entry = tk.Entry(root)
itimax_entry.insert(0, "120")
itimax_entry.grid(row=4, column=1)

tk.Label(root, text="Sequence").grid(row=5, column=0)
seq_entry = tk.Entry(root, width=40)
seq_entry.insert(0, "A,B,A,B,A,C")
seq_entry.grid(row=5, column=1)

start_btn = tk.Button(root, text="Start Experiment", command=start_experiment)
start_btn.grid(row=6, column=0, columnspan=2)

status_label = tk.Label(root, text="Ready")
status_label.grid(row=7, column=0, columnspan=2)

root.mainloop()
