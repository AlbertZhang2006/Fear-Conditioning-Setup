import csv
import os
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
        )

    def stop_auto_export_file(
        self,
        protocol_rows,
        events,
        summaries,
        iti_min_value,
        iti_max_value,
        start_delay_value,
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
    ):
        self.write_experiment_summary_file(
            experiment_summary_file,
            protocol_rows,
            events,
            iti_min_value,
            iti_max_value,
            start_delay_value,
        )
        self.write_trial_summary_file(trial_summary_file, events, summaries)

    def write_experiment_summary_file(
        self, file, protocol_rows, events, iti_min_value, iti_max_value, start_delay_value
    ):
        with open(file, "w", newline="") as f:
            w = csv.writer(f)

            w.writerow(["ExportCreated", datetime.now().isoformat(timespec="milliseconds")])
            w.writerow(["ITI_MIN", iti_min_value])
            w.writerow(["ITI_MAX", iti_max_value])
            w.writerow(["START_DELAY_SECONDS", start_delay_value])
            w.writerow([])

            w.writerow(["ProtocolTable"])
            w.writerow(["Trial", "Tone", "ToneDuration", "ShockStart", "ShockDuration"])
            for i, row in enumerate(protocol_rows, start=1):
                w.writerow([i] + list(row))
            w.writerow([])

            w.writerow(["EventLog"])
            w.writerow(["DateTime", "Timestamp", "Event", "Trial", "Tone", "Detail"])
            for event in events:
                w.writerow(
                    [
                        event["datetime"],
                        f"{event['timestamp']:.6f}",
                        event["event"],
                        event["trial"],
                        event["tone"],
                        event["detail"],
                    ]
                )

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

        self.status = tk.StringVar(value="Idle")
        self.export_manager = ExportManager(self.status, self.controller.is_running)
        self.iti_min_var = tk.StringVar(value="2")
        self.iti_max_var = tk.StringVar(value="3")
        self.start_delay_var = tk.StringVar(value="0")

        self._build()

    def run(self):
        self.root.after(2000, self.export_manager.choose_auto_export_folder)
        self.root.mainloop()

    def set_run_controls(self, experiment_running):
        self.start_btn.config(state="disabled" if experiment_running else "normal")
        self.stop_btn.config(state="normal" if experiment_running else "disabled")

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
        top = tk.Frame(self.root)
        top.pack()

        tk.Label(top, text="ITI Min").grid(row=0, column=0)
        tk.Entry(top, textvariable=self.iti_min_var, width=6).grid(row=0, column=1)

        tk.Label(top, text="ITI Max").grid(row=0, column=2)
        tk.Entry(top, textvariable=self.iti_max_var, width=6).grid(row=0, column=3)

        tk.Label(top, text="Time delay before experiment begins (sec)").grid(
            row=1, column=0, columnspan=3, sticky="e"
        )
        tk.Entry(top, textvariable=self.start_delay_var, width=6).grid(row=1, column=3)

        cols = ["Tone", "ToneDuration", "ShockStart", "ShockDuration"]
        self.table = ttk.Treeview(self.root, columns=cols, show="headings")
        for c in cols:
            self.table.heading(c, text=c)
            self.table.column(c, width=max(120, len(c) * 10), minwidth=len(c) * 10)

        self.table.pack(fill="both", expand=True)
        self.table.bind("<Double-1>", self.edit_cell)
        self.table.insert("", "end", values=("A", 10, 8, 2))

        run_btns = tk.Frame(self.root)
        run_btns.pack(pady=(6, 2))

        tk.Button(run_btns, text="Add Trial", command=self.add_trial).pack(side="left", padx=2)
        tk.Button(run_btns, text="Delete Trial", command=self.delete_trial).pack(side="left", padx=2)

        self.start_btn = tk.Button(
            run_btns,
            text="Start",
            command=self.controller.start,
            font=("TkDefaultFont", 9, "bold"),
        )
        self.start_btn.pack(side="left", padx=2)

        self.stop_btn = tk.Button(
            run_btns, text="Stop", command=self.controller.stop, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=2)

        file_btns = tk.Frame(self.root)
        file_btns.pack(pady=2)

        tk.Button(file_btns, text="Save Trial", command=self.save_protocol).pack(
            side="left", padx=2
        )
        tk.Button(file_btns, text="Load Previous Trial", command=self.load_protocol).pack(
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

    def add_trial(self):
        self.table.insert("", "end", values=("A", 5, "", 0))

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

    def edit_cell(self, event):
        row = self.table.identify_row(event.y)
        col = self.table.identify_column(event.x)
        if not row:
            return

        x, y, w, h = self.table.bbox(row, col)
        idx = int(col[1:]) - 1
        values = list(self.table.item(row)["values"])

        if idx == 0:
            cb = ttk.Combobox(self.root, values=["A", "B", "C"], state="readonly")
            cb.place(x=x + self.table.winfo_x(), y=y + self.table.winfo_y(), width=w, height=h)
            cb.set(values[idx])

            def save(e=None):
                values[idx] = cb.get()
                self.table.item(row, values=values)
                cb.destroy()

            cb.bind("<<ComboboxSelected>>", save)
            cb.focus()
        else:
            entry = tk.Entry(self.root)
            entry.place(
                x=x + self.table.winfo_x(), y=y + self.table.winfo_y(), width=w, height=h
            )
            entry.insert(0, values[idx])

            def save(e=None):
                values[idx] = entry.get()
                self.table.item(row, values=values)
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
            w.writerow([])
            w.writerow(["Tone", "ToneDuration", "ShockStart", "ShockDuration"])

            for row in self.table.get_children():
                w.writerow(self.table.item(row)["values"])

    def load_protocol(self):
        file = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not file:
            return

        for row in self.table.get_children():
            self.table.delete(row)

        with open(file) as f:
            reader = csv.reader(f)
            rows = list(reader)

        metadata_end = rows.index([])
        metadata = {
            row[0]: row[1]
            for row in rows[:metadata_end]
            if len(row) >= 2
        }

        self.iti_min_var.set(metadata.get("ITI_MIN", "2"))
        self.iti_max_var.set(metadata.get("ITI_MAX", "3"))
        self.start_delay_var.set(metadata.get("START_DELAY_SECONDS", "0"))

        start_idx = metadata_end + 2
        for row in rows[start_idx:]:
            self.table.insert("", "end", values=row)
