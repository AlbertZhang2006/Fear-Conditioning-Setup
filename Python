import tkinter as tk
import pygame
import serial
import time
import random
import csv
from datetime import datetime

# ---------------------------
# CONFIG
# ---------------------------
ARDUINO_PORT = "COM6"   # change this
BAUD = 115200

pygame.mixer.init()
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
shock_delay = 1
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
def play_tone(file):
    pygame.mixer.music.load(file)
    pygame.mixer.music.play()

def run_experiment():
    log("START", "", "")

    for i, stim in enumerate(sequence):

        log("TRIAL_START", i, stim)

        play_tone(tone_files[stim])
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
# SIMPLE GUI
# ---------------------------
root = tk.Tk()
root.title("Fear Conditioning Controller")

start_btn = tk.Button(root, text="Start Experiment", command=run_experiment)
start_btn.pack(pady=20)

root.mainloop()
