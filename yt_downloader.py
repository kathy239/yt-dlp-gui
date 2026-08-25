import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import sys
import re
import json
import shutil
import urllib.request
import urllib.error

# ─── Theme ────────────────────────────────────────────────────────────────────
BG        = "#0d0d0d"
SURFACE   = "#1a1a1a"
PANEL     = "#222222"
ACCENT    = "#ff3c3c"
ACCENT2   = "#ff7043"
TEXT      = "#f0f0f0"
SUBTEXT   = "#888888"
SUCCESS   = "#00e676"
WARNING   = "#ffab40"
BORDER    = "#333333"
FONT_MONO = ("Consolas", 9)
FONT_UI   = ("Segoe UI", 10)
FONT_SM   = ("Segoe UI", 9)

# ─── Config defaults ─────────────────────────────────────────────────────────
# Use local path. 
# Downloads will now default to the same folder as the script
SCRIPT_DIR  = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "yt_downloader_config.json")

DEFAULT_CFG = {
    "github_api_url": "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest",
    "asset_name":     "yt-dlp.exe",
    "ytdlp_dir":      SCRIPT_DIR,
    "auto_update":    False,
    "output_dir":     SCRIPT_DIR,
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CONFIG_FILE, "r") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Settings Dialog
# ═══════════════════════════════════════════════════════════════════════════════
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, cfg: dict, on_save):
        super().__init__(parent)
        self.title("Settings")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        self._cfg     = dict(cfg)
        self._on_save = on_save
        self._build()
        self.update_idletasks()
        w, h = 580, 420
        px = parent.winfo_rootx() + parent.winfo_width()  // 2 - w // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - h // 2
        self.geometry(f"{w}x{h}+{px}+{py}")

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=BG, padx=20, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚙  Settings", font=("Segoe UI", 14, "bold"),
                 fg=TEXT, bg=BG).pack(side="left")
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(self, bg=BG, padx=22, pady=6)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)

        def section(text):
            tk.Label(body, text=text, font=("Segoe UI", 9, "bold"),
                     fg=ACCENT2, bg=BG, anchor="w").pack(fill="x", pady=(10, 2))

        def hint(text):
            tk.Label(body, text=text, font=("Segoe UI", 8), fg=SUBTEXT,
                     bg=BG, wraplength=530, justify="left", anchor="w").pack(
                fill="x", pady=(0, 2))

        def entry_field(var):
            e = tk.Entry(body, textvariable=var, bg=PANEL, fg=TEXT,
                         insertbackground=TEXT, relief="flat", font=FONT_UI, bd=6,
                         highlightthickness=1, highlightbackground=BORDER)
            e.pack(fill="x", pady=(0, 2))
            return e

        # ── GitHub API URL ────────────────────────────────────────────────────
        section("GitHub Releases API URL")
        self._api_var = tk.StringVar(value=self._cfg["github_api_url"])
        row1 = tk.Frame(body, bg=BG)
        row1.pack(fill="x")
        row1.columnconfigure(0, weight=1)
        tk.Entry(row1, textvariable=self._api_var, bg=PANEL, fg=TEXT,
                 insertbackground=TEXT, relief="flat", font=FONT_UI, bd=6,
                 highlightthickness=1, highlightbackground=BORDER).grid(
            row=0, column=0, sticky="ew")
        tk.Button(row1, text="Reset default",
                  command=lambda: self._api_var.set(DEFAULT_CFG["github_api_url"]),
                  bg=PANEL, fg=SUBTEXT, relief="flat", font=("Segoe UI", 8),
                  padx=8, pady=5, cursor="hand2").grid(row=0, column=1, padx=(6, 0))
        hint("Must be a GitHub API releases/latest URL returning JSON with an 'assets' list.")

        # ── Asset name ────────────────────────────────────────────────────────
        section("Executable asset filename")
        self._asset_var = tk.StringVar(value=self._cfg["asset_name"])
        asset_row = tk.Frame(body, bg=BG)
        asset_row.pack(fill="x")
        tk.Entry(asset_row, textvariable=self._asset_var, bg=PANEL, fg=TEXT,
                 insertbackground=TEXT, relief="flat", font=FONT_UI, bd=6,
                 highlightthickness=1, highlightbackground=BORDER,
                 width=28).pack(side="left")
        hint('Filename exactly as listed in the GitHub release  (e.g. "yt-dlp.exe"  or  "yt-dlp_linux").')

        # ── Save directory ────────────────────────────────────────────────────
        section("Folder to save the yt-dlp executable")
        self._dir_var = tk.StringVar(value=self._cfg["ytdlp_dir"])
        dir_row = tk.Frame(body, bg=BG)
        dir_row.pack(fill="x")
        dir_row.columnconfigure(0, weight=1)
        tk.Entry(dir_row, textvariable=self._dir_var, bg=PANEL, fg=TEXT,
                 insertbackground=TEXT, relief="flat", font=FONT_UI, bd=6,
                 highlightthickness=1, highlightbackground=BORDER).grid(
            row=0, column=0, sticky="ew")
        tk.Button(dir_row, text="Browse",
                  command=self._browse_dir,
                  bg=PANEL, fg=TEXT, relief="flat", font=("Segoe UI", 8),
                  padx=8, pady=5, cursor="hand2").grid(row=0, column=1, padx=(6, 0))
        hint("The executable is saved here and looked up here first when launching downloads.")

        # ── Auto-update toggle ────────────────────────────────────────────────
        self._auto_var = tk.BooleanVar(value=self._cfg["auto_update"])
        tk.Checkbutton(body,
                       text="  Automatically check for yt-dlp updates on startup",
                       variable=self._auto_var,
                       bg=BG, fg=TEXT, selectcolor=PANEL,
                       activebackground=BG, activeforeground=TEXT,
                       font=FONT_UI, cursor="hand2").pack(anchor="w", pady=(12, 0))

        # ── Buttons ───────────────────────────────────────────────────────────
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        btn_bar = tk.Frame(self, bg=BG, padx=20, pady=12)
        btn_bar.pack(fill="x")
        tk.Button(btn_bar, text="Save", command=self._save,
                  bg=ACCENT, fg=TEXT, relief="flat",
                  font=("Segoe UI", 10, "bold"),
                  padx=18, pady=6, cursor="hand2").pack(side="right")
        tk.Button(btn_bar, text="Cancel", command=self.destroy,
                  bg=PANEL, fg=TEXT, relief="flat",
                  font=("Segoe UI", 10),
                  padx=14, pady=6, cursor="hand2").pack(side="right", padx=(0, 8))

    def _browse_dir(self):
        d = filedialog.askdirectory(initialdir=self._dir_var.get())
        if d:
            self._dir_var.set(d)

    def _save(self):
        self._cfg["github_api_url"] = self._api_var.get().strip()
        self._cfg["asset_name"]     = self._asset_var.get().strip()
        self._cfg["ytdlp_dir"]      = self._dir_var.get().strip()
        self._cfg["auto_update"]    = self._auto_var.get()
        save_config(self._cfg)
        self._on_save(self._cfg)
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════════════
#  Main App
# ═══════════════════════════════════════════════════════════════════════════════
class YTDownloader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YT-DLP Downloader")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(720, 650)

        self.cfg = load_config()

        self.output_dir = tk.StringVar(value=self.cfg["output_dir"])
        self.url_var    = tk.StringVar()
        self.mode_var   = tk.StringVar(value="video")
        self.res_var    = tk.StringVar(value="best")
        self.format_var = tk.StringVar(value="mp4")
        self.audio_fmt  = tk.StringVar(value="mp3")
        self.proc       = None
        self.fetching   = False
        self.updating   = False

        self._build_ui()
        self._mode_changed()
        self.output_dir.trace_add("write", lambda *_: self._persist_output_dir())

        if self.cfg.get("auto_update"):
            self.after(1200, lambda: self._run_update(silent=True))

    # ── UI ─────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        outer = tk.Frame(self, bg=BG, padx=20, pady=20)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(5, weight=1)  # log row

        # ── Header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(outer, bg=BG)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        tk.Label(hdr, text="▼", font=("Segoe UI", 22, "bold"),
                 fg=ACCENT, bg=BG).pack(side="left", padx=(0, 8))
        tk.Label(hdr, text="YT-DLP  Downloader", font=("Segoe UI", 18, "bold"),
                 fg=TEXT, bg=BG).pack(side="left")
        self._status_dot = tk.Label(hdr, text="●", font=("Segoe UI", 14),
                                    fg=SUBTEXT, bg=BG)
        self._status_dot.pack(side="right")
        tk.Button(hdr, text="⚙", font=("Segoe UI", 13), fg=SUBTEXT, bg=BG,
                  relief="flat", bd=0, cursor="hand2",
                  activebackground=BG, activeforeground=TEXT,
                  command=self._open_settings).pack(side="right", padx=(0, 6))

        # ── yt-dlp manager strip ─────────────────────────────────────────────
        mgr = self._card(outer, pady=10)
        mgr.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        mgr.columnconfigure(1, weight=1)

        tk.Label(mgr, text="yt-dlp", font=("Segoe UI", 9, "bold"),
                 fg=ACCENT2, bg=SURFACE, anchor="w", width=6).grid(
            row=0, column=0, padx=(0, 10))
        self._ytdlp_lbl = tk.Label(mgr, text="Not checked  —  use 'Check version' or 'Download / Update'",
                                   font=FONT_SM, fg=SUBTEXT, bg=SURFACE, anchor="w")
        self._ytdlp_lbl.grid(row=0, column=1, sticky="w")

        btn_grp = tk.Frame(mgr, bg=SURFACE)
        btn_grp.grid(row=0, column=2, sticky="e")
        self._check_btn = self._btn(btn_grp, "Check version",
                                    self._check_version, small=True)
        self._check_btn.pack(side="left", padx=(0, 6))
        self._upd_btn = self._btn(btn_grp, "⬇  Download / Update",
                                  lambda: self._run_update(silent=False),
                                  color=ACCENT2, small=True)
        self._upd_btn.pack(side="left")

        # Inline update progress (hidden by default)
        self._upd_prog_row = tk.Frame(mgr, bg=SURFACE)
        self._upd_prog_row.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(7, 0))
        self._upd_prog_row.columnconfigure(0, weight=1)
        self._upd_prog_row.grid_remove()

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Orange.Horizontal.TProgressbar",
                        troughcolor=PANEL, background=ACCENT2,
                        bordercolor=PANEL, lightcolor=ACCENT2, darkcolor=ACCENT2)
        style.configure("Red.Horizontal.TProgressbar",
                        troughcolor=PANEL, background=ACCENT,
                        bordercolor=PANEL, lightcolor=ACCENT, darkcolor=ACCENT)

        self._upd_bar = ttk.Progressbar(self._upd_prog_row,
                                        style="Orange.Horizontal.TProgressbar",
                                        mode="determinate", maximum=100, value=0)
        self._upd_bar.grid(row=0, column=0, sticky="ew")
        self._upd_bar_lbl = tk.Label(self._upd_prog_row, text="",
                                     font=FONT_SM, fg=SUBTEXT, bg=SURFACE,
                                     width=22, anchor="e")
        self._upd_bar_lbl.grid(row=0, column=1, padx=(8, 0))

        # ── URL row ──────────────────────────────────────────────────────────
        url_frame = self._card(outer)
        url_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        url_frame.columnconfigure(1, weight=1)
        tk.Label(url_frame, text="URL", font=FONT_UI, fg=SUBTEXT,
                 bg=SURFACE, width=8, anchor="w").grid(row=0, column=0, padx=(0, 8))
        url_entry = self._entry(url_frame, textvariable=self.url_var,
                                placeholder="https://www.youtube.com/watch?v=…")
        url_entry.grid(row=0, column=1, sticky="ew")
        self._fetch_btn = self._btn(url_frame, "Fetch Info",
                                    self._fetch_info, color=ACCENT2)
        self._fetch_btn.grid(row=0, column=2, padx=(8, 0))

        # ── Options row ──────────────────────────────────────────────────────
        opt_frame = self._card(outer)
        opt_frame.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        for i in range(6):
            opt_frame.columnconfigure(i, weight=1 if i in (1, 3, 5) else 0)

        tk.Label(opt_frame, text="Mode", font=FONT_SM, fg=SUBTEXT,
                 bg=SURFACE).grid(row=0, column=0, sticky="w", padx=(0, 6))
        mode_inner = tk.Frame(opt_frame, bg=SURFACE)
        mode_inner.grid(row=0, column=1, sticky="w", padx=(0, 20))
        self._vid_btn = self._toggle(mode_inner, "🎬 Video", "video")
        self._vid_btn.pack(side="left")
        self._aud_btn = self._toggle(mode_inner, "🎵 Audio", "audio")
        self._aud_btn.pack(side="left", padx=(4, 0))

        tk.Label(opt_frame, text="Res", font=FONT_SM, fg=SUBTEXT,
                 bg=SURFACE).grid(row=0, column=2, sticky="w", padx=(0, 6))
        self._res_combo = self._combo(
            opt_frame,
            values=["best","2160p","1440p","1080p","720p","480p","360p","240p","144p"],
            textvariable=self.res_var)
        self._res_combo.grid(row=0, column=3, sticky="ew", padx=(0, 20))

        tk.Label(opt_frame, text="Format", font=FONT_SM, fg=SUBTEXT,
                 bg=SURFACE).grid(row=0, column=4, sticky="w", padx=(0, 6))
        self._fmt_combo = self._combo(opt_frame, values=["mp4","mkv","webm","avi"],
                                      textvariable=self.format_var)
        self._fmt_combo_audio = self._combo(opt_frame,
                                            values=["mp3","m4a","flac","wav","ogg","opus"],
                                            textvariable=self.audio_fmt)
        self._fmt_combo.grid(row=0, column=5, sticky="ew")
        self._fmt_combo_audio.grid(row=0, column=5, sticky="ew")

        # ── Output dir ───────────────────────────────────────────────────────
        dir_frame = self._card(outer)
        dir_frame.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        dir_frame.columnconfigure(1, weight=1)
        tk.Label(dir_frame, text="Save to", font=FONT_UI, fg=SUBTEXT,
                 bg=SURFACE, width=8, anchor="w").grid(row=0, column=0, padx=(0, 8))
        self._entry(dir_frame, textvariable=self.output_dir).grid(
            row=0, column=1, sticky="ew")
        self._btn(dir_frame, "Browse", self._browse).grid(
            row=0, column=2, padx=(8, 0))

        # ── Log ──────────────────────────────────────────────────────────────
        log_outer = self._card(outer, pady=10)
        log_outer.grid(row=5, column=0, sticky="nsew", pady=(0, 8))
        log_outer.columnconfigure(0, weight=1)
        log_outer.rowconfigure(1, weight=1)

        log_hdr = tk.Frame(log_outer, bg=SURFACE)
        log_hdr.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        tk.Label(log_hdr, text="Output Log", font=FONT_SM,
                 fg=SUBTEXT, bg=SURFACE).pack(side="left")
        self._btn(log_hdr, "Clear", self._clear_log, small=True).pack(side="right")

        log_wrap = tk.Frame(log_outer, bg=BORDER)
        log_wrap.grid(row=1, column=0, sticky="nsew")
        log_wrap.columnconfigure(0, weight=1)
        log_wrap.rowconfigure(0, weight=1)

        self.log_box = tk.Text(log_wrap, bg="#111111", fg="#cccccc",
                               font=FONT_MONO, relief="flat", bd=8,
                               wrap="word", state="disabled",
                               insertbackground=ACCENT, selectbackground=ACCENT,
                               cursor="arrow")
        self.log_box.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(log_wrap, command=self.log_box.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.log_box.configure(yscrollcommand=sb.set)
        for tag, color in [("ok",SUCCESS),("err",ACCENT),("warn",WARNING),
                            ("info",ACCENT2),("dim",SUBTEXT)]:
            self.log_box.tag_configure(tag, foreground=color)

        # ── Download progress bar ─────────────────────────────────────────────
        prog_frame = tk.Frame(outer, bg=BG)
        prog_frame.grid(row=6, column=0, sticky="ew", pady=(0, 8))
        prog_frame.columnconfigure(0, weight=1)
        self._progress = ttk.Progressbar(prog_frame,
                                         style="Red.Horizontal.TProgressbar",
                                         mode="determinate", maximum=100, value=0)
        self._progress.grid(row=0, column=0, sticky="ew")
        self._prog_label = tk.Label(prog_frame, text="", font=FONT_SM,
                                    fg=SUBTEXT, bg=BG, width=12, anchor="e")
        self._prog_label.grid(row=0, column=1, padx=(8, 0))
        self._speed_label = tk.Label(prog_frame, text="", font=FONT_SM,
                                     fg=SUBTEXT, bg=BG, width=18, anchor="w")
        self._speed_label.grid(row=0, column=2, padx=(4, 0))

        # ── Bottom buttons ────────────────────────────────────────────────────
        btn_row = tk.Frame(outer, bg=BG)
        btn_row.grid(row=7, column=0, sticky="ew")
        btn_row.columnconfigure(1, weight=1)
        self._dl_btn = self._btn(btn_row, "⬇  Download",
                                 self._start_download, color=ACCENT, large=True)
        self._dl_btn.grid(row=0, column=0)
        self._stop_btn = self._btn(btn_row, "⏹  Stop",
                                   self._stop_download, color="#555", large=True)
        self._stop_btn.grid(row=0, column=2)
        self._stop_btn.configure(state="disabled")

    # ── Widget helpers ─────────────────────────────────────────────────────────
    def _card(self, parent, pady=12):
        return tk.Frame(parent, bg=SURFACE, bd=0,
                        highlightthickness=1, highlightbackground=BORDER,
                        padx=14, pady=pady)

    def _entry(self, parent, textvariable=None, placeholder=""):
        e = tk.Entry(parent, bg=PANEL, fg=TEXT, insertbackground=TEXT,
                     relief="flat", font=FONT_UI, bd=6,
                     highlightthickness=1, highlightbackground=BORDER,
                     textvariable=textvariable)
        if placeholder and textvariable:
            def on_in(_):
                if textvariable.get() == placeholder:
                    textvariable.set(""); e.configure(fg=TEXT)
            def on_out(_):
                if not textvariable.get():
                    textvariable.set(placeholder); e.configure(fg=SUBTEXT)
            if not textvariable.get():
                textvariable.set(placeholder); e.configure(fg=SUBTEXT)
            e.bind("<FocusIn>", on_in)
            e.bind("<FocusOut>", on_out)
        return e

    def _btn(self, parent, text, command, color=SURFACE, large=False, small=False):
        fs = 10 if large else (8 if small else 9)
        px = 16 if large else (6 if small else 10)
        py = 8  if large else (3 if small else 5)
        b = tk.Button(parent, text=text, command=command,
                      bg=color, fg=TEXT, activebackground=self._lighten(color),
                      activeforeground=TEXT, relief="flat", cursor="hand2",
                      font=("Segoe UI", fs, "bold"), padx=px, pady=py, bd=0)
        b.bind("<Enter>", lambda e: b.configure(bg=self._lighten(color)))
        b.bind("<Leave>", lambda e: b.configure(bg=color))
        return b

    def _toggle(self, parent, text, value):
        def cmd():
            self.mode_var.set(value)
            self._mode_changed()
        b = tk.Button(parent, text=text, command=cmd,
                      bg=PANEL, fg=TEXT, activebackground=ACCENT,
                      relief="flat", cursor="hand2",
                      font=("Segoe UI", 9), padx=10, pady=4, bd=0)
        return b

    def _combo(self, parent, values, textvariable):
        style = ttk.Style()
        style.configure("Dark.TCombobox",
                        fieldbackground=PANEL, background=PANEL,
                        foreground=TEXT, arrowcolor=TEXT,
                        selectbackground=PANEL, selectforeground=TEXT)
        return ttk.Combobox(parent, values=values, textvariable=textvariable,
                            style="Dark.TCombobox", state="readonly",
                            font=FONT_UI, width=10)

    def _lighten(self, hex_color):
        try:
            r = min(255, int(hex_color[1:3], 16) + 30)
            g = min(255, int(hex_color[3:5], 16) + 30)
            b = min(255, int(hex_color[5:7], 16) + 30)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color

    # ── Settings ───────────────────────────────────────────────────────────────
    def _open_settings(self):
        def on_save(new_cfg):
            self.cfg = new_cfg
            self._log("✓ Settings saved.", "ok")
        SettingsDialog(self, self.cfg, on_save)

    def _persist_output_dir(self):
        self.cfg["output_dir"] = self.output_dir.get()
        save_config(self.cfg)

    # ── Version check ──────────────────────────────────────────────────────────
    def _check_version(self):
        self._check_btn.configure(state="disabled", text="Checking…")
        threading.Thread(target=self._worker_check_version, daemon=True).start()

    def _worker_check_version(self):
        exe = self._find_ytdlp()
        if not exe:
            self.after(0, lambda: self._set_ytdlp_lbl(
                "Not found  —  use ⬇ Download / Update to install", ACCENT))
        else:
            try:
                r = subprocess.run([exe, "--version"],
                                   capture_output=True, text=True, timeout=8)
                ver = r.stdout.strip() or "unknown"
                self.after(0, lambda: self._set_ytdlp_lbl(f"Installed: {ver}", SUCCESS))
            except Exception as ex:
                self.after(0, lambda: self._set_ytdlp_lbl(f"Error: {ex}", ACCENT))
        self.after(0, lambda: self._check_btn.configure(
            state="normal", text="Check version"))

    def _set_ytdlp_lbl(self, text, color=SUBTEXT):
        self._ytdlp_lbl.configure(text=text, fg=color)

    # ── Download / Update yt-dlp ───────────────────────────────────────────────
    def _run_update(self, silent=False):
        if self.updating:
            return
        self.updating = True
        self._upd_btn.configure(state="disabled")
        self._upd_bar.configure(value=0)
        self._upd_bar_lbl.configure(text="Starting…")
        self._upd_prog_row.grid()
        if not silent:
            self._log("── yt-dlp download / update ──", "info")
        threading.Thread(target=self._worker_update,
                         args=(silent,), daemon=True).start()

    def _worker_update(self, silent):
        api_url    = self.cfg.get("github_api_url", DEFAULT_CFG["github_api_url"])
        asset_name = self.cfg.get("asset_name",     DEFAULT_CFG["asset_name"])
        dest_dir   = self.cfg.get("ytdlp_dir",      SCRIPT_DIR)
        dest_path  = os.path.join(dest_dir, asset_name)
        tmp_path   = dest_path + ".tmp"

        def ui(fn): self.after(0, fn)

        try:
            # 1. Fetch release metadata from GitHub API
            ui(lambda: self._upd_bar_lbl.configure(text="Fetching release info…"))
            req = urllib.request.Request(
                api_url,
                headers={"User-Agent": "yt-dlp-gui/1.0",
                         "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                release = json.loads(resp.read().decode())

            tag    = release.get("tag_name", "?")
            assets = release.get("assets", [])
            match  = [a for a in assets if a["name"] == asset_name]

            if not match:
                names = ", ".join(a["name"] for a in assets[:10])
                ui(lambda: self._log(
                    f"✗ Asset '{asset_name}' not found in release {tag}.\n"
                    f"  Available: {names}\n"
                    f"  Tip: update 'Executable asset filename' in Settings ⚙", "err"))
                ui(lambda: self._set_ytdlp_lbl(
                    f"Asset '{asset_name}' not in release {tag} — check Settings", ACCENT))
                return

            dl_url     = match[0]["browser_download_url"]
            size_bytes = match[0].get("size", 0)

            if not silent:
                ui(lambda: self._log(f"  Release : {tag}", "dim"))
                ui(lambda: self._log(
                    f"  Asset   : {asset_name}  "
                    f"({size_bytes/1024/1024:.1f} MB)", "dim"))
                ui(lambda: self._log(f"  URL     : {dl_url}", "dim"))

            # 2. Check if already up to date
            if os.path.isfile(dest_path):
                try:
                    r = subprocess.run([dest_path, "--version"],
                                       capture_output=True, text=True, timeout=8)
                    installed = r.stdout.strip()
                    if installed == tag:
                        ui(lambda: self._log(
                            f"✓ Already up to date ({tag}).", "ok"))
                        ui(lambda: self._set_ytdlp_lbl(
                            f"Up to date: {tag}", SUCCESS))
                        return
                    if not silent:
                        ui(lambda: self._log(
                            f"  Updating {installed}  →  {tag}", "warn"))
                except Exception:
                    pass

            # 3. Stream download with real progress
            ui(lambda: self._upd_bar_lbl.configure(text="Connecting…"))
            os.makedirs(dest_dir, exist_ok=True)

            dl_req = urllib.request.Request(
                dl_url, headers={"User-Agent": "yt-dlp-gui/1.0"})
            with urllib.request.urlopen(dl_req, timeout=60) as resp2:
                total     = int(resp2.headers.get("Content-Length", 0) or 0)
                received  = 0
                chunk_sz  = 65536
                with open(tmp_path, "wb") as f:
                    while True:
                        chunk = resp2.read(chunk_sz)
                        if not chunk:
                            break
                        f.write(chunk)
                        received += len(chunk)
                        if total:
                            pct  = received * 100 / total
                            mb_d = received / 1024 / 1024
                            mb_t = total    / 1024 / 1024
                            self.after(0, lambda p=pct, d=mb_d, t=mb_t: (
                                self._upd_bar.configure(value=p),
                                self._upd_bar_lbl.configure(
                                    text=f"{p:.0f}%  {d:.1f} / {t:.1f} MB")))
                        else:
                            mb_d = received / 1024 / 1024
                            self.after(0, lambda d=mb_d:
                                       self._upd_bar_lbl.configure(
                                           text=f"{d:.1f} MB downloaded"))

            # 4. Atomically replace old binary
            shutil.move(tmp_path, dest_path)
            if sys.platform != "win32":
                os.chmod(dest_path, 0o755)

            ui(lambda: self._upd_bar.configure(value=100))
            ui(lambda: self._log(
                f"✓ yt-dlp {tag} installed  →  {dest_path}", "ok"))
            ui(lambda: self._set_ytdlp_lbl(f"Installed: {tag}", SUCCESS))

        except urllib.error.URLError as ex:
            ui(lambda: self._log(f"✗ Network error: {ex}", "err"))
            ui(lambda: self._set_ytdlp_lbl("Network error — see log", ACCENT))
        except Exception as ex:
            ui(lambda: self._log(f"✗ Update failed: {ex}", "err"))
            ui(lambda: self._set_ytdlp_lbl("Update failed — see log", ACCENT))
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            self.after(0, self._update_done)

    def _update_done(self):
        self.updating = False
        self._upd_prog_row.grid_remove()
        self._upd_btn.configure(state="normal")

    # ── Mode toggle ────────────────────────────────────────────────────────────
    def _mode_changed(self):
        if self.mode_var.get() == "video":
            self._vid_btn.configure(bg=ACCENT)
            self._aud_btn.configure(bg=PANEL)
            self._res_combo.configure(state="readonly")
            self._fmt_combo.grid()
            self._fmt_combo_audio.grid_remove()
        else:
            self._aud_btn.configure(bg=ACCENT)
            self._vid_btn.configure(bg=PANEL)
            self._res_combo.configure(state="disabled")
            self._fmt_combo.grid_remove()
            self._fmt_combo_audio.grid()

    # ── Browse / log ──────────────────────────────────────────────────────────
    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.output_dir.get())
        if d:
            self.output_dir.set(d)

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _log(self, text, tag=""):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n", tag)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_status(self, color):
        self._status_dot.configure(fg=color)

    # ── Fetch video info ───────────────────────────────────────────────────────
    def _fetch_info(self):
        url = self.url_var.get().strip()
        placeholder = "https://www.youtube.com/watch?v=…"
        if not url or url == placeholder:
            messagebox.showwarning("No URL", "Please enter a video URL first.")
            return
        if self.fetching:
            return
        self.fetching = True
        self._fetch_btn.configure(state="disabled", text="Fetching…")
        self._log("── Fetching video info… ──", "info")
        threading.Thread(target=self._run_fetch, args=(url,), daemon=True).start()

    def _run_fetch(self, url):
        exe = self._find_ytdlp()
        if not exe:
            self.after(0, lambda: self._log(
                "✗ yt-dlp not found. Use ⬇ Download / Update to install it.", "err"))
            self.after(0, self._fetch_done)
            return
        try:
            result = subprocess.run(
                [exe, "--flat-playlist", "-J", url],
                capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                title    = data.get("title", "Unknown")
                uploader = data.get("uploader", "Unknown")
                duration = data.get("duration_string", "?")
                formats  = data.get("formats", [])
                resolutions = sorted(set(
                    f"{f.get('height',0)}p" for f in formats if f.get("height")
                ), key=lambda x: int(x[:-1]), reverse=True)
                self.after(0, lambda: self._log(f"✓ Title:    {title}", "ok"))
                self.after(0, lambda: self._log(f"  Uploader: {uploader}", "dim"))
                self.after(0, lambda: self._log(f"  Duration: {duration}", "dim"))
                if resolutions:
                    self.after(0, lambda: self._log(
                        f"  Resolutions: {', '.join(resolutions)}", "dim"))
                    self.after(0, lambda: self._res_combo.configure(
                        values=["best"] + resolutions))
            else:
                err = result.stderr[:300]
                self.after(0, lambda: self._log(f"✗ Error:\n{err}", "err"))
        except Exception as ex:
            self.after(0, lambda: self._log(f"✗ {ex}", "err"))
        self.after(0, self._fetch_done)

    def _fetch_done(self):
        self.fetching = False
        self._fetch_btn.configure(state="normal", text="Fetch Info")

    # ── Find yt-dlp executable ─────────────────────────────────────────────────
    def _find_ytdlp(self):
        asset     = self.cfg.get("asset_name", DEFAULT_CFG["asset_name"])
        ytdlp_dir = self.cfg.get("ytdlp_dir",  SCRIPT_DIR)
        # 1. Configured directory
        p = os.path.join(ytdlp_dir, asset)
        if os.path.isfile(p):
            return p
        # 2. Next to this script
        p = os.path.join(SCRIPT_DIR, asset)
        if os.path.isfile(p):
            return p
        # 3. System PATH
        for name in (asset, "yt-dlp.exe", "yt-dlp"):
            try:
                subprocess.run([name, "--version"], capture_output=True, timeout=5)
                return name
            except Exception:
                pass
        return None

    # ── Build yt-dlp download command ──────────────────────────────────────────
    def _build_command(self, exe, url):
        mode = self.mode_var.get()
        out  = os.path.join(self.output_dir.get(), "%(title)s.%(ext)s")
        cmd  = [exe, "--newline", "-o", out]
        if mode == "audio":
            fmt = self.audio_fmt.get()
            cmd += ["-x", "--audio-format", fmt, "--audio-quality", "0"]
        else:
            res = self.res_var.get()
            fmt = self.format_var.get()
            if res == "best":
                f_sel = (f"bestvideo[ext={fmt}]+bestaudio[ext=m4a]"
                         f"/bestvideo+bestaudio/best")
            else:
                h = res.replace("p", "")
                f_sel = (f"bestvideo[height<={h}][ext={fmt}]+bestaudio[ext=m4a]/"
                         f"bestvideo[height<={h}]+bestaudio/"
                         f"best[height<={h}]/best")
            cmd += ["-f", f_sel, "--merge-output-format", fmt]
        cmd.append(url)
        return cmd

    # ── Video download ─────────────────────────────────────────────────────────
    def _start_download(self):
        placeholder = "https://www.youtube.com/watch?v=…"
        url = self.url_var.get().strip()
        if not url or url == placeholder:
            messagebox.showwarning("No URL", "Please enter a video URL.")
            return
        if self.proc is not None:
            messagebox.showinfo("Busy", "A download is already running.")
            return
        exe = self._find_ytdlp()
        if not exe:
            messagebox.showerror("yt-dlp not found",
                "yt-dlp was not found.\n\n"
                "Use the  ⬇ Download / Update  button to install it.")
            return
        cmd = self._build_command(exe, url)
        self._log("── Starting download ──", "info")
        self._log("$ " + " ".join(cmd), "dim")
        self._dl_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._progress.configure(value=0)
        self._prog_label.configure(text="0%", fg=SUBTEXT)
        self._speed_label.configure(text="")
        self._set_status(WARNING)
        threading.Thread(target=self._run_download, args=(cmd,), daemon=True).start()

    def _run_download(self, cmd):
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            for line in self.proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                tag = self._classify_line(line)
                self.after(0, lambda l=line, t=tag: self._log(l, t))
                if "[download]" in line and "%" in line:
                    pct, speed, eta = self._parse_progress(line)
                    if pct is not None:
                        self.after(0, lambda p=pct, s=speed, e=eta:
                                   self._update_progress(p, s, e))
            self.proc.wait()
            rc = self.proc.returncode
            if rc == 0:
                self.after(0, lambda: self._progress.configure(value=100))
                self.after(0, lambda: self._prog_label.configure(text="100%", fg=SUCCESS))
                self.after(0, lambda: self._speed_label.configure(text="Done ✓", fg=SUCCESS))
                self.after(0, lambda: self._log("✓ Download complete!", "ok"))
                self.after(0, lambda: self._set_status(SUCCESS))
            elif rc == -1:
                self.after(0, lambda: self._prog_label.configure(text="Stopped", fg=WARNING))
                self.after(0, lambda: self._speed_label.configure(text=""))
                self.after(0, lambda: self._log("⏹ Stopped by user.", "warn"))
                self.after(0, lambda: self._set_status(SUBTEXT))
            else:
                self.after(0, lambda: self._prog_label.configure(text="Error", fg=ACCENT))
                self.after(0, lambda: self._speed_label.configure(text=""))
                self.after(0, lambda: self._log(f"✗ Exit code {rc}", "err"))
                self.after(0, lambda: self._set_status(ACCENT))
        except Exception as ex:
            self.after(0, lambda: self._log(f"✗ Exception: {ex}", "err"))
            self.after(0, lambda: self._set_status(ACCENT))
        finally:
            self.proc = None
            self.after(0, self._download_done)

    def _parse_progress(self, line):
        pct = speed = eta = None
        m = re.search(r'(\d+(?:\.\d+)?)%', line)
        if m:
            pct = float(m.group(1))
        m = re.search(r'at\s+([\d.]+\s*\S+/s)', line)
        if m:
            speed = m.group(1).strip()
        m = re.search(r'ETA\s+(\S+)', line)
        if m:
            eta = m.group(1).strip()
        return pct, speed, eta

    def _update_progress(self, pct, speed, eta):
        self._progress.configure(value=pct)
        color = ACCENT if pct < 50 else (WARNING if pct < 90 else SUCCESS)
        self._prog_label.configure(text=f"{pct:.1f}%", fg=color)
        parts = []
        if speed:
            parts.append(speed)
        if eta and eta != "Unknown":
            parts.append(f"ETA {eta}")
        self._speed_label.configure(text="  ".join(parts), fg=SUBTEXT)

    def _classify_line(self, line):
        l = line.lower()
        if "error" in l or "failed" in l:      return "err"
        if "warning" in l:                      return "warn"
        if "[download]" in l and "%" in l:      return "ok"
        if "[ffmpeg]" in l or "[merger]" in l:  return "info"
        return ""

    def _download_done(self):
        self._dl_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")

    def _stop_download(self):
        if self.proc:
            self.proc.terminate()
            self._log("Stopping…", "warn")


if __name__ == "__main__":
    app = YTDownloader()
    app.mainloop()