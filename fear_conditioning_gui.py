import os
import csv
import time
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

import serial
import winsound

# =====================================================
# CONFIG
# =====================================================

ARDUINO_PORT = "COM5"
BAUD = 115200

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

tone_files = {
    "A": os.path.join(SCRIPT_DIR, "BlueNoise,SR=50k,F=12K-20K.wav"),
    "B": os.path.join(SCRIPT_DIR, "BrownNoise,SR=50k,F=4K-8K.wav"),
    "C": os.path.join(SCRIPT_DIR, "WhiteNoise,SR=50k,F=4K-20K.wav"),
}

try:
    ser = serial.Serial(ARDUINO_PORT, BAUD, timeout=1)
    time.sleep(2)
except:
    ser = None
    print("Arduino not connected")

# =====================================================
# LOGGING
# =====================================================

log_file = f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

def log(event, trial="", stim=""):
    with open(log_file, "a", newline="") as f:
        csv.writer(f).writerow([time.time(), event, trial, stim])

with open(log_file, "w", newline="") as f:
    csv.writer(f).writerow(["timestamp", "event", "trial", "stimulus"])

# =====================================================
# HARDWARE
# =====================================================

def shock_on():
    if ser:
        ser.write(b"SHOCK_ON\n")
        ser.flush()

def shock_off():
    if ser:
        ser.write(b"SHOCK_OFF\n")
        ser.flush()

# =====================================================
# AUDIO
# =====================================================

def tone_on(stim):
    path = tone_files.get(stim)
    if path and os.path.exists(path):
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)

def tone_off():
    winsound.PlaySound(None, winsound.SND_PURGE)

# =====================================================
# GLOBAL STATE
# =====================================================

stop_event = threading.Event()
running = False

# =====================================================
# TRIAL PARSING
# =====================================================

def get_trials():
    trials = []
    for row in table.get_children():
        v = table.item(row)["values"]
        shock_start = v[2]
        trials.append({
            "tone": v[0],
            "tone_duration": float(v[1]),
            "shock_start": None if shock_start == "" else float(shock_start),
            "shock_duration": float(v[3])
        })
    return trials

# =====================================================
# EXPERIMENT ENGINE
# =====================================================

def run_experiment():
    global running
    running = True
    stop_event.clear()

    try:
        trials = get_trials()
        iti_min = float(iti_min_var.get())
        iti_max = float(iti_max_var.get())

        log("START")

        for i, t in enumerate(trials):
            if stop_event.is_set():
                break

            status.set(f"Trial {i+1}/{len(trials)}")

            start = time.time()
            tone_stop_time = start + t["tone_duration"]
            shock_start_time = (
                start + t["shock_start"]
                if t["shock_start"] is not None
                else None
            )
            shock_stop_time = (
                shock_start_time + t["shock_duration"]
                if shock_start_time is not None
                else None
            )

            tone_on(t["tone"])
            log("TONE_ON", i, t["tone"])

            tone_stopped = False
            shock_started = False
            shock_stopped = shock_start_time is None

            while not stop_event.is_set() and not (tone_stopped and shock_stopped):
                now = time.time()

                if not tone_stopped and now >= tone_stop_time:
                    tone_off()
                    log("TONE_OFF", i, t["tone"])
                    tone_stopped = True

                if shock_start_time is not None and not shock_started and now >= shock_start_time:
                    shock_on()
                    log("SHOCK_ON", i, t["tone"])
                    shock_started = True

                if shock_started and not shock_stopped and now >= shock_stop_time:
                    shock_off()
                    log("SHOCK_OFF", i, t["tone"])
                    shock_stopped = True

                next_times = []
                if not tone_stopped:
                    next_times.append(tone_stop_time)
                if shock_start_time is not None and not shock_started:
                    next_times.append(shock_start_time)
                if shock_started and not shock_stopped:
                    next_times.append(shock_stop_time)

                if next_times:
                    time.sleep(min(0.005, max(0.001, min(next_times) - time.time())))

            if not tone_stopped:
                tone_off()
                log("TONE_OFF", i, t["tone"])

            if shock_started and not shock_stopped:
                shock_off()
                log("SHOCK_OFF", i, t["tone"])

            log("TRIAL_END", i, t["tone"])

            iti = random.uniform(iti_min, iti_max)
            status.set(f"ITI {iti:.1f}s")
            stop_event.wait(iti)

        log("END")

    finally:
        tone_off()
        shock_off()
        running = False
        status.set("Idle")
        start_btn.config(state="normal")
        stop_btn.config(state="disabled")

