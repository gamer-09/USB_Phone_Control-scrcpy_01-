import queue
import subprocess
import threading
import time
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import ttk

# ---------------------------------------------------------------------------
# Palette (Catppuccin Mocha-inspired dark theme)
# ---------------------------------------------------------------------------
PALETTE = {
    "bg": "#1e1e2e",
    "bg_alt": "#181825",
    "surface": "#313244",
    "surface_alt": "#45475a",
    "border": "#45475a",
    "text": "#cdd6f4",
    "muted": "#a6adc8",
    "accent": "#89b4fa",
    "accent_hover": "#b4befe",
    "green": "#a6e3a1",
    "green_hover": "#b7e7b3",
    "amber": "#f9e2af",
    "amber_hover": "#e6c97e",
    "red": "#f38ba8",
    "red_hover": "#f5a0b7",
    "purple": "#cba6f7",
    "purple_hover": "#d9c2fa",
    "log_bg": "#11111b",
    "tooltip_bg": "#313244",
}

FONT = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_TITLE = ("Segoe UI", 15, "bold")
FONT_LOG = ("Consolas", 10)

STATUS_COLORS = {
    "idle": PALETTE["muted"],
    "running": PALETTE["amber"],
    "scrcpy": PALETTE["green"],
    "error": PALETTE["red"],
}

# Audio source choices shown in the GUI -> values passed to run.ps1
# (None means "no audio", passed as -NoAudio)
AUDIO_SOURCES: dict[str, str | None] = {
    "Phone audio": "output",
    "Microphone": "mic",
    "Off": None,
}


