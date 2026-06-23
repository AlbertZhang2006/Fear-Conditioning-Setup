import csv
import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
import pandas as pd

EPOCH_THRESHOLD = 1e6  # values above this are treated as absolute Unix timestamps
TONE_ID_TO_LETTER = {"0": "A", "1": "B", "2": "C"}
TRIAL_TABLE_SUFFIX = "_Trial Data Table.csv"
SUMMARY_TABLE_SUFFIX = "_Experiment Summary.csv"

WHITE = (255, 255, 255)
PHASE_COLOR_BGR = {
    "Tone": (0, 165, 255),
    "Shock": (0, 0, 255),
    "ITI": (200, 200, 200),
    "Start delay": (200, 200, 200),
    "Trial": (0, 165, 255),
    "Idle": (200, 200, 200),
}


def tokenize(name):
    name = re.sub(r"(?<!^)(?=[A-Z])", " ", str(name))
    return [p.lower() for p in re.split(r"[^A-Za-z0-9]+", name) if p]


def find_header_row(rows):
    for i, row in enumerate(rows):
        cells = [str(c).strip().lower() for c in row]
        if any("trial" in c for c in cells) and any("tone" in c for c in cells):
            return i
    return 0


def find_start_timestamp(rows, header_idx):
    for row in rows[:header_idx]:
        if len(row) >= 2 and row[0].strip().lower() == "starttimestamp":
            try:
                return float(row[1])
            except ValueError:
                return None
    return None


def find_metadata_float(rows, key):
    key = key.strip().lower()
    for row in rows:
        if len(row) >= 2 and str(row[0]).strip().lower() == key:
            return to_float(row[1])
    return None


def find_event_timestamp(rows, event_name):
    event_name = event_name.strip().upper()
    timestamp_idx = None
    event_idx = None

    for row in rows:
        normalized = [str(c).strip().lower() for c in row]
        if "timestamp" in normalized and "event" in normalized:
            timestamp_idx = normalized.index("timestamp")
            event_idx = normalized.index("event")
            continue

        if timestamp_idx is None or event_idx is None:
            continue
        if len(row) <= max(timestamp_idx, event_idx):
            continue
        if str(row[event_idx]).strip().upper() == event_name:
            return to_float(row[timestamp_idx])

    return None


def paired_experiment_summary_path(csv_path):
    folder = os.path.dirname(csv_path)
    filename = os.path.basename(csv_path)
    if filename.endswith(TRIAL_TABLE_SUFFIX):
        paired = filename[: -len(TRIAL_TABLE_SUFFIX)] + SUMMARY_TABLE_SUFFIX
        return os.path.join(folder, paired)
    return None


def load_paired_experiment_summary(csv_path):
    summary_path = paired_experiment_summary_path(csv_path)
    if not summary_path or not os.path.isfile(summary_path):
        return []

    with open(summary_path, newline="", encoding="utf-8-sig") as f:
        return list(csv.reader(f))


def find_video_start_timestamp(csv_path, rows, header_idx, experiment_start_ts):
    summary_rows = load_paired_experiment_summary(csv_path)

    camera_on_ts = find_event_timestamp(summary_rows, "CAMERA_ON")
    if camera_on_ts is not None:
        return camera_on_ts

    start_delay = find_metadata_float(summary_rows, "START_DELAY_SECONDS")
    if start_delay is None:
        start_delay = find_metadata_float(rows[:header_idx], "START_DELAY_SECONDS")
    if experiment_start_ts is not None and start_delay is not None:
        return experiment_start_ts - start_delay

    return experiment_start_ts


def load_table(csv_path):
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        raw_rows = list(csv.reader(f))

    header_idx = find_header_row(raw_rows)
    start_ts = find_start_timestamp(raw_rows, header_idx)
    video_start_ts = find_video_start_timestamp(csv_path, raw_rows, header_idx, start_ts)

    df = pd.read_csv(csv_path, skiprows=header_idx, encoding="utf-8-sig")
    df.columns = [str(c).strip() for c in df.columns]
    return df, video_start_ts


