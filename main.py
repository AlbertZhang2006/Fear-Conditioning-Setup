import os
import random
import threading
import time

import serial
import winsound

from gui_export import FearConditioningGUI, timestamp_strings, tone_id


ARDUINO_PORT = "COM5"
BAUD = 115200
CAMERA_ON_COMMAND = b"CAMERA_ON\n"
CAMERA_OFF_COMMAND = b"CAMERA_OFF\n"
SHOCK_ON_COMMAND = b"SHOCK_ON\n"
SHOCK_OFF_COMMAND = b"SHOCK_OFF\n"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

TONE_FILES = {
    "A": os.path.join(SCRIPT_DIR, "WhiteNoise,SR=50k,F=4K-20K.wav"),
    "B": os.path.join(SCRIPT_DIR, "toneCloud1sMonoFS88200.wav"),
    "C": os.path.join(SCRIPT_DIR, "WhiteNoise,SR=50k,F=4K-20K.wav"),
}
LOOPING_TONES = set(TONE_FILES)


class HardwareController:
    def __init__(self, port=ARDUINO_PORT, baud=BAUD):
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            time.sleep(2)
        except Exception:
            self.ser = None
            print("Arduino not connected")

    def send(self, command):
        if self.ser:
            self.ser.write(command)
            self.ser.flush()

    def camera_on(self):
        self.send(CAMERA_ON_COMMAND)

    def camera_off(self):
        self.send(CAMERA_OFF_COMMAND)

    def shock_on(self):
        self.send(SHOCK_ON_COMMAND)

    def shock_off(self):
        self.send(SHOCK_OFF_COMMAND)


class AudioController:
    def __init__(self, tone_files):
        self.tone_files = tone_files

    def tone_on(self, stim):
        path = self.tone_files.get(stim)
        if path and os.path.exists(path):
            flags = winsound.SND_FILENAME | winsound.SND_ASYNC
            if stim in LOOPING_TONES:
                flags |= winsound.SND_LOOP
            winsound.PlaySound(path, flags)

    def tone_off(self):
        winsound.PlaySound(None, winsound.SND_PURGE)


