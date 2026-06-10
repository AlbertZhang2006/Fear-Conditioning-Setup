import tkinter as tk
import threading
import pygame
import serial
import time
import random
import csv
from datetime import datetime

# ---------------------------
# CONFIG
# ---------------------------

ARDUINO_PORT = "COM3"      # Change if needed
BAUD = 115200

# ---------------------------
# AUDIO FILES
# ---------------------------

tone_freqs = {
    "A": 440,
    "B": 550,
    "C": 660
}

# ---------------------------
# INITIALIZE AUDIO
# ---------------------------

pygame.mixer.init()

# ---------------------------
# INITIALIZE ARDUINO
# ---------------------------

try:
    ser = serial.Serial(ARDUINO_PORT, BAUD, timeout=1)
    time.sleep(2)
    arduino_connected = True
except Exception as e:
    print("Arduino connection failed:", e)
    arduino_connected = False

# ---------------------------
# DEFAULT PARAMETERS
# ---------------------------

tone_duration = 30
shock_delay = 28
shock_duration = 2

iti_min = 60
iti_max = 120

sequence = ["A", "B", "A", "B", "A", "C"]

# ---------------------------
# LOGGING
# ---------------------------

log_file = (
    f"experiment_"
    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)

with open(log_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "timestamp",
        "event",
        "trial",
        "stimulus"
    ])


def log(event, trial, stim):

    with open(log_file, "a", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            time.time(),
            event,
            trial,
            stim
        ])

    print(event, trial, stim)


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
# AUDIO CONTROL
# ---------------------------

def play_tone(file):

    pygame.mixer.music.load(file)
    pygame.mixer.music.play()


# ---------------------------
# EXPERIMENT
# ---------------------------

def run_experiment():

    status_label.config(text="Running...")

    log("START", "", "")

    for i, stim in enumerate(sequence):

        status_label.config(
            text=f"Trial {i+1}/{len(sequence)} : {stim}"
        )

        log("TRIAL_START", i, stim)

        play_tone(tone_files[stim])

        log("TONE_ON", i, stim)

        start_time = time.time()

        # Tone A gets shock
        if stim == "A":

            while time.time() - start_time < shock_delay:
                time.sleep(0.01)

            shock_on()

            log("SHOCK_ON", i, stim)

            time.sleep(shock_duration)

            shock_off()

            log("SHOCK_OFF", i, stim)

            remaining = tone_duration - (
                shock_delay + shock_duration
            )

            if remaining > 0:
                time.sleep(remaining)

        else:

            time.sleep(tone_duration)

        log("TRIAL_END", i, stim)

        iti = random.uniform(
            iti_min,
            iti_max
        )

        log(
            f"ITI_{iti:.1f}s",
            i,
            stim
        )

        time.sleep(iti)

    log("END", "", "")

    status_label.config(
        text="Experiment Complete"
    )


# ---------------------------
# GUI START FUNCTION
# ---------------------------

def start_experiment():

    global tone_duration
    global shock_delay
    global shock_duration
    global iti_min
    global iti_max
    global sequence

    try:

        tone_duration = float(
            tone_duration_entry.get()
        )

        shock_delay = float(
            shock_delay_entry.get()
        )

        shock_duration = float(
            shock_duration_entry.get()
        )

        iti_min = float(
            iti_min_entry.get()
        )

        iti_max = float(
            iti_max_entry.get()
        )

        sequence = [
            x.strip().upper()
            for x in sequence_entry.get().split(",")
        ]

        threading.Thread(
            target=run_experiment,
            daemon=True
        ).start()

    except Exception as e:

        status_label.config(
            text=f"Error: {e}"
        )


# ---------------------------
# GUI
# ---------------------------

root = tk.Tk()
root.title("Fear Conditioning Controller")

# Tone Duration

tk.Label(
    root,
    text="Tone Duration (s)"
).grid(row=0, column=0, padx=5, pady=5)

tone_duration_entry = tk.Entry(root)
tone_duration_entry.insert(0, "30")
tone_duration_entry.grid(row=0, column=1)

# Shock Delay

tk.Label(
    root,
    text="Shock Delay (s)"
).grid(row=1, column=0, padx=5, pady=5)

shock_delay_entry = tk.Entry(root)
shock_delay_entry.insert(0, "28")
shock_delay_entry.grid(row=1, column=1)

# Shock Duration

tk.Label(
    root,
    text="Shock Duration (s)"
).grid(row=2, column=0, padx=5, pady=5)

shock_duration_entry = tk.Entry(root)
shock_duration_entry.insert(0, "2")
shock_duration_entry.grid(row=2, column=1)

# ITI Min

tk.Label(
    root,
    text="ITI Min (s)"
).grid(row=3, column=0, padx=5, pady=5)

iti_min_entry = tk.Entry(root)
iti_min_entry.insert(0, "60")
iti_min_entry.grid(row=3, column=1)

# ITI Max

tk.Label(
    root,
    text="ITI Max (s)"
).grid(row=4, column=0, padx=5, pady=5)

iti_max_entry = tk.Entry(root)
iti_max_entry.insert(0, "120")
iti_max_entry.grid(row=4, column=1)

# Sequence

tk.Label(
    root,
    text="Sequence"
).grid(row=5, column=0, padx=5, pady=5)

sequence_entry = tk.Entry(root, width=40)
sequence_entry.insert(
    0,
    "A,B,A,B,A,C"
)
sequence_entry.grid(row=5, column=1)

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

# Status

status_label = tk.Label(
    root,
    text="Ready"
)

status_label.grid(
    row=7,
    column=0,
    columnspan=2,
    pady=10
)

root.mainloop()