def classify_event_columns(columns, keyword):
    identity_cols, onset_cols, offset_cols, duration_cols = [], [], [], []
    for col in columns:
        tokens = set(tokenize(col))
        if keyword not in tokens:
            continue
        if "duration" in tokens:
            duration_cols.append(col)
        elif tokens & {"on", "onset", "start"}:
            onset_cols.append(col)
        elif tokens & {"off", "offset", "end", "stop"}:
            offset_cols.append(col)
        else:
            identity_cols.append(col)
    return identity_cols, onset_cols, offset_cols, duration_cols


def find_trial_column(columns):
    for col in columns:
        tokens = set(tokenize(col))
        if "trial" in tokens and not ({"tone", "shock", "iti"} & tokens):
            return col
    return None


def find_iti_columns(columns):
    start_col, stop_col = None, None
    for col in columns:
        if "iti" not in str(col).lower():
            continue
        tokens = set(tokenize(col))
        if tokens & {"start", "on", "onset"}:
            start_col = col
        elif tokens & {"stop", "end", "off", "offset"}:
            stop_col = col
    return start_col, stop_col


def tone_letter(value):
    text = str(value).strip()
    if text.upper() in ("A", "B", "C"):
        return text.upper()
    try:
        text = str(int(float(text)))
    except ValueError:
        pass
    return TONE_ID_TO_LETTER.get(text)


def to_float(value):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def extract_trial_timeline(csv_path):
    df, start_ts = load_table(csv_path)
    columns = df.columns

    tone_identity_cols, tone_onset_cols, tone_offset_cols, tone_duration_cols = classify_event_columns(
        columns, "tone"
    )
    shock_identity_cols, shock_onset_cols, shock_offset_cols, _ = classify_event_columns(columns, "shock")
    trial_col = find_trial_column(columns)
    iti_start_col, iti_stop_col = find_iti_columns(columns)

    if not tone_identity_cols or not tone_onset_cols or not (tone_offset_cols or tone_duration_cols):
        raise ValueError(
            "Could not find tone identity/onset/offset columns in this CSV. "
            f"Columns present: {list(columns)}"
        )

    tone_identity_col = tone_identity_cols[0]
    tone_onset_col = tone_onset_cols[0]
    tone_offset_col = tone_offset_cols[0] if tone_offset_cols else None
    tone_duration_col = tone_duration_cols[0] if tone_duration_cols else None
    shock_identity_col = shock_identity_cols[0] if shock_identity_cols else None
    shock_onset_col = shock_onset_cols[0] if shock_onset_cols else None
    shock_offset_col = shock_offset_cols[0] if shock_offset_cols else None

    timeline = []
    for position, (_, row) in enumerate(df.iterrows()):
        letter = tone_letter(row[tone_identity_col])
        if letter is None:
            continue

        tone_on = to_float(row[tone_onset_col])
        if tone_on is None:
            continue

        tone_off = to_float(row[tone_offset_col]) if tone_offset_col is not None else None
        if tone_off is None and tone_duration_col is not None:
            duration = to_float(row[tone_duration_col])
            if duration is not None:
                tone_off = tone_on + duration
        if tone_off is None:
            continue

        shock_on = to_float(row[shock_onset_col]) if shock_onset_col is not None else None
        shock_off = to_float(row[shock_offset_col]) if shock_offset_col is not None else None
        shock_present = shock_on is not None and shock_off is not None
        if shock_identity_col is not None and not shock_present:
            flag = to_float(row[shock_identity_col])
            shock_present = bool(flag) if flag is not None else shock_present

        iti_start = to_float(row[iti_start_col]) if iti_start_col is not None else None
        iti_stop = to_float(row[iti_stop_col]) if iti_stop_col is not None else None

        if trial_col is not None:
            trial_value = to_float(row[trial_col])
            trial_number = int(trial_value) if trial_value is not None else position + 1
        else:
            trial_number = position + 1

        timeline.append(
            {
                "trial_number": trial_number,
                "tone": letter,
                "tone_on": tone_on,
                "tone_off": tone_off,
                "shock_present": shock_present,
                "shock_on": shock_on,
                "shock_off": shock_off,
                "iti_start": iti_start,
                "iti_stop": iti_stop,
            }
        )

    if not timeline:
        raise ValueError("No trial rows with a tone onset/offset were found in this CSV.")

    timeline.sort(key=lambda item: item["tone_on"])

    all_values = [
        v
        for item in timeline
        for v in (
            item["tone_on"],
            item["tone_off"],
            item["shock_on"],
            item["shock_off"],
            item["iti_start"],
            item["iti_stop"],
        )
        if v is not None
    ]
    if all_values and max(all_values) > EPOCH_THRESHOLD:
        reference = start_ts if start_ts is not None else min(all_values)
        for item in timeline:
            for key in ("tone_on", "tone_off", "shock_on", "shock_off", "iti_start", "iti_stop"):
                if item[key] is not None:
                    item[key] -= reference

    return timeline