class Tooltip:
    """Lightweight hover tooltip for any widget."""

    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, event=None):
        if self.tip is not None or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tip,
            text=self.text,
            justify="left",
            bg=PALETTE["tooltip_bg"],
            fg=PALETTE["text"],
            font=FONT_SMALL,
            padx=8,
            pady=5,
        )
        label.pack()

    def _hide(self, event=None):
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("USB Phone Control (scrcpy)")
        self.geometry("1000x700")
        self.minsize(880, 600)
        self.configure(bg=PALETTE["bg"])
        self._build_styles()

        self._root_dir = Path(__file__).resolve().parent
        self._scripts_dir = self._root_dir / "scripts"

        self._log_queue: queue.Queue[tuple | str] = queue.Queue()
        self._active_proc: subprocess.Popen[str] | None = None
        self._scrcpy_proc: subprocess.Popen[str] | None = None
        self._current_script: str | None = None
        self._status_kind = "idle"
        self._cmd_start_time: float | None = None
        self._pulse = False
        self._quick_active = False
        self._quick_steps: list[tuple[str, list[str], bool]] = []
        self._quick_step_index = 0

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_quit)
        self.after(50, self._drain_log_queue)
        self.after(250, self._tick_status)

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------
    def _build_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            ".",
            font=FONT,
            background=PALETTE["bg"],
            foreground=PALETTE["text"],
        )
        style.configure("TFrame", background=PALETTE["bg"])
        style.configure("TLabel", background=PALETTE["bg"], foreground=PALETTE["text"])
        style.configure("Muted.TLabel", foreground=PALETTE["muted"])
        style.configure("Title.TLabel", font=FONT_TITLE)
        style.configure("Subtitle.TLabel", font=FONT_SMALL, foreground=PALETTE["muted"])

        style.configure(
            "TLabelframe",
            background=PALETTE["bg"],
            bordercolor=PALETTE["border"],
            relief="flat",
        )
        style.configure(
            "TLabelframe.Label",
            background=PALETTE["bg"],
            foreground=PALETTE["muted"],
            font=FONT_SMALL,
        )

        style.configure(
            "TButton",
            font=FONT,
            padding=(12, 7),
            relief="flat",
            background=PALETTE["surface"],
            foreground=PALETTE["text"],
            bordercolor=PALETTE["surface_alt"],
            lightcolor=PALETTE["surface"],
            darkcolor=PALETTE["surface"],
            focuscolor=PALETTE["accent"],
        )
        style.map(
            "TButton",
            background=[("pressed", PALETTE["surface_alt"]), ("active", PALETTE["surface_alt"])],
            foreground=[("disabled", PALETTE["muted"])],
        )

        style.configure(
            "Accent.TButton",
            background=PALETTE["accent"],
            foreground=PALETTE["bg"],
            bordercolor=PALETTE["accent"],
            lightcolor=PALETTE["accent"],
            darkcolor=PALETTE["accent"],
        )
        style.map(
            "Accent.TButton",
            background=[("pressed", PALETTE["accent_hover"]), ("active", PALETTE["accent_hover"])],
            foreground=[("disabled", PALETTE["bg"])],
        )

        style.configure(
            "Success.TButton",
            background=PALETTE["green"],
            foreground=PALETTE["bg"],
            bordercolor=PALETTE["green"],
            lightcolor=PALETTE["green"],
            darkcolor=PALETTE["green"],
        )
        style.map(
            "Success.TButton",
            background=[("pressed", PALETTE["green_hover"]), ("active", PALETTE["green_hover"])],
            foreground=[("disabled", PALETTE["bg"])],
        )

        style.configure(
            "Danger.TButton",
            background=PALETTE["red"],
            foreground=PALETTE["bg"],
            bordercolor=PALETTE["red"],
            lightcolor=PALETTE["red"],
            darkcolor=PALETTE["red"],
        )
        style.map(
            "Danger.TButton",
            background=[("pressed", PALETTE["red_hover"]), ("active", PALETTE["red_hover"])],
            foreground=[("disabled", PALETTE["bg"])],
        )

        style.configure(
            "Purple.TButton",
            background=PALETTE["purple"],
            foreground=PALETTE["bg"],
            bordercolor=PALETTE["purple"],
            lightcolor=PALETTE["purple"],
            darkcolor=PALETTE["purple"],
        )
        style.map(
            "Purple.TButton",
            background=[("pressed", PALETTE["purple_hover"]), ("active", PALETTE["purple_hover"])],
            foreground=[("disabled", PALETTE["bg"])],
        )

        style.configure(
            "TEntry",
            fieldbackground=PALETTE["surface"],
            foreground=PALETTE["text"],
            insertcolor=PALETTE["accent"],
            bordercolor=PALETTE["border"],
            lightcolor=PALETTE["border"],
            darkcolor=PALETTE["border"],
            padding=6,
        )
        style.map("TEntry", bordercolor=[("focus", PALETTE["accent"])])

        style.configure(
            "TCombobox",
            fieldbackground=PALETTE["surface"],
            background=PALETTE["surface"],
            foreground=PALETTE["text"],
            arrowcolor=PALETTE["muted"],
            bordercolor=PALETTE["border"],
            lightcolor=PALETTE["border"],
            darkcolor=PALETTE["border"],
            padding=4,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", PALETTE["surface"])],
            foreground=[("readonly", PALETTE["text"])],
            selectbackground=[("readonly", PALETTE["surface"])],
            selectforeground=[("readonly", PALETTE["text"])],
        )

        style.configure(
            "Vertical.TScrollbar",
            background=PALETTE["surface"],
            troughcolor=PALETTE["bg"],
            bordercolor=PALETTE["bg"],
            arrowcolor=PALETTE["muted"],
        )
        style.map("Vertical.TScrollbar", background=[("active", PALETTE["surface_alt"])])

        style.configure("TSeparator", background=PALETTE["border"])

    def _make_button(self, parent, text, style_name, command, tip=None) -> ttk.Button:
        btn = ttk.Button(parent, text=text, style=style_name, command=command, cursor="hand2")
        if tip:
            Tooltip(btn, tip)
        return btn

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # Header
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="USB Phone Control", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Android via scrcpy — USB & Wireless", style="Subtitle.TLabel").grid(
            row=1, column=0, sticky="w"
        )

        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.grid(row=1, column=0, sticky="ew", padx=16, pady=8)
        toolbar.columnconfigure(0, weight=1)

        self.btn_setup = self._make_button(
            toolbar,
            "Setup (download tools)",
            "Accent.TButton",
            self.on_setup,
            "Downloads adb (platform-tools) and scrcpy into tools\\",
        )
        self.btn_setup.grid(row=0, column=0, padx=(0, 8))

        self.btn_check = self._make_button(
            toolbar,
            "Check device",
            "TButton",
            self.on_check,
            "Lists connected devices (adb devices -l)",
        )
        self.btn_check.grid(row=0, column=1, padx=(0, 8))

        self.btn_start = self._make_button(
            toolbar,
            "Start scrcpy",
            "Success.TButton",
            self.on_start,
            "Starts mirroring. Uses Wi-Fi settings if a Connect IP:port is entered.",
        )
        self.btn_start.grid(row=0, column=2, padx=(0, 8))

        self.btn_stop = self._make_button(
            toolbar,
            "Stop scrcpy",
            "Danger.TButton",
            self.on_stop,
            "Closes the running scrcpy window",
        )
        self.btn_stop.grid(row=0, column=3, padx=(0, 8))

        self.btn_clear = self._make_button(
            toolbar,
            "Clear log",
            "TButton",
            self.on_clear,
            "Clears the log panel below",
        )
        self.btn_clear.grid(row=0, column=4, padx=(0, 8))

        ttk.Label(toolbar, text="Audio:", style="Muted.TLabel").grid(row=0, column=5, padx=(8, 4))
        self.audio_source = ttk.Combobox(
            toolbar,
            state="readonly",
            width=14,
            values=list(AUDIO_SOURCES.keys()),
            style="TCombobox",
        )
        self.audio_source.current(0)
        self.audio_source.grid(row=0, column=6, padx=(0, 8))
        Tooltip(
            self.audio_source,
            "Which audio is forwarded to the PC: the phone's own audio output, "
            "the phone's microphone (acts as a remote mic for the PC), or none. "
            "With 'Microphone', the phone may show a mic-in-use indicator.",
        )

        # Wireless section
        wifi = ttk.LabelFrame(self, text="  Wireless debugging (Wi-Fi)  ")
        wifi.grid(row=2, column=0, sticky="ew", padx=16, pady=8)
        wifi.columnconfigure(7, weight=1)

        ttk.Label(wifi, text="Pair IP:port", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w", padx=(14, 6), pady=(12, 0)
        )
        self.pair_hostport = ttk.Entry(wifi, width=20)
        self.pair_hostport.grid(row=1, column=0, sticky="w", padx=(14, 6), pady=(4, 10))
        self.pair_hostport.bind("<Return>", lambda e: self.on_wireless_pair())
        Tooltip(self.pair_hostport, "IP:port shown on the phone under: Wireless debugging > Pair device with pairing code")

        ttk.Label(wifi, text="Pairing code", style="Muted.TLabel").grid(
            row=0, column=1, sticky="w", padx=(0, 6), pady=(12, 0)
        )
        self.pair_code = ttk.Entry(wifi, width=10)
        self.pair_code.grid(row=1, column=1, sticky="w", padx=(0, 6), pady=(4, 10))
        self.pair_code.bind("<Return>", lambda e: self.on_wireless_pair())
        Tooltip(self.pair_code, "6-digit pairing code shown on the phone")

        self.btn_pair = self._make_button(
            wifi, "Pair", "Accent.TButton", self.on_wireless_pair, "Runs: adb pair <ip:port> <code>"
        )
        self.btn_pair.grid(row=1, column=2, sticky="w", padx=(4, 16), pady=(4, 10))

        ttk.Label(wifi, text="Connect IP:port", style="Muted.TLabel").grid(
            row=0, column=3, sticky="w", padx=(0, 6), pady=(12, 0)
        )
        self.connect_hostport = ttk.Entry(wifi, width=20)
        self.connect_hostport.grid(row=1, column=3, sticky="w", padx=(0, 6), pady=(4, 10))
        self.connect_hostport.bind("<Return>", lambda e: self.on_wireless_connect())
        Tooltip(self.connect_hostport, "IP:port shown on the Wireless debugging main screen (often a different port than pairing)")

        self.btn_connect = self._make_button(
            wifi, "Connect", "Accent.TButton", self.on_wireless_connect, "Runs: adb connect <ip:port>"
        )
        self.btn_connect.grid(row=1, column=4, sticky="w", padx=(4, 8), pady=(4, 10))

        self.btn_disconnect = self._make_button(
            wifi, "Disconnect", "TButton", self.on_wireless_disconnect, "Runs: adb disconnect [<ip:port>]"
        )
        self.btn_disconnect.grid(row=1, column=5, sticky="w", padx=(0, 8), pady=(4, 10))

        self.btn_status = self._make_button(
            wifi, "Status", "TButton", self.on_wireless_status, "Lists connected devices (adb devices -l)"
        )
        self.btn_status.grid(row=1, column=6, sticky="w", padx=(0, 14), pady=(4, 10))

        self.btn_install_lyto = self._make_button(
            wifi,
            "Install Lyto",
            "TButton",
            self.on_install_lyto,
            "Installs lyto (QR pairing helper) via pip — requires internet",
        )
        self.btn_install_lyto.grid(row=2, column=0, sticky="w", padx=(14, 6), pady=(0, 12))

        self.btn_qr_pair_lyto = self._make_button(
            wifi,
            "QR Pair (Lyto)",
            "Purple.TButton",
            self.on_qr_pair_lyto,
            "Opens a QR code window — scan it from the phone (Wireless debugging > Pair device with QR code)",
        )
        self.btn_qr_pair_lyto.grid(row=2, column=1, sticky="w", padx=(0, 6), pady=(0, 12))

        self.btn_quick = self._make_button(
            wifi,
            "Quick connect  (pair + connect + start scrcpy)",
            "Success.TButton",
            self.on_quick_connect,
            "Runs Pair, Connect and Start scrcpy in one click using the fields above. "
            "Pairing is skipped if the pair fields are empty.",
        )
        self.btn_quick.grid(row=3, column=0, columnspan=8, sticky="ew", padx=14, pady=(0, 12))

        # Log panel
        log_frame = ttk.Frame(self)
        log_frame.grid(row=3, column=0, sticky="nsew", padx=16, pady=8)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log = tk.Text(
            log_frame,
            wrap="word",
            state="disabled",
            bg=PALETTE["log_bg"],
            fg=PALETTE["text"],
            insertbackground=PALETTE["accent"],
            font=FONT_LOG,
            padx=10,
            pady=8,
            borderwidth=0,
            relief="flat",
            highlightthickness=1,
            highlightbackground=PALETTE["border"],
            highlightcolor=PALETTE["border"],
            selectbackground=PALETTE["accent"],
            selectforeground=PALETTE["bg"],
        )
        self.log.grid(row=0, column=0, sticky="nsew")
        self.log.tag_configure("cmd", foreground=PALETTE["accent"])
        self.log.tag_configure("error", foreground=PALETTE["red"])
        self.log.tag_configure("exit_ok", foreground=PALETTE["muted"])
        self.log.tag_configure("exit_err", foreground=PALETTE["amber"])

        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scroll.set)

        # Separator + status bar
        ttk.Separator(self, orient="horizontal").grid(row=4, column=0, sticky="ew", padx=16)

        statusbar = ttk.Frame(self)
        statusbar.grid(row=5, column=0, sticky="ew", padx=16, pady=(8, 12))
        statusbar.columnconfigure(2, weight=1)

        self.status_dot = ttk.Label(statusbar, text="●", font=FONT_SMALL, foreground=PALETTE["muted"])
        self.status_dot.grid(row=0, column=0, padx=(2, 6))

        self.status_var = tk.StringVar(value="Idle")
        self.status = ttk.Label(statusbar, textvariable=self.status_var, style="Muted.TLabel")
        self.status.grid(row=0, column=1, sticky="w")

        self.runtime_var = tk.StringVar(value="")
        self.runtime = ttk.Label(statusbar, textvariable=self.runtime_var, style="Muted.TLabel")
        self.runtime.grid(row=0, column=3, sticky="e", padx=(8, 8))

        self.btn_quit = self._make_button(
            statusbar, "Quit", "Danger.TButton", self.on_quit, "Closes the app and stops scrcpy if it is running"
        )
        self.btn_quit.grid(row=0, column=4, padx=(8, 0))

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    def _append_log(self, text: str, tag: str | None = None):
        self.log.configure(state="normal")
        self.log.insert("end", text, tag)
        self.log.configure(state="disabled")
        self.log.see("end")

    def _drain_log_queue(self):
        try:
            while True:
                item = self._log_queue.get_nowait()
                # Status updates come from worker threads; apply them on the main thread
                if isinstance(item, tuple) and len(item) == 3 and item[0] == "__status__":
                    _, text, kind = item
                    self._set_status(text, kind)
                    continue
                # Workflow step finished; run its callback on the main thread
                if isinstance(item, tuple) and len(item) == 3 and item[0] == "__done__":
                    _, callback, rc = item
                    try:
                        callback(rc)
                    except Exception as exc:  # never let a callback break the UI loop
                        self._append_log(f"ERROR in workflow callback: {exc}\n", "error")
                    continue
                if isinstance(item, tuple):
                    text, tag = item
                else:
                    text, tag = item, None
                if tag is None:
                    tag = self._tag_for_text(text)
                self._append_log(text, tag)
        except queue.Empty:
            pass
        self.after(50, self._drain_log_queue)

    @staticmethod
    def _tag_for_text(text: str) -> str | None:
        lower = text.lower()
        if "error" in lower or "failed" in lower or "not found" in lower:
            return "error"
        return None

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------
    def _set_status(self, text: str, kind: str = "idle"):
        self.status_var.set(text)
        self._status_kind = kind
        if kind == "running":
            self._cmd_start_time = time.monotonic()
        else:
            self._cmd_start_time = None
            self.runtime_var.set("")
        self._update_status_dot()

    def _update_status_dot(self):
        color = STATUS_COLORS.get(self._status_kind, PALETTE["muted"])
        self.status_dot.configure(foreground=color)

    def _tick_status(self):
        if self._status_kind == "running" and self._cmd_start_time is not None:
            elapsed = time.monotonic() - self._cmd_start_time
            self.runtime_var.set(f"{int(elapsed)}s")
            # subtle pulse animation while a command is running
            self._pulse = not self._pulse
            color = PALETTE["amber"] if self._pulse else PALETTE["amber_hover"]
            self.status_dot.configure(foreground=color)
        self.after(250, self._tick_status)

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------
    def _run_powershell_script(
        self,
        script_name: str,
        *,
        as_scrcpy: bool = False,
        extra_args: list[str] | None = None,
        on_done: Callable[[int], None] | None = None,
    ):
        script_path = (self._scripts_dir / script_name).resolve()
        if not script_path.exists():
            self._log_queue.put(f"ERROR: Script not found: {script_path}\n")
            if on_done is not None:
                on_done(1)
            return

        if as_scrcpy:
            if self._scrcpy_proc is not None and self._scrcpy_proc.poll() is None:
                self._log_queue.put("scrcpy is already running.\n")
                # For a workflow, scrcpy already running satisfies the "start" step
                if on_done is not None:
                    on_done(0)
                return
        else:
            if self._active_proc is not None and self._active_proc.poll() is None:
                self._log_queue.put("Another command is already running.\n")
                if on_done is not None:
                    on_done(1)
                return

        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
        ]

        if extra_args:
            cmd.extend(extra_args)

        self._current_script = script_name
        self._log_queue.put((f"\n$ {' '.join(cmd)}\n", "cmd"))
        proc = subprocess.Popen(
            cmd,
            cwd=str(self._root_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        if as_scrcpy:
            self._scrcpy_proc = proc
            self._set_status("scrcpy running", "scrcpy")
        else:
            self._active_proc = proc
            self._set_status(f"Running {script_name}", "running")

        t = threading.Thread(target=self._read_proc_output, args=(proc, as_scrcpy, on_done), daemon=True)
        t.start()

    def _read_proc_output(
        self,
        proc: subprocess.Popen[str],
        as_scrcpy: bool,
        on_done: Callable[[int], None] | None = None,
    ):
        try:
            if proc.stdout is not None:
                for line in proc.stdout:
                    self._log_queue.put((line, None))
        finally:
            rc = proc.wait()
            tag = "exit_ok" if rc == 0 else "exit_err"
            self._log_queue.put((f"\n[exit code: {rc}]\n", tag))
            if as_scrcpy:
                self._scrcpy_proc = None
                self._log_queue.put(("__status__", "Idle", "idle"))
            else:
                self._active_proc = None
                if rc == 0:
                    self._log_queue.put(("__status__", "Idle", "idle"))
                else:
                    name = self._current_script or "command"
                    self._log_queue.put(("__status__", f"Failed: {name}", "error"))
            if on_done is not None:
                self._log_queue.put(("__done__", on_done, rc))

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def on_setup(self):
        self._run_powershell_script("setup.ps1")

    def on_check(self):
        self._run_powershell_script("check-device.ps1")

    def on_start(self):
        hostport = self.connect_hostport.get().strip()
        extra: list[str] = []
        source_value = AUDIO_SOURCES.get(self.audio_source.get())
        if source_value is None:
            extra.append("-NoAudio")
        else:
            extra.extend(["-AudioSource", source_value])
        if hostport:
            extra.extend(["-Serial", hostport])
        self._run_powershell_script("run.ps1", as_scrcpy=True, extra_args=extra)

    def on_wireless_pair(self):
        hostport = self.pair_hostport.get().strip()
        code = self.pair_code.get().strip()
        if not hostport:
            self._log_queue.put("Enter Pair IP:port from Android Wireless debugging > Pair using pairing code.\n")
            return
        args = ["-PairHostPort", hostport]
        if code:
            args.extend(["-PairingCode", code])
        self._run_powershell_script("wireless-pair.ps1", extra_args=args)

    def on_wireless_connect(self):
        hostport = self.connect_hostport.get().strip()
        if not hostport:
            self._log_queue.put("Enter Connect IP:port from Android Wireless debugging main screen.\n")
            return
        self._run_powershell_script("wireless-connect.ps1", extra_args=["-HostPort", hostport])

    def on_wireless_disconnect(self):
        hostport = self.connect_hostport.get().strip()
        args: list[str] = []
        if hostport:
            args = ["-HostPort", hostport]
        self._run_powershell_script("wireless-disconnect.ps1", extra_args=args)

    def on_wireless_status(self):
        self._run_powershell_script("wireless-status.ps1")

    def on_quick_connect(self):
        """One-click wireless workflow: pair (if fields given) -> connect -> start scrcpy."""
        if self._quick_active:
            self._log_queue.put("A quick-connect workflow is already running.\n")
            return

        connect_hostport = self.connect_hostport.get().strip()
        if not connect_hostport:
            self._log_queue.put("Enter Connect IP:port from Android Wireless debugging main screen.\n")
            return

        self._quick_steps = []
        pair_hostport = self.pair_hostport.get().strip()
        if pair_hostport:
            pair_args = ["-PairHostPort", pair_hostport]
            pair_code = self.pair_code.get().strip()
            if pair_code:
                pair_args.extend(["-PairingCode", pair_code])
            self._quick_steps.append(("wireless-pair.ps1", pair_args, False))
        self._quick_steps.append(("wireless-connect.ps1", ["-HostPort", connect_hostport], False))
        run_args = ["-Serial", connect_hostport]
        source_value = AUDIO_SOURCES.get(self.audio_source.get())
        if source_value is None:
            run_args.append("-NoAudio")
        else:
            run_args.extend(["-AudioSource", source_value])
        self._quick_steps.append(("run.ps1", run_args, True))

        self._quick_step_index = 0
        self._quick_active = True
        self._log_queue.put("\n--- Quick connect: pair -> connect -> start scrcpy ---\n")
        self._run_quick_step()

    def _run_quick_step(self):
        if self._quick_step_index >= len(self._quick_steps):
            self._quick_active = False
            return
        name, args, as_scrcpy = self._quick_steps[self._quick_step_index]
        self._log_queue.put(f"--- Quick connect step {self._quick_step_index + 1}/{len(self._quick_steps)}: {name} ---\n")
        if as_scrcpy:
            self._log_queue.put("Quick connect complete — scrcpy is starting.\n")
        self._run_powershell_script(name, as_scrcpy=as_scrcpy, extra_args=args, on_done=self._on_quick_step_done)

    def _on_quick_step_done(self, rc: int):
        name = self._quick_steps[self._quick_step_index][0]
        if rc != 0:
            self._quick_active = False
            self._log_queue.put(f"Quick connect aborted: {name} failed (exit code {rc}). Fix it and try again.\n")
            self._set_status("Quick connect failed", "error")
            return
        self._quick_step_index += 1
        if self._quick_step_index >= len(self._quick_steps):
            self._quick_active = False
            self._log_queue.put("Quick connect workflow complete.\n")
            return
        self._run_quick_step()

    def on_install_lyto(self):
        self._log_queue.put("This will install lyto via pip (internet download).\n")
        self._run_powershell_script("install-lyto.ps1")

    def on_qr_pair_lyto(self):
        self._log_queue.put("Opening Lyto QR pairing window. Use Android: Wireless debugging > Pair device with QR code.\n")
        self._run_powershell_script("lyto-qr.ps1")

    def on_stop(self):
        proc = self._scrcpy_proc
        if proc is None or proc.poll() is not None:
            self._log_queue.put("scrcpy is not running.\n")
            return

        self._log_queue.put("Stopping scrcpy...\n")
        try:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        finally:
            self._scrcpy_proc = None
            self._set_status("Idle", "idle")

    def on_clear(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def on_quit(self):
        try:
            if self._scrcpy_proc is not None and self._scrcpy_proc.poll() is None:
                self._scrcpy_proc.terminate()
        finally:
            self.destroy()


if __name__ == "__main__":
    App().mainloop()