# =====================================================
# CONTROL
# =====================================================

def start():
    if running:
        return
    start_btn.config(state="disabled")
    stop_btn.config(state="normal")
    threading.Thread(target=run_experiment, daemon=True).start()

def stop():
    stop_event.set()

# =====================================================
# TABLE EDITING
# =====================================================

def edit_cell(event):
    row = table.identify_row(event.y)
    col = table.identify_column(event.x)
    if not row:
        return

    x, y, w, h = table.bbox(row, col)
    idx = int(col[1:]) - 1
    values = list(table.item(row)["values"])

    if idx == 0:
        cb = ttk.Combobox(root, values=["A","B","C"], state="readonly")
        cb.place(x=x+table.winfo_x(), y=y+table.winfo_y(), width=w, height=h)
        cb.set(values[idx])

        def save(e=None):
            values[idx] = cb.get()
            table.item(row, values=values)
            cb.destroy()

        cb.bind("<<ComboboxSelected>>", save)
        cb.focus()

    else:
        e = tk.Entry(root)
        e.place(x=x+table.winfo_x(), y=y+table.winfo_y(), width=w, height=h)
        e.insert(0, values[idx])

        def save(e2=None):
            values[idx] = e.get()
            table.item(row, values=values)
            e.destroy()

        e.bind("<Return>", save)
        e.bind("<FocusOut>", save)
        e.focus()

# =====================================================
# SAVE / LOAD
# =====================================================

def save_protocol():
    file = filedialog.asksaveasfilename(defaultextension=".csv")
    if not file:
        return

    with open(file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ITI_MIN", iti_min_var.get()])
        w.writerow(["ITI_MAX", iti_max_var.get()])
        w.writerow([])
        w.writerow(["Tone","ToneDuration","ShockStart","ShockDuration"])

        for r in table.get_children():
            w.writerow(table.item(r)["values"])

def load_protocol():
    file = filedialog.askopenfilename(filetypes=[("CSV","*.csv")])
    if not file:
        return

    for r in table.get_children():
        table.delete(r)

    with open(file) as f:
        r = csv.reader(f)
        rows = list(r)

    global iti_min_var, iti_max_var

    iti_min_var.set(rows[0][1])
    iti_max_var.set(rows[1][1])

    start_idx = rows.index([]) + 2

    for row in rows[start_idx:]:
        table.insert("", "end", values=row)

# =====================================================
# GUI
# =====================================================

root = tk.Tk()
root.title("Fear Conditioning Controller")

status = tk.StringVar(value="Idle")

top = tk.Frame(root)
top.pack()

iti_min_var = tk.StringVar(value="2")
iti_max_var = tk.StringVar(value="3")

tk.Label(top, text="ITI Min").grid(row=0, column=0)
tk.Entry(top, textvariable=iti_min_var, width=6).grid(row=0, column=1)

tk.Label(top, text="ITI Max").grid(row=0, column=2)
tk.Entry(top, textvariable=iti_max_var, width=6).grid(row=0, column=3)

cols = ["Tone","ToneDuration","ShockStart","ShockDuration"]

table = ttk.Treeview(root, columns=cols, show="headings")
for c in cols:
    table.heading(c, text=c)
    table.column(c, width=120)

table.pack(fill="both", expand=True)
table.bind("<Double-1>", edit_cell)

table.insert("", "end", values=("A",10,8,2))

btns = tk.Frame(root)
btns.pack()

tk.Button(btns, text="Add Trial",
          command=lambda: table.insert("", "end", values=("A",5,"",0))).pack(side="left")

tk.Button(btns, text="Save", command=save_protocol).pack(side="left")
tk.Button(btns, text="Load", command=load_protocol).pack(side="left")

start_btn = tk.Button(btns, text="Start", command=start)
start_btn.pack(side="left")

stop_btn = tk.Button(btns, text="Stop", command=stop, state="disabled")
stop_btn.pack(side="left")

tk.Label(root, textvariable=status).pack()

root.mainloop()