def stage_at(t, timeline):
    if not timeline or t < timeline[0]["tone_on"]:
        return {
            "phase": "Start delay",
            "trial_number": None,
            "total_trials": len(timeline),
            "tone": None,
            "shock_present": False,
            "shock_active": False,
            "shock_off": None,
        }

    trial = timeline[0]
    for item in timeline:
        if t < item["tone_on"]:
            break
        trial = item

    shock_active = (
        trial["shock_on"] is not None
        and trial["shock_off"] is not None
        and trial["shock_on"] <= t <= trial["shock_off"]
    )

    if shock_active:
        phase = "Shock"
    elif t <= trial["tone_off"]:
        phase = "Tone"
    elif (
        trial["iti_start"] is not None
        and trial["iti_stop"] is not None
        and trial["iti_start"] <= t <= trial["iti_stop"]
    ):
        phase = "ITI"
    elif trial is timeline[-1] and trial["iti_stop"] is None:
        phase = "Idle"
    elif trial["iti_stop"] is not None and t > trial["iti_stop"]:
        phase = "Idle"
    else:
        phase = "Trial"

    return {
        "phase": phase,
        "trial_number": trial["trial_number"],
        "total_trials": len(timeline),
        "tone": trial["tone"],
        "shock_present": trial["shock_present"],
        "shock_active": shock_active,
        "shock_off": trial["shock_off"],
    }


def format_time(seconds):
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    return f"{minutes:02d}:{secs:06.3f}"


def build_tracker_lines(t, state):
    phase = state["phase"]
    lines = [
        (f"Stopwatch  {format_time(t)}", WHITE),
        (
            "Trial -- / --"
            if state["trial_number"] is None
            else f"Trial {state['trial_number']} / {state['total_trials']}",
            WHITE,
        ),
        (f"Phase: {phase}", PHASE_COLOR_BGR.get(phase, WHITE)),
        (f"Tone: {state['tone'] or '--'}", WHITE),
    ]

    if not state["shock_present"]:
        lines.append(("Shock: none", WHITE))
    elif state["shock_active"]:
        remaining = max(0.0, state["shock_off"] - t)
        lines.append((f"Shock: ON ({remaining:.1f}s left)", PHASE_COLOR_BGR["Shock"]))
    else:
        lines.append(("Shock: armed", WHITE))

    return lines


