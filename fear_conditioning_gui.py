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
auto_export_folder = None
auto_export_file = None
auto_export_active = False
export_lock = threading.Lock()
experiment_events = []
trial_summaries = []
protocol_snapshot = []
protocol_iti_min = ""
protocol_iti_max = ""
last_experiment_events = []
last_trial_summaries = []
last_protocol_snapshot = []
last_protocol_iti_min = ""
last_protocol_iti_max = ""

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

def get_protocol_rows():
    return [table.item(row)["values"] for row in table.get_children()]

# =====================================================
# EXPORT
# =====================================================

def timestamp_strings(ts=None):
    ts = time.time() if ts is None else ts
    return ts, datetime.fromtimestamp(ts).isoformat(timespec="milliseconds")

def choose_auto_export_folder():
    global auto_export_folder
    if running:
        messagebox.showwarning("Auto Export Folder", "Stop the experiment before changing the auto export folder.")
        return

    messagebox.showinfo(
        "Auto Export Folder",
        "Choose a folder where the trials will auto export the data to."
    )

    folder = filedialog.askdirectory(title="Choose Auto Export Folder")
    if not folder:
        auto_export_folder = None
        status.set("Auto export disabled")
        return

    auto_export_folder = folder
    status.set(f"Auto export folder: {os.path.basename(folder)}")

def start_auto_export_file():
    global auto_export_file, auto_export_active
    if not auto_export_folder:
        auto_export_file = None
        auto_export_active = False
        return

    auto_export_file = os.path.join(
        auto_export_folder,
        f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}_auto.csv"
    )
    auto_export_active = True
    write_export_file(
        auto_export_file,
        protocol_snapshot,
        experiment_events,
        trial_summaries,
        protocol_iti_min,
        protocol_iti_max
    )

def stop_auto_export_file():
    global auto_export_active
    if auto_export_active and auto_export_file:
        write_export_file(
            auto_export_file,
            protocol_snapshot,
            experiment_events,
            trial_summaries,
            protocol_iti_min,
            protocol_iti_max
        )
    auto_export_active = False

def export_data_manually():
    file = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV", "*.csv")],
        initialfile=f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    if not file:
        return

    if experiment_events:
        write_export_file(
            file,
            protocol_snapshot,
            experiment_events,
            trial_summaries,
            protocol_iti_min,
            protocol_iti_max
        )
        status.set(f"Exported {os.path.basename(file)}")
    elif last_experiment_events:
        write_export_file(
            file,
            last_protocol_snapshot,
            last_experiment_events,
            last_trial_summaries,
            last_protocol_iti_min,
            last_protocol_iti_max
        )
        status.set(f"Exported {os.path.basename(file)}")
    else:
        messagebox.showinfo("Export Data", "No experiment data has been recorded yet.")

def append_event(event, trial="", tone="", detail=""):
    ts, iso = timestamp_strings()
    row = {
        "timestamp": ts,
        "datetime": iso,
        "event": event,
        "trial": trial,
        "tone": tone,
        "detail": detail
    }

    with export_lock:
        experiment_events.append(row)
        if auto_export_active and auto_export_file:
            write_export_file(
                auto_export_file,
                protocol_snapshot,
                experiment_events,
                trial_summaries,
                protocol_iti_min,
                protocol_iti_max
            )

    return row

def add_tone_summary(trial, tone, tone_on_event, tone_off_event):
    duration = tone_off_event["timestamp"] - tone_on_event["timestamp"]
    with export_lock:
        trial_summaries.append({
            "trial": trial,
            "tone": tone,
            "tone_start_datetime": tone_on_event["datetime"],
            "tone_start_timestamp": tone_on_event["timestamp"],
            "tone_stop_datetime": tone_off_event["datetime"],
            "tone_stop_timestamp": tone_off_event["timestamp"],
            "tone_duration_seconds": duration
        })

        if auto_export_active and auto_export_file:
            write_export_file(
                auto_export_file,
                protocol_snapshot,
                experiment_events,
                trial_summaries,
                protocol_iti_min,
                protocol_iti_max
            )

def write_export_file(file, protocol_rows, events, summaries, iti_min_value, iti_max_value):
    with open(file, "w", newline="") as f:
        w = csv.writer(f)

        w.writerow(["ExportCreated", datetime.now().isoformat(timespec="milliseconds")])
        w.writerow(["ITI_MIN", iti_min_value])
        w.writerow(["ITI_MAX", iti_max_value])
        w.writerow([])

        w.writerow(["ProtocolTable"])
        w.writerow(["Trial", "Tone", "ToneDuration", "ShockStart", "ShockDuration"])
        for i, row in enumerate(protocol_rows, start=1):
            w.writerow([i] + list(row))
        w.writerow([])

        w.writerow(["TonePlaybackSummary"])
        w.writerow([
            "Trial",
            "Tone",
            "ToneStartDateTime",
            "ToneStartTimestamp",
            "ToneStopDateTime",
            "ToneStopTimestamp",
            "TonePlayedForSeconds"
        ])
        for summary in summaries:
            w.writerow([
                summary["trial"],
                summary["tone"],
                summary["tone_start_datetime"],
                f"{summary['tone_start_timestamp']:.6f}",
                summary["tone_stop_datetime"],
                f"{summary['tone_stop_timestamp']:.6f}",
                f"{summary['tone_duration_seconds']:.6f}"
            ])
        w.writerow([])

        w.writerow(["EventLog"])
        w.writerow(["DateTime", "Timestamp", "Event", "Trial", "Tone", "Detail"])
        for event in events:
            w.writerow([
                event["datetime"],
                f"{event['timestamp']:.6f}",
                event["event"],
                event["trial"],
                event["tone"],
                event["detail"]
            ])

