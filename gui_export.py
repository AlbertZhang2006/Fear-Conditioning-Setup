import csv
import os
import queue
import random
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk


def timestamp_strings(ts=None):
    ts = time.time() if ts is None else ts
    return ts, datetime.fromtimestamp(ts).isoformat(timespec="milliseconds")


def format_timestamp(ts):
    if isinstance(ts, str):
        return ts
    return "" if ts in ("", None) else f"{ts:.6f}"


def tone_id(tone):
    return {"A": 0, "B": 1, "C": 2}.get(tone, "")


def export_file_names(base_file):
    folder = os.path.dirname(base_file)
    base = os.path.splitext(os.path.basename(base_file))[0]
    if base.startswith("experiment_"):
        base = base[len("experiment_"):]
    return (
        os.path.join(folder, f"{base}_Experiment Summary.csv"),
        os.path.join(folder, f"{base}_Trial Data Table.csv"),
    )


class ExportManager:
    def __init__(self, status_var, is_running):
        self.status_var = status_var
        self.is_running = is_running
        self.auto_export_folder = None
        self.auto_experiment_summary_file = None
        self.auto_trial_summary_file = None
        self.auto_export_active = False

    def choose_auto_export_folder(self):
        if self.is_running():
            messagebox.showwarning(
                "Auto Export Folder",
                "Stop the experiment before changing the auto export folder.",
            )
            return

        messagebox.showinfo(
            "Auto Export Folder",
            "Choose a folder where the trials will auto export the data to.",
        )

        folder = filedialog.askdirectory(title="Choose Auto Export Folder")
        if not folder:
            self.auto_export_folder = None
            self.status_var.set("Auto export disabled")
            return

        self.auto_export_folder = folder
        self.status_var.set(f"Auto export folder: {os.path.basename(folder)}")

    def start_auto_export_file(
        self,
        protocol_rows,
        events,
        summaries,
        iti_min_value,
        iti_max_value,
        start_delay_value,
        notes="",
        observer="",
        demonstrator="",
    ):
        if not self.auto_export_folder:
            self.auto_experiment_summary_file = None
            self.auto_trial_summary_file = None
            self.auto_export_active = False
            return

        base_file = os.path.join(
            self.auto_export_folder,
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        self.auto_experiment_summary_file, self.auto_trial_summary_file = export_file_names(
            base_file
        )
        self.auto_export_active = True
        self.write_export_files(
            self.auto_experiment_summary_file,
            self.auto_trial_summary_file,
            protocol_rows,
            events,
            summaries,
            iti_min_value,
            iti_max_value,
            start_delay_value,
            notes,
            observer,
            demonstrator,
        )

    def stop_auto_export_file(
        self,
        protocol_rows,
        events,
        summaries,
        iti_min_value,
        iti_max_value,
        start_delay_value,
        notes="",
        observer="",
        demonstrator="",
    ):
        if (
            self.auto_export_active
            and self.auto_experiment_summary_file
            and self.auto_trial_summary_file
        ):
            self.write_export_files(
                self.auto_experiment_summary_file,
                self.auto_trial_summary_file,
                protocol_rows,
                events,
                summaries,
                iti_min_value,
                iti_max_value,
                start_delay_value,
                notes,
                observer,
                demonstrator,
            )
        self.auto_export_active = False

    def write_auto_export_files(
        self,
        protocol_rows,
        events,
        summaries,
        iti_min_value,
        iti_max_value,
        start_delay_value,
        notes="",
        observer="",
        demonstrator="",
    ):
        if self.auto_export_active and self.auto_experiment_summary_file and self.auto_trial_summary_file:
            self.write_export_files(
                self.auto_experiment_summary_file,
                self.auto_trial_summary_file,
                protocol_rows,
                events,
                summaries,
                iti_min_value,
                iti_max_value,
                start_delay_value,
                notes,
                observer,
                demonstrator,
            )

    def export_data_manually(
        self,
        protocol_rows,
        events,
        summaries,
        iti_min_value,
        iti_max_value,
        start_delay_value,
        last_protocol_rows,
        last_events,
        last_summaries,
        last_iti_min_value,
        last_iti_max_value,
        last_start_delay_value,
        notes="",
        last_notes="",
        observer="",
        demonstrator="",
        last_observer="",
        last_demonstrator="",
    ):
        file = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            title="Choose Export Base Name",
        )
        if not file:
            return

        experiment_summary_file, trial_summary_file = export_file_names(file)

        if events:
            self.write_export_files(
                experiment_summary_file,
                trial_summary_file,
                protocol_rows,
                events,
                summaries,
                iti_min_value,
                iti_max_value,
                start_delay_value,
                notes,
                observer,
                demonstrator,
            )
            self.status_var.set("Exported experiment summary and trial data table")
        elif last_events:
            self.write_export_files(
                experiment_summary_file,
                trial_summary_file,
                last_protocol_rows,
                last_events,
                last_summaries,
                last_iti_min_value,
                last_iti_max_value,
                last_start_delay_value,
                last_notes,
                last_observer,
                last_demonstrator,
            )
            self.status_var.set("Exported experiment summary and trial data table")
        else:
            messagebox.showinfo("Export Data", "No experiment data has been recorded yet.")

    def write_export_files(
        self,
        experiment_summary_file,
        trial_summary_file,
        protocol_rows,
        events,
        summaries,
        iti_min_value,
        iti_max_value,
        start_delay_value,
        notes="",
        observer="",
        demonstrator="",
    ):
        self.write_experiment_summary_file(
            experiment_summary_file,
            protocol_rows,
            events,
            iti_min_value,
            iti_max_value,
            start_delay_value,
            notes,
            observer,
            demonstrator,
        )
        self.write_trial_summary_file(trial_summary_file, events, summaries)

    def write_experiment_summary_file(
        self, file, protocol_rows, events, iti_min_value, iti_max_value, start_delay_value,
        notes="", observer="", demonstrator=""
    ):
        with open(file, "w", newline="") as f:
            w = csv.writer(f)

            left_section = [
                ["ExportCreated", datetime.now().isoformat(timespec="milliseconds")],
                ["Observer", observer],
                ["Demonstrator", demonstrator],
                ["ITI_MIN", iti_min_value],
                ["ITI_MAX", iti_max_value],
                ["START_DELAY_SECONDS", start_delay_value],
                [],
                ["ExperimentNotes"],
                [notes],
            ]

            proto_section = [
                ["ProtocolTable"],
                ["Trial", "Tone", "ToneDuration", "ShockStart", "ShockDuration"],
            ]
            for i, row in enumerate(protocol_rows, start=1):
                proto_section.append([i] + list(row))

            # EventLog starts 3 rows below the ExperimentNotes label (index 7 + 3 = 10)
            PROTO_COL = 7   # column H (0-indexed)
            EVENT_LOG_ROW = 10  # row index where EventLog label appears
            EVENT_LOG_COLS = ["DateTime", "Timestamp", "Event", "Trial", "Tone", "Trial Note", "Detail"]
            event_data_start = EVENT_LOG_ROW + 2  # label row + header row

            total_rows = max(
                len(proto_section),
                event_data_start + len(events),
            )
            NUM_COLS = PROTO_COL + 6  # enough for both sides
            grid = [[""] * NUM_COLS for _ in range(total_rows)]

            for r, row_data in enumerate(left_section):
                for c, val in enumerate(row_data):
                    grid[r][c] = val

            for r, row_data in enumerate(proto_section):
                for c, val in enumerate(row_data):
                    grid[r][PROTO_COL + c] = val

            grid[EVENT_LOG_ROW][0] = "EventLog"
            for c, h in enumerate(EVENT_LOG_COLS):
                grid[EVENT_LOG_ROW + 1][c] = h
            for r, event in enumerate(events, start=event_data_start):
                grid[r][0] = event["datetime"]
                grid[r][1] = f"{event['timestamp']:.6f}"
                grid[r][2] = event["event"]
                grid[r][3] = event["trial"]
                grid[r][4] = event["tone"]
                if event["event"] == "TRIAL_NOTE":
                    grid[r][5] = event["detail"]
                else:
                    grid[r][6] = event["detail"]

            for row in grid:
                last = max((i for i, v in enumerate(row) if v != ""), default=-1)
                w.writerow(row[:last + 1] if last >= 0 else [])

    def write_trial_summary_file(self, file, events, summaries):
        start_event = next((event for event in events if event["event"] == "START"), None)
        with open(file, "w", newline="") as f:
            w = csv.writer(f)

            if start_event:
                w.writerow(["StartTimestamp", format_timestamp(start_event["timestamp"])])
                w.writerow(["StartDateTime", start_event["datetime"]])
            else:
                w.writerow(["StartTimestamp", ""])
                w.writerow(["StartDateTime", ""])
            w.writerow([])

            w.writerow(
                [
                    "Trial",
                    "Tone ID",
                    "Tone On TS",
                    "Tone Off TS",
                    "Shock",
                    "Shock On TS",
                    "Shock Off TS",
                    "ITI Start",
                    "ITI Stop",
                ]
            )
            for summary in summaries:
                w.writerow(
                    [
                        summary["trial"],
                        summary["tone_id"],
                        format_timestamp(summary["tone_on_timestamp"]),
                        format_timestamp(summary["tone_off_timestamp"]),
                        summary["shock"],
                        format_timestamp(summary["shock_on_timestamp"]),
                        format_timestamp(summary["shock_off_timestamp"]),
                        format_timestamp(summary["iti_start_timestamp"]),
                        format_timestamp(summary["iti_stop_timestamp"]),
                    ]
                )