def draw_tracker(frame, lines, width, height):
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.45, height / 1080 * 0.6)
    thickness = 2 if font_scale >= 0.7 else 1
    line_h = int(round(28 * font_scale / 0.6))
    pad = int(round(12 * font_scale / 0.6))

    text_sizes = [cv2.getTextSize(text, font, font_scale, thickness)[0] for text, _ in lines]
    box_w = max(w for w, h in text_sizes) + pad * 2
    box_h = line_h * len(lines) + pad * 2

    x0 = max(0, width - box_w - 10)
    y0 = 10

    overlay = frame.copy()
    cv2.rectangle(overlay, (x0, y0), (x0 + box_w, y0 + box_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    for i, (text, color) in enumerate(lines):
        y = y0 + pad + line_h * (i + 1) - int(line_h * 0.25)
        cv2.putText(frame, text, (x0 + pad, y), font, font_scale, color, thickness, cv2.LINE_AA)


def annotate_video(video_path, timeline, progress_callback=None):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    base, ext = os.path.splitext(video_path)
    out_path = f"{base}_annotated{ext or '.mp4'}"

    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Could not open video writer for: {out_path}")

    progress_step = max(1, total_frames // 200) if total_frames else 30

    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        t = frame_idx / fps
        state = stage_at(t, timeline)
        lines = build_tracker_lines(t, state)
        draw_tracker(frame, lines, width, height)

        writer.write(frame)
        frame_idx += 1

        if progress_callback and (frame_idx % progress_step == 0 or frame_idx == total_frames):
            progress_callback(frame_idx, total_frames)

    cap.release()
    writer.release()
    return out_path


class AnnotateVideoGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tone Annotation Tool")
        self.root.minsize(900, 220)
        self.video_path = tk.StringVar()
        self.csv_path = tk.StringVar(value="No CSV selected")
        self.video_path.set("No video selected")
        self.status = tk.StringVar(value="Select a video and a CSV file to begin.")
        self._build()

    def _build(self):
        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        tk.Button(frame, text="Select Video (.mp4)", command=self.select_video).grid(
            row=0, column=0, sticky="w", pady=4
        )
        tk.Label(
            frame,
            textvariable=self.video_path,
            anchor="w",
            justify="left",
            wraplength=720,
        ).grid(
            row=0, column=1, sticky="ew", padx=(8, 0)
        )

        tk.Button(frame, text="Select CSV", command=self.select_csv).grid(
            row=1, column=0, sticky="w", pady=4
        )
        tk.Label(
            frame,
            textvariable=self.csv_path,
            anchor="w",
            justify="left",
            wraplength=720,
        ).grid(
            row=1, column=1, sticky="ew", padx=(8, 0)
        )

        self.run_btn = tk.Button(frame, text="Process Video", command=self.start_processing)
        self.run_btn.grid(row=2, column=0, columnspan=2, pady=(10, 4))

        self.progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate", length=380)
        self.progress.grid(row=3, column=0, columnspan=2, pady=(0, 6))

        tk.Label(
            frame, textvariable=self.status, anchor="w", justify="left", wraplength=440
        ).grid(row=4, column=0, columnspan=2, sticky="w")

    def select_video(self):
        path = filedialog.askopenfilename(
            title="Select video file", filetypes=[("MP4 video", "*.mp4")]
        )
        if path:
            self.video_path.set(path)

    def select_csv(self):
        path = filedialog.askopenfilename(
            title="Select CSV file", filetypes=[("CSV files", "*.csv")]
        )
        if path:
            self.csv_path.set(path)

    def start_processing(self):
        video = self.video_path.get()
        csv_file = self.csv_path.get()
        if not os.path.isfile(video) or not os.path.isfile(csv_file):
            messagebox.showwarning("Missing input", "Please select both a video file and a CSV file.")
            return

        self.run_btn.config(state="disabled")
        self.progress.config(mode="determinate")
        self.progress["value"] = 0
        self.status.set("Reading CSV...")

        threading.Thread(target=self._run, args=(video, csv_file), daemon=True).start()

    def _run(self, video, csv_file):
        try:
            timeline = extract_trial_timeline(csv_file)
            self._set_status(f"Loaded {len(timeline)} trial(s). Processing video...")

            def on_progress(frame_idx, total_frames):
                pct = (frame_idx / total_frames) * 100 if total_frames else 0
                self.root.after(0, self._update_progress, pct, frame_idx, total_frames)

            out_path = annotate_video(video, timeline, progress_callback=on_progress)
            self._set_status(f"Done. Saved annotated video to:\n{out_path}")
        except Exception as exc:
            self._set_status(f"Error: {exc}")
            messagebox.showerror("Processing failed", str(exc))
        finally:
            self.root.after(0, lambda: self.run_btn.config(state="normal"))

    def _update_progress(self, pct, frame_idx, total_frames):
        self.progress["value"] = pct
        if total_frames:
            self.status.set(f"Processing frame {frame_idx}/{total_frames} ({pct:.1f}%)")
        else:
            self.status.set(f"Processing frame {frame_idx}...")

    def _set_status(self, text):
        self.root.after(0, lambda: self.status.set(text))

    def run(self):
        self.root.mainloop()


def main():
    AnnotateVideoGUI().run()


if __name__ == "__main__":
    main()