class ExperimentController:
    def __init__(self):
        self.hardware = HardwareController()
        self.audio = AudioController(TONE_FILES)
        self.stop_event = threading.Event()
        self.running = False
        self.gui = None
        self.export_manager = None
        self.export_lock = threading.Lock()

        self.experiment_events = []
        self.trial_summaries = []
        self.protocol_snapshot = []
        self.protocol_iti_min = ""
        self.protocol_iti_max = ""
        self.protocol_start_delay = ""

        self.last_experiment_events = []
        self.last_trial_summaries = []
        self.last_protocol_snapshot = []
        self.last_protocol_iti_min = ""
        self.last_protocol_iti_max = ""
        self.last_protocol_start_delay = ""

    def attach_gui(self, gui):
        self.gui = gui
        self.export_manager = gui.export_manager

    def is_running(self):
        return self.running

    def start(self):
        if self.running:
            return
        self.gui.set_run_controls(True)
        threading.Thread(target=self.run_experiment, daemon=True).start()

    def stop(self):
        self.stop_event.set()

    def append_event(self, event, trial="", tone="", detail=""):
        ts, iso = timestamp_strings()
        row = {
            "timestamp": ts,
            "datetime": iso,
            "event": event,
            "trial": trial,
            "tone": tone,
            "detail": detail,
        }

        with self.export_lock:
            self.experiment_events.append(row)
            self.write_auto_export_files()

        return row

    def add_trial_summary(self, trial, tone, has_shock):
        with self.export_lock:
            self.trial_summaries.append(
                {
                    "trial": trial,
                    "tone": tone,
                    "tone_id": tone_id(tone),
                    "tone_on_timestamp": "",
                    "tone_off_timestamp": "",
                    "iti_start_timestamp": "",
                    "iti_stop_timestamp": "",
                    "shock": 1 if has_shock else 0,
                    "shock_on_timestamp": "" if has_shock else "NA",
                    "shock_off_timestamp": "" if has_shock else "NA",
                }
            )
            self.write_auto_export_files()

    def update_trial_summary(self, trial, **updates):
        with self.export_lock:
            for summary in self.trial_summaries:
                if summary["trial"] == trial:
                    summary.update(updates)
                    break
            self.write_auto_export_files()

    def write_auto_export_files(self):
        self.export_manager.write_auto_export_files(
            self.protocol_snapshot,
            self.experiment_events,
            self.trial_summaries,
            self.protocol_iti_min,
            self.protocol_iti_max,
            self.protocol_start_delay,
        )

    def export_data_manually(self):
        self.export_manager.export_data_manually(
            self.protocol_snapshot,
            self.experiment_events,
            self.trial_summaries,
            self.protocol_iti_min,
            self.protocol_iti_max,
            self.protocol_start_delay,
            self.last_protocol_snapshot,
            self.last_experiment_events,
            self.last_trial_summaries,
            self.last_protocol_iti_min,
            self.last_protocol_iti_max,
            self.last_protocol_start_delay,
        )

    def run_experiment(self):
        self.running = True
        self.stop_event.clear()
        self.experiment_events = []
        self.trial_summaries = []
        self.protocol_snapshot = self.gui.get_protocol_rows()
        self.protocol_iti_min = self.gui.iti_min_var.get()
        self.protocol_iti_max = self.gui.iti_max_var.get()
        self.protocol_start_delay = self.gui.start_delay_var.get().strip() or "0"

        try:
            trials = self.gui.get_trials()
            iti_min = float(self.protocol_iti_min)
            iti_max = float(self.protocol_iti_max)
            start_delay = self.gui.get_start_delay_seconds()

            self.export_manager.start_auto_export_file(
                self.protocol_snapshot,
                self.experiment_events,
                self.trial_summaries,
                self.protocol_iti_min,
                self.protocol_iti_max,
                self.protocol_start_delay,
            )

            self.hardware.camera_on()
            self.append_event("CAMERA_ON")

            if start_delay > 0:
                self.append_event("START_DELAY", detail=f"seconds={start_delay}")
                self.gui.status.set(f"Start delay {start_delay:.1f}s")
                self.stop_event.wait(start_delay)
                if self.stop_event.is_set():
                    self.append_event("STOPPED")
                    return

            self.append_event("START", detail=f"trials={len(trials)}")

            for i, trial in enumerate(trials):
                if self.stop_event.is_set():
                    break

                self.run_trial(i + 1, len(trials), trial)

            if self.stop_event.is_set():
                self.append_event("STOPPED")
            else:
                self.append_event("END")

        finally:
            self.audio.tone_off()
            self.hardware.shock_off()
            self.hardware.camera_off()
            self.append_event("CAMERA_OFF")
            with self.export_lock:
                self.last_experiment_events = list(self.experiment_events)
                self.last_trial_summaries = list(self.trial_summaries)
                self.last_protocol_snapshot = list(self.protocol_snapshot)
                self.last_protocol_iti_min = self.protocol_iti_min
                self.last_protocol_iti_max = self.protocol_iti_max
                self.last_protocol_start_delay = self.protocol_start_delay
                self.export_manager.stop_auto_export_file(
                    self.protocol_snapshot,
                    self.experiment_events,
                    self.trial_summaries,
                    self.protocol_iti_min,
                    self.protocol_iti_max,
                    self.protocol_start_delay,
                )
            self.running = False
            self.gui.status.set("Idle")
            self.gui.set_run_controls(False)

    def run_trial(self, trial_number, total_trials, trial):
        self.gui.status.set(f"Trial {trial_number}/{total_trials}")

        start = time.time()
        tone_stop_time = start + trial["tone_duration"]
        shock_start_time = (
            start + trial["shock_start"] if trial["shock_start"] is not None else None
        )
        shock_stop_time = (
            shock_start_time + trial["shock_duration"]
            if shock_start_time is not None
            else None
        )

        self.add_trial_summary(trial_number, trial["tone"], shock_start_time is not None)

        self.audio.tone_on(trial["tone"])
        tone_on_event = self.append_event("TONE_ON", trial_number, trial["tone"])
        self.update_trial_summary(
            trial_number, tone_on_timestamp=tone_on_event["timestamp"]
        )

        tone_stopped = False
        shock_started = False
        shock_stopped = shock_start_time is None

        while not self.stop_event.is_set() and not (tone_stopped and shock_stopped):
            now = time.time()

            if not tone_stopped and now >= tone_stop_time:
                self.audio.tone_off()
                tone_off_event = self.append_event("TONE_OFF", trial_number, trial["tone"])
                self.update_trial_summary(
                    trial_number, tone_off_timestamp=tone_off_event["timestamp"]
                )
                tone_stopped = True

            if shock_start_time is not None and not shock_started and now >= shock_start_time:
                self.hardware.shock_on()
                shock_on_event = self.append_event("SHOCK_ON", trial_number, trial["tone"])
                self.update_trial_summary(
                    trial_number, shock_on_timestamp=shock_on_event["timestamp"]
                )
                shock_started = True

            if shock_started and not shock_stopped and now >= shock_stop_time:
                self.hardware.shock_off()
                shock_off_event = self.append_event("SHOCK_OFF", trial_number, trial["tone"])
                self.update_trial_summary(
                    trial_number, shock_off_timestamp=shock_off_event["timestamp"]
                )
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

        self.finish_trial_outputs(
            trial_number,
            trial,
            tone_stopped,
            shock_started,
            shock_stopped,
            shock_start_time,
        )
        self.run_iti(trial_number, trial["tone"])

    def finish_trial_outputs(
        self,
        trial_number,
        trial,
        tone_stopped,
        shock_started,
        shock_stopped,
        shock_start_time,
    ):
        if not tone_stopped:
            self.audio.tone_off()
            tone_off_event = self.append_event(
                "TONE_OFF", trial_number, trial["tone"], "stopped early"
            )
            self.update_trial_summary(
                trial_number, tone_off_timestamp=tone_off_event["timestamp"]
            )

        if shock_started and not shock_stopped:
            self.hardware.shock_off()
            shock_off_event = self.append_event(
                "SHOCK_OFF", trial_number, trial["tone"], "stopped early"
            )
            self.update_trial_summary(
                trial_number, shock_off_timestamp=shock_off_event["timestamp"]
            )
        elif self.stop_event.is_set() and shock_start_time is not None and not shock_started:
            self.update_trial_summary(
                trial_number,
                shock=0,
                shock_on_timestamp="NA",
                shock_off_timestamp="NA",
            )

        self.append_event("TRIAL_END", trial_number, trial["tone"])

    def run_iti(self, trial_number, tone):
        iti = random.uniform(float(self.protocol_iti_min), float(self.protocol_iti_max))
        self.gui.status.set(f"ITI {iti:.1f}s")
        iti_start_event = self.append_event(
            "ITI_START", trial_number, tone, f"seconds={iti:.6f}"
        )
        self.update_trial_summary(
            trial_number, iti_start_timestamp=iti_start_event["timestamp"]
        )
        self.stop_event.wait(iti)
        iti_detail = "stopped early" if self.stop_event.is_set() else ""
        iti_stop_event = self.append_event("ITI_STOP", trial_number, tone, iti_detail)
        self.update_trial_summary(
            trial_number, iti_stop_timestamp=iti_stop_event["timestamp"]
        )


def main():
    controller = ExperimentController()
    gui = FearConditioningGUI(controller)
    controller.attach_gui(gui)
    gui.run()


if __name__ == "__main__":
    main()
