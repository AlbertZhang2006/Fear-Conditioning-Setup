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
DOT_COLOR_BGR = {"A": (0, 0, 255), "B": (255, 0, 0)}


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


def load_table(csv_path):
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        raw_rows = list(csv.reader(f))

    header_idx = find_header_row(raw_rows)
    start_ts = find_start_timestamp(raw_rows, header_idx)

    df = pd.read_csv(csv_path, skiprows=header_idx, encoding="utf-8-sig")
    df.columns = [str(c).strip() for c in df.columns]
    return df, start_ts


def classify_columns(columns):
    identity_cols, onset_cols, offset_cols, duration_cols = [], [], [], []
    for col in columns:
        tokens = set(tokenize(col))
        if "tone" not in tokens:
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


def extract_tone_intervals(csv_path):
    df, start_ts = load_table(csv_path)
    identity_cols, onset_cols, offset_cols, duration_cols = classify_columns(df.columns)

    if not identity_cols or not onset_cols or not (offset_cols or duration_cols):
        raise ValueError(
            "Could not find tone identity/onset/offset columns in this CSV. "
            f"Columns present: {list(df.columns)}"
        )

    identity_col = identity_cols[0]
    onset_col = onset_cols[0]
    offset_col = offset_cols[0] if offset_cols else None
    duration_col = duration_cols[0] if duration_cols else None

    intervals = {"A": [], "B": []}
    for _, row in df.iterrows():
        letter = tone_letter(row[identity_col])
        if letter not in intervals:
            continue

        onset = to_float(row[onset_col])
        if onset is None:
            continue

        offset = to_float(row[offset_col]) if offset_col is not None else None
        if offset is None and duration_col is not None:
            duration = to_float(row[duration_col])
            if duration is not None:
                offset = onset + duration
        if offset is None:
            continue

        intervals[letter].append((onset, offset))

    all_values = [v for pairs in intervals.values() for pair in pairs for v in pair]
    if all_values and max(all_values) > EPOCH_THRESHOLD:
        reference = start_ts if start_ts is not None else min(all_values)
        intervals = {
            letter: [(on - reference, off - reference) for on, off in pairs]
            for letter, pairs in intervals.items()
        }

    return intervals


def format_time(seconds):
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    return f"{minutes:02d}:{secs:06.3f}"


def annotate_video(video_path, intervals, progress_callback=None):
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

    dot_radius = max(8, height // 40)
    center = (width - dot_radius * 3, dot_radius * 3)
    progress_step = max(1, total_frames // 200) if total_frames else 30

    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        t = frame_idx / fps

        for letter in ("A", "B"):
            if any(onset <= t <= offset for onset, offset in intervals.get(letter, [])):
                cv2.circle(frame, center, dot_radius, DOT_COLOR_BGR[letter], -1)
                break

        cv2.putText(
            frame,
            format_time(t),
            (10, height - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

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
        self.video_path = tk.StringVar()
        self.csv_path = tk.StringVar(value="No CSV selected")
        self.video_path.set("No video selected")
        self.status = tk.StringVar(value="Select a video and a CSV file to begin.")
        self._build()

    def _build(self):
        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        tk.Button(frame, text="Select Video (.mp4)", command=self.select_video).grid(
            row=0, column=0, sticky="w", pady=4
        )
        tk.Label(frame, textvariable=self.video_path, anchor="w", width=50).grid(
            row=0, column=1, sticky="w"
        )

        tk.Button(frame, text="Select CSV", command=self.select_csv).grid(
            row=1, column=0, sticky="w", pady=4
        )
        tk.Label(frame, textvariable=self.csv_path, anchor="w", width=50).grid(
            row=1, column=1, sticky="w"
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
            intervals = extract_tone_intervals(csv_file)
            self._set_status(
                f"Found {len(intervals['A'])} tone A and {len(intervals['B'])} tone B event(s). "
                "Processing video..."
            )

            def on_progress(frame_idx, total_frames):
                pct = (frame_idx / total_frames) * 100 if total_frames else 0
                self.root.after(0, self._update_progress, pct, frame_idx, total_frames)

            out_path = annotate_video(video, intervals, progress_callback=on_progress)
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