class FearConditioningGUI:
    def __init__(self, controller):
        self.controller = controller
        self.root = tk.Tk()
        self.root.title("Fear Conditioning Controller")
        self._ui_thread_id = threading.get_ident()
        self._ui_queue = queue.Queue()

        self.status = tk.StringVar(value="Idle")
        self.export_manager = ExportManager(self.status, self.controller.is_running)
        self.iti_min_var = tk.StringVar(value="2")
        self.iti_max_var = tk.StringVar(value="3")
        self.start_delay_var = tk.StringVar(value="0")
        self.sequence_randomize_var = tk.BooleanVar(value=False)
        self.observer_var = tk.StringVar()
        self.demonstrator_var = tk.StringVar()
        self.watch_trial_var = tk.StringVar(value="Trial -- / --")
        self.watch_time_var = tk.StringVar(value="00:00.0")
        self.watch_phase_var = tk.StringVar(value="Idle")
        self.watch_tone_var = tk.StringVar(value="Tone: --")
        self.watch_shock_var = tk.StringVar(value="Shock: --")
        self._trial_watch_pending = False
        self._trial_watch_latest = None
        self._running_trial_number = None

        self._build()
        self.root.after(50, self._drain_ui_queue)

    def run(self):
        self.root.after(2000, self.export_manager.choose_auto_export_folder)
        self.root.mainloop()

    def set_run_controls(self, experiment_running):
        self.run_on_ui_thread(
            lambda: (
                self.start_btn.config(state="disabled" if experiment_running else "normal"),
                self.stop_btn.config(state="normal" if experiment_running else "disabled"),
                self.skip_btn.config(state="normal" if experiment_running else "disabled"),
                self.pause_btn.config(state="normal" if experiment_running else "disabled"),
                self.continue_btn.config(state="disabled"),
            )
        )

    def set_status(self, text):
        self.run_on_ui_thread(lambda: self.status.set(text))

    def run_on_ui_thread(self, callback):
        if threading.get_ident() == self._ui_thread_id:
            try:
                callback()
            except tk.TclError:
                return
        else:
            self._ui_queue.put(callback)

    def _drain_ui_queue(self):
        try:
            while True:
                callback = self._ui_queue.get_nowait()
                try:
                    callback()
                except tk.TclError:
                    return
        except queue.Empty:
            pass

        try:
            self.root.after(50, self._drain_ui_queue)
        except tk.TclError:
            return

    def set_paused(self, paused):
        self.run_on_ui_thread(
            lambda: (
                self.skip_btn.config(state="disabled" if paused else "normal"),
                self.pause_btn.config(state="disabled" if paused else "normal"),
                self.continue_btn.config(state="normal" if paused else "disabled"),
            )
        )

    def get_trials(self):
        trials = []
        for row in self.table.get_children():
            values = self.table.item(row)["values"]
            shock_start = values[2]
            trials.append(
                {
                    "tone": values[0],
                    "tone_duration": float(values[1]),
                    "shock_start": None if shock_start == "" else float(shock_start),
                    "shock_duration": float(values[3]),
                }
            )
        return trials

    def get_protocol_rows(self):
        return [self.table.item(row)["values"] for row in self.table.get_children()]

    def get_start_delay_seconds(self):
        value = self.start_delay_var.get().strip()
        return 0.0 if value == "" else float(value)

    def _build(self):
        self.root.minsize(1100, 460)

        top = tk.Frame(self.root)
        top.pack(fill="x", padx=8, pady=(8, 4))

        tk.Label(top, text="ITI Min").grid(row=0, column=0)
        tk.Entry(top, textvariable=self.iti_min_var, width=6).grid(row=0, column=1)

        tk.Label(top, text="ITI Max").grid(row=0, column=2)
        tk.Entry(top, textvariable=self.iti_max_var, width=6).grid(row=0, column=3)

        tk.Label(top, text="Time delay before experiment begins (sec)").grid(
            row=1, column=0, columnspan=3, sticky="e"
        )
        tk.Entry(top, textvariable=self.start_delay_var, width=6).grid(row=1, column=3)

        content = tk.Frame(self.root)
        content.pack(fill="both", expand=True, padx=8, pady=4)

        left_panel = tk.Frame(content)
        left_panel.pack(side="left", fill="y", padx=(0, 8))

        sequence_box = ttk.LabelFrame(left_panel, text="Sequence Builder")
        sequence_box.pack(fill="x")
        self._build_sequence_builder(sequence_box)

        watch_box = ttk.LabelFrame(left_panel, text="Live Monitor")
        watch_box.pack(fill="x", pady=(8, 0))
        self._build_trial_watch(watch_box)

        exp_notes_box = ttk.LabelFrame(left_panel, text="Experiment Notes")
        exp_notes_box.pack(fill="both", expand=True, pady=(8, 0))
        self._build_experiment_notes(exp_notes_box)

        trial_box = tk.Frame(content)
        trial_box.pack(side="left", fill="both", expand=True)

        trial_header = tk.Frame(trial_box)
        trial_header.pack(fill="x")
        tk.Label(trial_header, text="Trial Sequence").pack(side="left")
        tk.Button(
            trial_header,
            text="Reset",
            command=self.reset_trial_sequence,
        ).pack(side="left", padx=(8, 0))
        tk.Label(trial_header, text="Observer ID:").pack(side="left", padx=(16, 2))
        tk.Entry(trial_header, textvariable=self.observer_var, width=14).pack(side="left")
        tk.Label(trial_header, text="Demonstrator ID:").pack(side="left", padx=(10, 2))
        tk.Entry(trial_header, textvariable=self.demonstrator_var, width=14).pack(side="left")

        cols = ["Tone", "ToneDuration", "ShockStart", "ShockDuration"]
        table_frame = tk.Frame(trial_box)
        table_frame.pack(fill="both", expand=True)

        self.table = ttk.Treeview(
            table_frame,
            columns=cols,
            show="tree headings",
            selectmode="extended",
        )
        self.table.heading("#0", text="Trial")
        self.table.column("#0", width=64, minwidth=54, anchor="center", stretch=False)
        for c in cols:
            self.table.heading(c, text=c)
            self.table.column(c, width=max(120, len(c) * 10), minwidth=len(c) * 10)

        trial_scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview
        )
        self.table.configure(yscrollcommand=trial_scrollbar.set)
        self.table.tag_configure("running", background="#fff2b8")
        self.table.pack(side="left", fill="both", expand=True)
        trial_scrollbar.pack(side="right", fill="y")
        self.table.bind("<Double-1>", self.edit_cell)
        self.reset_trial_sequence(update_status=False)

        run_btns = tk.Frame(self.root)
        run_btns.pack(pady=(6, 2))

        tk.Button(run_btns, text="Add Trial", command=self.add_trial).pack(side="left", padx=2)
        tk.Button(run_btns, text="Delete Trial", command=self.delete_trial).pack(side="left", padx=2)

        self.start_btn = tk.Button(
            run_btns,
            text="Start Experiment",
            command=self.controller.start,
            font=("TkDefaultFont", 9, "bold"),
        )
        self.start_btn.pack(side="left", padx=2)

        self.stop_btn = tk.Button(
            run_btns, text="Stop Experiment", command=self.controller.stop, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=2)

        file_btns = tk.Frame(self.root)
        file_btns.pack(pady=2)

        tk.Button(file_btns, text="Save Experiment", command=self.save_protocol).pack(
            side="left", padx=2
        )
        tk.Button(file_btns, text="Load Previous Experiment", command=self.load_protocol).pack(
            side="left", padx=2
        )

        export_btns = tk.Frame(self.root)
        export_btns.pack(pady=(2, 6))

        tk.Button(
            export_btns,
            text="Set Auto Export Folder",
            command=self.export_manager.choose_auto_export_folder,
        ).pack(side="left", padx=2)
        tk.Button(
            export_btns,
            text="Export Data for Trial Held",
            command=self.controller.export_data_manually,
        ).pack(side="left", padx=2)

        tk.Label(self.root, textvariable=self.status).pack()

    def _build_sequence_builder(self, parent):
        cols = ["Tone", "Trials", "ToneDuration", "ShockStart", "ShockDuration"]
        headings = {
            "Tone": "Tone",
            "Trials": "Trials",
            "ToneDuration": "Tone Dur.",
            "ShockStart": "Shock Delay",
            "ShockDuration": "Shock Dur.",
        }
        widths = {
            "Tone": 42,
            "Trials": 46,
            "ToneDuration": 70,
            "ShockStart": 74,
            "ShockDuration": 70,
        }

        self.sequence_table = ttk.Treeview(
            parent, columns=cols, show="headings", height=3, selectmode="browse"
        )
        for col in cols:
            self.sequence_table.heading(col, text=headings[col])
            self.sequence_table.column(col, width=widths[col], minwidth=widths[col])

        self.sequence_table.pack(fill="x", padx=6, pady=(6, 4))
        self.sequence_table.bind("<Double-1>", self.edit_sequence_cell)
        self.sequence_table.insert("", "end", values=("A", 1, 10, 8, 2))
        self.sequence_table.insert("", "end", values=("B", 0, 10, "NA", "NA"))
        self.sequence_table.insert("", "end", values=("C", 0, 10, "NA", "NA"))

        tk.Checkbutton(
            parent,
            text="Randomize order when building",
            variable=self.sequence_randomize_var,
        ).pack(anchor="w", padx=6, pady=(2, 4))

        btns = tk.Frame(parent)
        btns.pack(fill="x", padx=6, pady=(0, 6))

        tk.Button(
            btns,
            text="Build Sequence",
            command=self.build_sequence_from_settings,
        ).pack(fill="x", pady=(0, 3))
        tk.Button(
            btns,
            text="Randomize Current Sequence",
            command=self.randomize_current_sequence,
        ).pack(fill="x")

    def _build_trial_watch(self, parent):
        parent.columnconfigure(0, weight=0)
        parent.columnconfigure(1, weight=1)

        watch_details = tk.Frame(parent)
        watch_details.grid(row=0, column=0, sticky="nw", padx=(8, 12), pady=8)

        tk.Label(
            watch_details,
            textvariable=self.watch_trial_var,
            font=("TkDefaultFont", 10, "bold"),
        ).pack(anchor="w")
        tk.Label(
            watch_details,
            textvariable=self.watch_time_var,
            font=("TkDefaultFont", 18, "bold"),
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(watch_details, textvariable=self.watch_phase_var).pack(anchor="w")
        tk.Label(watch_details, textvariable=self.watch_tone_var).pack(anchor="w")
        tk.Label(watch_details, textvariable=self.watch_shock_var).pack(anchor="w")
        btn_row = tk.Frame(watch_details)
        btn_row.pack(anchor="w", pady=(6, 0))
        self.skip_btn = tk.Button(
            btn_row,
            text="Skip Current Event",
            command=self.controller.skip_phase,
            state="disabled",
        )
        self.skip_btn.pack(side="left", padx=(0, 4))
        self.pause_btn = tk.Button(
            btn_row,
            text="Pause",
            command=self.controller.pause,
            state="disabled",
        )
        self.pause_btn.pack(side="left", padx=(0, 4))
        self.continue_btn = tk.Button(
            btn_row,
            text="Continue",
            command=self.controller.resume,
            state="disabled",
        )
        self.continue_btn.pack(side="left")

        notes_area = tk.Frame(parent)
        notes_area.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)
        tk.Label(notes_area, text="Notes on this trial").pack(anchor="w")
        self.trial_note_text = tk.Text(notes_area, height=4, width=34, wrap="word")
        self.trial_note_text.pack(fill="both", expand=True)

    def _build_experiment_notes(self, parent):
        self.experiment_note_text = tk.Text(parent, height=5, wrap="word")
        self.experiment_note_text.pack(fill="both", expand=True, padx=6, pady=(6, 2))
        tk.Button(
            parent,
            text="Save & Reset Experiment Notes",
            command=self._on_save_reset_experiment_notes,
        ).pack(fill="x", padx=6, pady=(0, 6))

    def _on_save_reset_experiment_notes(self):
        note = self.experiment_note_text.get("1.0", "end").strip()
        self.experiment_note_text.delete("1.0", "end")
        self.controller.save_and_reset_experiment_notes(note)

    def build_sequence_from_settings(self):
        if self.controller.is_running():
            messagebox.showwarning(
                "Sequence Builder", "Stop the experiment before building a sequence."
            )
            return

        try:
            rows = self.sequence_builder_trial_rows()
        except ValueError as exc:
            messagebox.showerror("Sequence Builder", str(exc))
            return

        if not rows:
            messagebox.showinfo(
                "Sequence Builder", "Enter at least one trial in the sequence builder."
            )
            return

        if self.sequence_randomize_var.get():
            random.shuffle(rows)

        self.replace_trial_rows(rows)
        self.status.set(f"Built {len(rows)} trials")

    def sequence_builder_trial_rows(self):
        rows = []
        for item in self.sequence_table.get_children():
            tone, trials, tone_duration, shock_start, shock_duration = [
                str(value).strip() for value in self.sequence_table.item(item)["values"]
            ]
            if shock_start.upper() == "NA":
                shock_start = ""
            if shock_duration.upper() == "NA":
                shock_duration = ""

            try:
                trial_count = int(trials)
            except ValueError as exc:
                raise ValueError(f"Trials for tone {tone} must be a whole number.") from exc

            if trial_count < 0:
                raise ValueError(f"Trials for tone {tone} cannot be negative.")

            try:
                tone_duration_value = float(tone_duration)
            except ValueError as exc:
                raise ValueError(f"Tone duration for tone {tone} must be a number.") from exc

            if tone_duration_value < 0:
                raise ValueError(f"Tone duration for tone {tone} cannot be negative.")

            if shock_start:
                try:
                    shock_start_value = float(shock_start)
                except ValueError as exc:
                    raise ValueError(f"Shock delay for tone {tone} must be a number.") from exc

                if shock_start_value < 0:
                    raise ValueError(f"Shock delay for tone {tone} cannot be negative.")

                try:
                    shock_duration_value = float(shock_duration)
                except ValueError as exc:
                    raise ValueError(
                        f"Shock duration for tone {tone} must be a number."
                    ) from exc

                if shock_duration_value < 0:
                    raise ValueError(
                        f"Shock duration for tone {tone} cannot be negative."
                    )
            else:
                shock_duration = shock_duration or "0"

            for _ in range(trial_count):
                rows.append((tone, tone_duration, shock_start, shock_duration))

        return rows

    def randomize_current_sequence(self):
        if self.controller.is_running():
            messagebox.showwarning(
                "Sequence Builder", "Stop the experiment before randomizing the sequence."
            )
            return

        rows = [self.table.item(item)["values"] for item in self.table.get_children()]
        if len(rows) < 2:
            self.status.set("Need at least two trials to randomize")
            return

        random.shuffle(rows)
        self.replace_trial_rows(rows)
        self.status.set(f"Randomized {len(rows)} trials")

    def reset_trial_sequence(self, update_status=True):
        if self.controller.is_running():
            messagebox.showwarning(
                "Reset Trial Sequence", "Stop the experiment before resetting the table."
            )
            return

        self.replace_trial_rows([("A", 10, 8, 2)])
        self.set_running_trial_row(None)
        if update_status:
            self.status.set("Reset trial sequence")

    def insert_trial_row(self, values):
        self.table.insert("", "end", values=values)
        self.renumber_trial_rows()

    def replace_trial_rows(self, rows):
        for row in self.table.get_children():
            self.table.delete(row)

        for values in rows:
            self.table.insert("", "end", values=values)
        self.renumber_trial_rows()

    def renumber_trial_rows(self):
        for index, row in enumerate(self.table.get_children(), start=1):
            self.table.item(row, text=str(index))

    def set_running_trial_row(self, trial_number):
        if trial_number in ("", None):
            if self._running_trial_number is None:
                return
            for row in self.table.get_children():
                self.table.item(row, tags=())
            self._running_trial_number = None
            return

        try:
            trial_index = int(trial_number) - 1
        except (TypeError, ValueError):
            return

        if self._running_trial_number == trial_index + 1:
            return

        rows = self.table.get_children()
        if self._running_trial_number is not None:
            previous_index = self._running_trial_number - 1
            if 0 <= previous_index < len(rows):
                self.table.item(rows[previous_index], tags=())

        if 0 <= trial_index < len(rows):
            current_row = rows[trial_index]
            self.table.item(current_row, tags=("running",))
            self.table.see(current_row)
            self._running_trial_number = trial_index + 1

    def set_trial_watch(
        self,
        trial_number=None,
        total_trials=None,
        tone="",
        phase="Idle",
        elapsed=0,
        total_seconds=None,
        shock_start=None,
        shock_duration=None,
        mark_trial=True,
    ):
        self._trial_watch_latest = {
            "trial_number": trial_number,
            "total_trials": total_trials,
            "tone": tone,
            "phase": phase,
            "elapsed": elapsed,
            "total_seconds": total_seconds,
            "shock_start": shock_start,
            "shock_duration": shock_duration,
            "mark_trial": mark_trial,
        }
        if self._trial_watch_pending:
            return

        self._trial_watch_pending = True

        def update():
            self._trial_watch_pending = False
            state = self._trial_watch_latest or {}
            trial_number = state.get("trial_number")
            total_trials = state.get("total_trials")
            tone = state.get("tone", "")
            phase = state.get("phase", "Idle")
            elapsed = state.get("elapsed", 0)
            total_seconds = state.get("total_seconds")
            shock_start = state.get("shock_start")
            shock_duration = state.get("shock_duration")
            mark_trial = state.get("mark_trial", True)

            if trial_number is None or total_trials is None:
                self.watch_trial_var.set("Trial -- / --")
            else:
                self.watch_trial_var.set(f"Trial {trial_number} / {total_trials}")

            elapsed_text = self.format_watch_time(elapsed)
            if total_seconds is None:
                self.watch_time_var.set(elapsed_text)
            else:
                self.watch_time_var.set(
                    f"{elapsed_text} / {self.format_watch_time(total_seconds)}"
                )

            self.watch_phase_var.set(f"Phase: {phase}")
            self.watch_tone_var.set(f"Tone: {tone or '--'}")

            if shock_start in ("", None):
                self.watch_shock_var.set("Shock: none")
            else:
                self.watch_shock_var.set(
                    f"Shock: delay {float(shock_start):g}s, duration {float(shock_duration):g}s"
                )

            if mark_trial:
                self.set_running_trial_row(trial_number)

        try:
            self.run_on_ui_thread(update)
        except tk.TclError:
            self._trial_watch_pending = False
            return

    def pop_trial_note(self):
        result = {"note": ""}
        done = threading.Event()

        def read_and_clear():
            try:
                result["note"] = self.trial_note_text.get("1.0", "end").strip()
                self.trial_note_text.delete("1.0", "end")
            finally:
                done.set()

        try:
            self.run_on_ui_thread(read_and_clear)
        except tk.TclError:
            return ""

        done.wait(1)
        return result["note"]

    def pop_experiment_note(self):
        result = {"note": ""}
        done = threading.Event()

        def read_and_clear():
            try:
                result["note"] = self.experiment_note_text.get("1.0", "end").strip()
                self.experiment_note_text.delete("1.0", "end")
            finally:
                done.set()

        try:
            self.root.after(0, read_and_clear)
        except tk.TclError:
            return ""

        done.wait(1)
        return result["note"]

    def format_watch_time(self, seconds):
        seconds = max(0, float(seconds or 0))
        minutes = int(seconds // 60)
        remaining = seconds - minutes * 60
        return f"{minutes:02d}:{remaining:04.1f}"

    def place_cell_editor(self, table, row, col, editor):
        table.update_idletasks()
        bbox = table.bbox(row, col)
        if not bbox:
            editor.destroy()
            return False

        x, y, w, h = bbox
        editor.place(
            x=table.winfo_rootx() - self.root.winfo_rootx() + x,
            y=table.winfo_rooty() - self.root.winfo_rooty() + y,
            width=w,
            height=h,
        )
        editor.lift()
        return True

    def add_trial(self):
        self.insert_trial_row(("A", 5, "", 0))

    def delete_trial(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo("Delete Trial", "Select one or more trials to delete.")
            return

        if self.controller.is_running():
            messagebox.showwarning(
                "Delete Trial", "Stop the experiment before deleting trials."
            )
            return

        for row in selected:
            self.table.delete(row)
        self.renumber_trial_rows()

    def edit_cell(self, event):
        row = self.table.identify_row(event.y)
        col = self.table.identify_column(event.x)
        if not row or col == "#0":
            return

        idx = int(col[1:]) - 1
        values = list(self.table.item(row)["values"])

        if idx == 0:
            cb = ttk.Combobox(self.root, values=["A", "B", "C"], state="readonly")
            if not self.place_cell_editor(self.table, row, col, cb):
                return
            cb.set(values[idx])

            def save(e=None):
                values[idx] = cb.get()
                self.table.item(row, values=values)
                cb.destroy()

            cb.bind("<<ComboboxSelected>>", save)
            cb.focus()
        else:
            entry = tk.Entry(self.root)
            if not self.place_cell_editor(self.table, row, col, entry):
                return
            entry.insert(0, values[idx])

            def save(e=None):
                values[idx] = entry.get()
                self.table.item(row, values=values)
                entry.destroy()

            entry.bind("<Return>", save)
            entry.bind("<FocusOut>", save)
            entry.focus()

    def edit_sequence_cell(self, event):
        row = self.sequence_table.identify_row(event.y)
        col = self.sequence_table.identify_column(event.x)
        if not row:
            return

        idx = int(col[1:]) - 1
        if idx == 0:
            return

        values = list(self.sequence_table.item(row)["values"])

        entry = tk.Entry(self.root)
        if not self.place_cell_editor(self.sequence_table, row, col, entry):
            return
        entry.insert(0, values[idx])

        def save(e=None):
            values[idx] = entry.get()
            self.sequence_table.item(row, values=values)
            entry.destroy()

        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", save)
        entry.focus()

    def save_protocol(self):
        file = filedialog.asksaveasfilename(defaultextension=".csv")
        if not file:
            return

        with open(file, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ITI_MIN", self.iti_min_var.get()])
            w.writerow(["ITI_MAX", self.iti_max_var.get()])
            w.writerow(["START_DELAY_SECONDS", self.start_delay_var.get().strip() or "0"])
            w.writerow(["SEQUENCE_RANDOMIZE", str(self.sequence_randomize_var.get())])
            w.writerow(["OBSERVER_ID", self.observer_var.get()])
            w.writerow(["DEMONSTRATOR_ID", self.demonstrator_var.get()])
            w.writerow([])

            w.writerow(["SequenceBuilder"])
            for item in self.sequence_table.get_children():
                w.writerow(self.sequence_table.item(item)["values"])
            w.writerow([])

            w.writerow(["TrialSequence"])
            for row in self.table.get_children():
                w.writerow(self.table.item(row)["values"])

    def load_protocol(self):
        file = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not file:
            return

        with open(file) as f:
            rows = list(csv.reader(f))

        metadata = {}
        seq_builder_rows = None
        trial_rows = []
        current_section = None

        for row in rows:
            if not any(cell.strip() for cell in row):
                current_section = None
                continue

            if len(row) == 1:
                marker = row[0].strip()
                if marker == "SequenceBuilder":
                    current_section = "seq"
                    seq_builder_rows = []
                    continue
                elif marker == "TrialSequence":
                    current_section = "trial"
                    continue

            if current_section == "seq":
                seq_builder_rows.append(row)
            elif current_section == "trial":
                trial_rows.append(row)
            else:
                if len(row) >= 2:
                    key, val = row[0].strip(), row[1].strip()
                    if key == "Tone" and val == "ToneDuration":
                        current_section = "trial"
                    else:
                        metadata[key] = val

        self.iti_min_var.set(metadata.get("ITI_MIN", "2"))
        self.iti_max_var.set(metadata.get("ITI_MAX", "3"))
        self.start_delay_var.set(metadata.get("START_DELAY_SECONDS", "0"))
        self.sequence_randomize_var.set(
            metadata.get("SEQUENCE_RANDOMIZE", "False").lower() == "true"
        )
        self.observer_var.set(metadata.get("OBSERVER_ID", ""))
        self.demonstrator_var.set(metadata.get("DEMONSTRATOR_ID", ""))

        if seq_builder_rows is not None:
            for item in self.sequence_table.get_children():
                self.sequence_table.delete(item)
            for row in seq_builder_rows:
                if len(row) >= 5:
                    self.sequence_table.insert("", "end", values=row[:5])

        self.replace_trial_rows(trial_rows)