# =====================================================
# EXPERIMENT ENGINE
# =====================================================

def run_experiment():
    global running, experiment_events, trial_summaries, protocol_snapshot
    global last_experiment_events, last_trial_summaries, last_protocol_snapshot
    global protocol_iti_min, protocol_iti_max
    global last_protocol_iti_min, last_protocol_iti_max
    running = True
    stop_event.clear()
    experiment_events = []
    trial_summaries = []
    protocol_snapshot = get_protocol_rows()
    protocol_iti_min = iti_min_var.get()
    protocol_iti_max = iti_max_var.get()

    try:
        trials = get_trials()
        iti_min = float(protocol_iti_min)
        iti_max = float(protocol_iti_max)
        start_auto_export_file()

        append_event("START", detail=f"trials={len(trials)}")

        for i, t in enumerate(trials):
            if stop_event.is_set():
                break

            trial_number = i + 1
            status.set(f"Trial {trial_number}/{len(trials)}")

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
            tone_on_event = append_event("TONE_ON", trial_number, t["tone"])

            tone_stopped = False
            shock_started = False
            shock_stopped = shock_start_time is None

            while not stop_event.is_set() and not (tone_stopped and shock_stopped):
                now = time.time()

                if not tone_stopped and now >= tone_stop_time:
                    tone_off()
                    tone_off_event = append_event("TONE_OFF", trial_number, t["tone"])
                    add_tone_summary(trial_number, t["tone"], tone_on_event, tone_off_event)
                    tone_stopped = True

                if shock_start_time is not None and not shock_started and now >= shock_start_time:
                    shock_on()
                    append_event("SHOCK_ON", trial_number, t["tone"])
                    shock_started = True

                if shock_started and not shock_stopped and now >= shock_stop_time:
                    shock_off()
                    append_event("SHOCK_OFF", trial_number, t["tone"])
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
                tone_off_event = append_event("TONE_OFF", trial_number, t["tone"], "stopped early")
                add_tone_summary(trial_number, t["tone"], tone_on_event, tone_off_event)

            if shock_started and not shock_stopped:
                shock_off()
                append_event("SHOCK_OFF", trial_number, t["tone"], "stopped early")

            append_event("TRIAL_END", trial_number, t["tone"])

            iti = random.uniform(iti_min, iti_max)
            status.set(f"ITI {iti:.1f}s")
            stop_event.wait(iti)

        if stop_event.is_set():
            append_event("STOPPED")
        else:
            append_event("END")

    finally:
        tone_off()
        shock_off()
        with export_lock:
            last_experiment_events = list(experiment_events)
            last_trial_summaries = list(trial_summaries)
            last_protocol_snapshot = list(protocol_snapshot)
            last_protocol_iti_min = protocol_iti_min
            last_protocol_iti_max = protocol_iti_max
            stop_auto_export_file()
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

def add_trial():
    table.insert("", "end", values=("A",5,"",0))

def delete_trial():
    selected = table.selection()
    if not selected:
        messagebox.showinfo("Delete Trial", "Select one or more trials to delete.")
        return

    if running:
        messagebox.showwarning("Delete Trial", "Stop the experiment before deleting trials.")
        return

    for row in selected:
        table.delete(row)

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

run_btns = tk.Frame(root)
run_btns.pack(pady=(6, 2))

tk.Button(run_btns, text="Add Trial", command=add_trial).pack(side="left", padx=2)
tk.Button(run_btns, text="Delete Trial", command=delete_trial).pack(side="left", padx=2)

start_btn = tk.Button(run_btns, text="Start", command=start)
start_btn.pack(side="left", padx=2)

stop_btn = tk.Button(run_btns, text="Stop", command=stop, state="disabled")
stop_btn.pack(side="left", padx=2)

file_btns = tk.Frame(root)
file_btns.pack(pady=2)

tk.Button(file_btns, text="Save Trial", command=save_protocol).pack(side="left", padx=2)
tk.Button(file_btns, text="Load Previous Trial", command=load_protocol).pack(side="left", padx=2)

export_btns = tk.Frame(root)
export_btns.pack(pady=(2, 6))

tk.Button(export_btns, text="Set Auto Export Folder", command=choose_auto_export_folder).pack(side="left", padx=2)
tk.Button(export_btns, text="Export Data for Trial Held", command=export_data_manually).pack(side="left", padx=2)

tk.Label(root, textvariable=status).pack()

root.after(2000, choose_auto_export_folder)
root.mainloop()

