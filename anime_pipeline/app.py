"""Local production console. Run with Python 3.12+ on Windows 11.

The GUI launches the same resumable CLI used for automated production; it does
not fabricate progress or claim a model backend is available when it is not.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import zipfile

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
EPISODE_NAME = "THE_MAGICAL_WORLD_EP01_720P.mp4"
MODES = {
    "Mode 2 — lightweight hybrid": "hybrid",
    "Mode 1 — local neural animation (not configured)": "local_neural",
    "Mode 3 — advanced video generation (not configured)": "advanced",
}
STYLES = {
    "Cinematic fantasy anime": "default",
    "Moonlit fantasy anime": "moonlit",
    "Warm dawn fantasy anime": "dawn",
}


def episode_video_path(output: Path = OUTPUT, delivery: Path = ROOT / "delivery") -> Path:
    """Prefer the render master; a source-package delivery copy is playable too."""
    master = output / EPISODE_NAME
    compressed = delivery / EPISODE_NAME
    if master.is_file():
        return master
    if compressed.is_file():
        return compressed
    # open_local supplies the normal not-generated message for an absent output.
    return master


def pipeline_command(action: str, shot: int | None = None) -> list[str]:
    allowed = {"prepare", "sample", "render", "audio", "export", "validate", "all", "pause", "resume"}
    if action not in allowed:
        raise ValueError(f"Unknown action: {action}")
    command = [sys.executable, "-u", str(ROOT / "pipeline.py"), action]
    if shot is not None:
        if action != "render" or not 0 <= shot <= 59:
            raise ValueError("A shot index must be between 0 and 59 and is valid only for render.")
        command += ["--shot", str(shot), "--force"]
    return command


def read_progress(path: Path = OUTPUT / "progress.json") -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def archive_audio(source: Path, destination: Path) -> int:
    """Archive actual generated audio only; an empty source is an error."""
    extensions = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}
    files = sorted(p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in extensions)
    if not files:
        raise FileNotFoundError(f"No generated audio files exist in {source} yet.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(source))
    return len(files)


def open_local(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"This output has not been generated yet: {path}")
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def main() -> None:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, scrolledtext, ttk
    except ImportError as exc:
        raise SystemExit("Tkinter is required for the GUI. Install Python with Tcl/Tk, or use pipeline.py from a terminal.") from exc

    class ProductionApp:
        def __init__(self, window: tk.Tk):
            self.window = window
            self.events: queue.Queue = queue.Queue()
            self.worker: threading.Thread | None = None
            self.process: subprocess.Popen | None = None
            self.preview_images: list = []
            self.asset_stamp = 0.0
            OUTPUT.mkdir(parents=True, exist_ok=True)
            window.title("THE MAGICAL WORLD · Episode 1 Production")
            window.geometry("1180x850")
            window.minsize(960, 720)
            window.protocol("WM_DELETE_WINDOW", self.close)
            style = ttk.Style(window)
            if "clam" in style.theme_names():
                style.theme_use("clam")
            style.configure("Title.TLabel", font=("Segoe UI", 19, "bold"))
            style.configure("Sub.TLabel", foreground="#44616a")
            self.duration = tk.StringVar(value="600")
            self.style = tk.StringVar(value=list(STYLES)[0])
            self.mode = tk.StringVar(value=list(MODES)[0])
            self.accent = tk.StringVar(value="Indian English (requested; backend validation required)")
            self.shot = tk.StringVar(value="0")
            self.status = tk.StringVar(value="Idle — no generation command has been started.")
            self.details = tk.StringVar(value="Progress will be read from output/progress.json.")
            self._build()
            self.load_settings()
            window.after(250, self.poll)

        def _build(self):
            outer = ttk.Frame(self.window, padding=16)
            outer.pack(fill="both", expand=True)
            ttk.Label(outer, text="THE MAGICAL WORLD", style="Title.TLabel").pack(anchor="w")
            ttk.Label(outer, text="S01E01 · The Boy Without a Magic Signature", style="Sub.TLabel").pack(anchor="w", pady=(0, 12))
            brief = ttk.LabelFrame(outer, text="Episode brief / direction notes", padding=10)
            brief.pack(fill="x")
            self.story = scrolledtext.ScrolledText(brief, height=4, wrap="word", font=("Segoe UI", 10))
            self.story.pack(fill="x")
            line = ttk.Frame(brief)
            line.pack(fill="x", pady=(6, 0))
            ttk.Button(line, text="Load notes…", command=self.load_notes).pack(side="left")
            ttk.Label(line, text=" Notes are saved with this fixed ten-section Episode 1 project.", style="Sub.TLabel").pack(side="left")
            settings = ttk.Frame(outer)
            settings.pack(fill="x", pady=10)
            for column in [1, 3]:
                settings.columnconfigure(column, weight=1)
            ttk.Label(settings, text="Duration").grid(row=0, column=0, sticky="w", padx=(0, 8))
            ttk.Entry(settings, textvariable=self.duration, width=8, state="readonly").grid(row=0, column=1, sticky="w")
            ttk.Label(settings, text="seconds · 1280×720 · 24 FPS").grid(row=0, column=2, sticky="w", padx=8)
            ttk.Combobox(settings, textvariable=self.style, values=list(STYLES), state="readonly", width=28).grid(row=0, column=3, sticky="ew")
            ttk.Label(settings, text="Production").grid(row=1, column=0, sticky="w", pady=(8, 0))
            ttk.Combobox(settings, textvariable=self.mode, values=list(MODES), state="readonly", width=47).grid(row=1, column=1, columnspan=2, sticky="ew", padx=(0, 10), pady=(8, 0))
            ttk.Combobox(settings, textvariable=self.accent, values=[self.accent.get()], state="readonly", width=49).grid(row=1, column=3, sticky="ew", pady=(8, 0))
            buttons = ttk.Frame(outer)
            buttons.pack(fill="x")
            primary = [
                ("Generate Character Assets", lambda: self.launch("prepare")),
                ("Generate Sample", lambda: self.launch("sample")),
                ("Generate Episode", lambda: self.launch("all")),
                ("Pause", self.pause), ("Resume", self.resume),
                ("Preview Timeline", self.show_timeline),
            ]
            for index, (label, callback) in enumerate(primary):
                ttk.Button(buttons, text=label, command=callback).grid(row=0, column=index, sticky="ew", padx=(0, 5), pady=3)
                buttons.columnconfigure(index, weight=1)
            regeneration = ttk.Frame(outer)
            regeneration.pack(fill="x", pady=(4, 0))
            ttk.Label(regeneration, text="Shot index (0–59)").pack(side="left")
            ttk.Spinbox(regeneration, from_=0, to=59, width=5, textvariable=self.shot).pack(side="left", padx=8)
            ttk.Button(regeneration, text="Regenerate Selected Shot", command=self.regenerate).pack(side="left", padx=(0, 6))
            ttk.Button(regeneration, text="Generate Dialogue / Music / SFX", command=lambda: self.launch("audio")).pack(side="left", padx=(0, 6))
            ttk.Button(regeneration, text="Validate Outputs", command=lambda: self.launch("validate")).pack(side="left")
            exports = ttk.Frame(outer)
            exports.pack(fill="x", pady=7)
            actions = [
                ("Export Video", lambda: self.launch("export")),
                ("Export Dialogue WAV Files", lambda: self.export_audio("voices", "dialogue_wav.zip")),
                ("Export Background Music", lambda: self.export_audio("music", "background_music.zip")),
                ("Export Sound Effects", lambda: self.export_audio("sound_effects", "sound_effects.zip")),
                ("Open Output Folder", lambda: self.open(OUTPUT)),
            ]
            for index, (label, callback) in enumerate(actions):
                ttk.Button(exports, text=label, command=callback).pack(side="left", padx=(0, 5), fill="x", expand=True)
            ttk.Label(outer, textvariable=self.status, wraplength=1120).pack(anchor="w", pady=(5, 2))
            self.bar = ttk.Progressbar(outer, mode="determinate", maximum=60)
            self.bar.pack(fill="x")
            ttk.Label(outer, textvariable=self.details, style="Sub.TLabel", wraplength=1120).pack(anchor="w", pady=(3, 8))
            self.tabs = ttk.Notebook(outer)
            self.tabs.pack(fill="both", expand=True)
            self.asset_tab = ttk.Frame(self.tabs, padding=8)
            self.timeline_tab = ttk.Frame(self.tabs)
            self.log_tab = ttk.Frame(self.tabs)
            self.tabs.add(self.asset_tab, text="Character references")
            self.tabs.add(self.timeline_tab, text="Timeline")
            self.tabs.add(self.log_tab, text="Generation log")
            self.asset_controls = ttk.Frame(self.asset_tab)
            self.asset_controls.pack(fill="x")
            ttk.Button(self.asset_controls, text="Refresh references", command=self.refresh_assets).pack(side="left")
            ttk.Button(self.asset_controls, text="Play sample", command=lambda: self.open(OUTPUT / "sample.mp4")).pack(side="left", padx=5)
            ttk.Button(self.asset_controls, text="Play episode", command=lambda: self.open(episode_video_path())).pack(side="left")
            self.asset_grid = ttk.Frame(self.asset_tab)
            self.asset_grid.pack(fill="both", expand=True, pady=10)
            self.timeline_text = scrolledtext.ScrolledText(self.timeline_tab, wrap="none", font=("Consolas", 9))
            self.timeline_text.pack(fill="both", expand=True)
            self.log = scrolledtext.ScrolledText(self.log_tab, wrap="word", font=("Consolas", 9), state="disabled")
            self.log.pack(fill="both", expand=True)
            ttk.Label(outer, text="Voice accent, neural backends and Windows support are reported in quality_report.json; selecting a label does not install a model.", style="Sub.TLabel", wraplength=1120).pack(anchor="w", pady=(8, 0))

        def load_settings(self):
            try:
                saved = json.loads((OUTPUT / "user_settings.json").read_text(encoding="utf-8"))
                self.story.insert("1.0", saved.get("story_input", ""))
                for label, key in STYLES.items():
                    if key == saved.get("anime_style"):
                        self.style.set(label)
            except (OSError, ValueError):
                self.story.insert("1.0", "Preserve the ten-section story, character identities, and the Origin Weaving mystery. Prioritize clear combat staging and compassionate character choices.")

        def save_settings(self):
            settings = {
                "story_input": self.story.get("1.0", "end").strip(),
                "duration_seconds": 600,
                "anime_style": STYLES[self.style.get()],
                "requested_voice": "Indian English",
                "production_mode": MODES[self.mode.get()],
            }
            path = OUTPUT / "user_settings.json"
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(path)

        def append_log(self, text):
            self.log.configure(state="normal")
            self.log.insert("end", text if text.endswith("\n") else text + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")

        def launch(self, action, shot=None):
            if self.worker and self.worker.is_alive():
                messagebox.showinfo("Already running", "A production command is still running. You can request a pause and resume after it reaches a safe checkpoint.")
                return
            if MODES[self.mode.get()] != "hybrid" and action not in {"validate", "export"}:
                messagebox.showinfo("Backend not configured", "This installation currently supports Mode 2. Neural or advanced generation requires a separately configured, validated backend. No remote service will be invoked.")
                return
            if not (ROOT / "pipeline.py").exists():
                messagebox.showerror("Pipeline missing", "pipeline.py is missing from the application directory.")
                return
            self.save_settings()
            command = pipeline_command(action, shot)
            self.status.set(f"Starting {action}…")
            self.tabs.select(self.log_tab)
            self.append_log(f"> {subprocess.list2cmdline(command)}")
            def run():
                try:
                    self.process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)
                    for line in self.process.stdout:
                        self.events.put(("log", line))
                    code = self.process.wait()
                    self.events.put(("done", action, code))
                except Exception as exc:
                    self.events.put(("error", str(exc)))
                finally:
                    self.process = None
            self.worker = threading.Thread(target=run, daemon=True)
            self.worker.start()

        def poll(self):
            try:
                while True:
                    event = self.events.get_nowait()
                    if event[0] == "log":
                        self.append_log(event[1])
                    elif event[0] == "done":
                        self.append_log(f"{event[1]} exited with code {event[2]}.")
                        self.status.set(f"{event[1]} finished." if event[2] == 0 else f"{event[1]} failed; inspect the log for the actual error.")
                        self.refresh_assets()
                    elif event[0] == "error":
                        self.append_log(event[1])
                        self.status.set("Command could not run; inspect the log.")
            except queue.Empty:
                pass
            progress = read_progress()
            if progress:
                total = max(1, int(progress.get("total_shots", 60)))
                completed = max(0, min(total, int(progress.get("completed_shots", 0))))
                self.bar.configure(maximum=total, value=completed)
                self.details.set(f"{completed}/{total} shots · stage: {progress.get('stage', 'unknown')} · status: {progress.get('status', 'unknown')} · current shot: {progress.get('current_shot', '—')} · {progress.get('message', '')}")
            self.window.after(500, self.poll)

        def pause(self):
            (OUTPUT / "PAUSE").touch()
            self.status.set("Pause requested. Rendering will stop at a safe checkpoint.")
            self.append_log("Pause sentinel written to output/PAUSE.")

        def resume(self):
            (OUTPUT / "PAUSE").unlink(missing_ok=True)
            if self.worker and self.worker.is_alive():
                self.status.set("Resume requested; active worker can continue.")
                return
            self.launch("all")

        def regenerate(self):
            try:
                shot = int(self.shot.get())
                pipeline_command("render", shot)
            except ValueError as exc:
                messagebox.showerror("Invalid shot", str(exc))
                return
            self.launch("render", shot)

        def show_timeline(self):
            path = OUTPUT / "episode01_timeline.json"
            try:
                timeline = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                messagebox.showinfo("Timeline unavailable", f"Generate assets first.\n{exc}")
                return
            self.timeline_text.delete("1.0", "end")
            self.timeline_text.insert("1.0", json.dumps(timeline, ensure_ascii=False, indent=2))
            self.tabs.select(self.timeline_tab)

        def refresh_assets(self):
            for child in self.asset_grid.winfo_children():
                child.destroy()
            self.preview_images.clear()
            paths = sorted((OUTPUT / "characters").rglob("*.png")) if (OUTPUT / "characters").exists() else []
            if not paths:
                ttk.Label(self.asset_grid, text="Character references appear here after asset generation.").pack(anchor="w")
                return
            try:
                from PIL import Image, ImageTk
            except ImportError:
                ttk.Label(self.asset_grid, text="Install Pillow to view references. Files are available in output/characters.").pack(anchor="w")
                return
            # Prefer one master sheet per character, with actual file-open access.
            selected = []
            for name in ["kael", "mira", "riven", "elder"]:
                matching = [p for p in paths if name in str(p).lower()]
                if matching:
                    selected.append(matching[0])
            selected = selected or paths[:4]
            for index, path in enumerate(selected[:4]):
                tile = ttk.Frame(self.asset_grid, padding=5)
                tile.grid(row=0, column=index, sticky="nsew")
                self.asset_grid.columnconfigure(index, weight=1)
                try:
                    with Image.open(path) as picture:
                        picture = picture.convert("RGB")
                        picture.thumbnail((245, 220))
                        preview = ImageTk.PhotoImage(picture)
                    self.preview_images.append(preview)
                    ttk.Button(tile, image=preview, command=lambda p=path: self.open(p)).pack()
                    ttk.Label(tile, text=path.stem, wraplength=245).pack(pady=3)
                except OSError as exc:
                    ttk.Label(tile, text=str(exc), wraplength=245).pack()

        def load_notes(self):
            selected = filedialog.askopenfilename(title="Load episode direction notes", filetypes=[("Text / JSON", "*.txt *.md *.json"), ("All files", "*.*")])
            if not selected:
                return
            try:
                text = Path(selected).read_text(encoding="utf-8-sig")
                self.story.delete("1.0", "end")
                self.story.insert("1.0", text)
            except (OSError, UnicodeError) as exc:
                messagebox.showerror("Cannot load notes", str(exc))

        def export_audio(self, directory, default_name):
            selected = filedialog.asksaveasfilename(title="Export generated audio", defaultextension=".zip", initialfile=default_name, filetypes=[("ZIP archive", "*.zip")])
            if not selected:
                return
            try:
                count = archive_audio(OUTPUT / directory, Path(selected))
                messagebox.showinfo("Audio exported", f"Exported {count} generated audio files to:\n{selected}")
            except (OSError, ValueError) as exc:
                messagebox.showerror("Export unavailable", str(exc))

        def open(self, path):
            try:
                open_local(path)
            except (OSError, ValueError) as exc:
                messagebox.showinfo("Output unavailable", str(exc))

        def close(self):
            if self.worker and self.worker.is_alive():
                messagebox.showwarning(
                    "Production is running",
                    "Keep this window open while its production worker is active. "
                    "Pause keeps the generation process alive. Resume it here, "
                    "then wait for the command to finish before closing.",
                )
                return
            self.save_settings()
            self.window.destroy()

    window = tk.Tk()
    ProductionApp(window)
    window.mainloop()


if __name__ == "__main__":
    main()
