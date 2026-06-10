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

ARDUINO_PORT = "COM3"
BAUD = 115200

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

tone_files = {
    "A": os.path.join(BASE_DIR, "WhiteNoise,SR=50k,F=4K-20K.wav"),
    "B": os.path.join(BASE_DIR, "BrownNoise,SR=50k,F=4K-8K.wav"),
    "C": os.path.join(BASE_DIR, "BlueNoise,SR=50k,F=12K-20K.wav")
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
shock_delay = 28
shock_duration = 2

iti_min = 60
iti_max = 120

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
# AUDIO (FIXED TIMING CONTROL)
# ---------------------------

def play_tone(file, duration):
    try:
        print("Playing:", file)

        if not os.path.exists(file):
            print("❌ FILE NOT FOUND:", file)
            return

        # stop any previous sound
        winsound.PlaySound(None, winsound.SND_PURGE)

        # start playback (async)
        winsound.PlaySound(file, winsound.SND_ASYNC)

        # enforce experiment-defined duration
        time.sleep(duration)

        # force stop exactly at tone_duration
        winsound.PlaySound(None, winsound.SND_PURGE)

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

        # FIX: tone duration now controlled properly
        play_tone(tone_files[stim], tone_duration)
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
            time.sleep(max(0, tone_duration))

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
# DEBUG CHECK
# ---------------------------

print("WORKING DIR:", os.getcwd())
for k, v in tone_files.items():
    print(k, "->", v, "exists:", os.path.exists(v))

# ---------------------------
# GUI
# ---------------------------

root = tk.Tk()
root.title("Fear Conditioning Controller")

tk.Label(root, text="Tone Duration").grid(row=0, column=0)
tone_entry = tk.Entry(root)
tone_entry.insert(0, "5")
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
