"""Main UI module."""

import logging
import queue
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from src import __app_name__, __version__
from src.core.app import validate_paths
from src.core.logger import LOGGER_LEVEL_STYLES, LOGGER_MESSAGE_FORMAT, get_logger, resolve_log_file

logger = get_logger(__name__)

MIN_WINDOW_WIDTH = 560
MIN_WINDOW_HEIGHT = 620


class _QueueHandler(logging.Handler):
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        self.log_queue.put((self.format(record), record.levelno))


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{__app_name__} v{__version__}")
        self.root.resizable(True, True)
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        self._log_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()

        self._build_ui()
        self._poll_log_queue()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Row 0 – Type + Action
        top = ttk.Frame(main)
        top.pack(fill=tk.X, pady=(0, 6))

        type_frame = ttk.LabelFrame(top, text="Type", padding=6)
        type_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        self._type = tk.StringVar(value="symbol")
        ttk.Radiobutton(type_frame, text="Symbol", variable=self._type, value="symbol").pack(side=tk.LEFT, padx=4)
        ttk.Radiobutton(type_frame, text="Footprint", variable=self._type, value="footprint").pack(side=tk.LEFT, padx=4)

        action_frame = ttk.LabelFrame(top, text="Action", padding=6)
        action_frame.pack(side=tk.LEFT, fill=tk.Y)
        self._action = tk.StringVar(value="export")
        ttk.Radiobutton(
            action_frame, text="Export", variable=self._action, value="export", command=self._on_action_change
        ).pack(side=tk.LEFT, padx=4)
        ttk.Radiobutton(
            action_frame, text="Import", variable=self._action, value="import", command=self._on_action_change
        ).pack(side=tk.LEFT, padx=4)

        # Row 1 – KiCad source
        kicad_frame = ttk.LabelFrame(main, text="KiCad Source", padding=6)
        kicad_frame.pack(fill=tk.X, pady=(0, 6))

        mode_row = ttk.Frame(kicad_frame)
        mode_row.pack(fill=tk.X)
        self._mode = tk.StringVar(value="directory")
        ttk.Radiobutton(mode_row, text="Directory", variable=self._mode, value="directory").pack(side=tk.LEFT)
        ttk.Radiobutton(mode_row, text="Single File", variable=self._mode, value="file").pack(side=tk.LEFT, padx=(8, 0))

        kicad_row = ttk.Frame(kicad_frame)
        kicad_row.pack(fill=tk.X, pady=(4, 0))
        self._kicad_path = tk.StringVar()
        ttk.Entry(kicad_row, textvariable=self._kicad_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Button(kicad_row, text="Browse…", command=self._browse_kicad).pack(side=tk.LEFT)

        # Row 2 – CSV file
        csv_frame = ttk.LabelFrame(main, text="CSV File", padding=6)
        csv_frame.pack(fill=tk.X, pady=(0, 6))

        csv_row = ttk.Frame(csv_frame)
        csv_row.pack(fill=tk.X)
        self._csv_path = tk.StringVar()
        ttk.Entry(csv_row, textvariable=self._csv_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self._csv_browse_btn = ttk.Button(csv_row, text="Browse…", command=self._browse_csv)
        self._csv_browse_btn.pack(side=tk.LEFT)

        # Row 3 – Logging options
        log_frame = ttk.LabelFrame(main, text="Logging", padding=6)
        log_frame.pack(fill=tk.X, pady=(0, 6))

        log_row = ttk.Frame(log_frame)
        log_row.pack(fill=tk.X)
        ttk.Label(log_row, text="Level:").pack(side=tk.LEFT)
        self._log_level = tk.StringVar(value="INFO")
        ttk.Combobox(
            log_row,
            textvariable=self._log_level,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            state="readonly",
            width=9,
        ).pack(side=tk.LEFT, padx=(4, 16))
        self._log_to_file = tk.BooleanVar(value=False)
        ttk.Checkbutton(log_row, text="Log to file", variable=self._log_to_file).pack(side=tk.LEFT, padx=(16, 0))

        # Row 4 – Start/Stop button
        run_row = ttk.Frame(main)
        run_row.pack(fill=tk.X, pady=(0, 4))
        self._run_btn = ttk.Button(run_row, text="Start", command=self._toggle)
        self._run_btn.pack(side=tk.RIGHT)

        # Progress bar anchored to bottom first, so it's never squeezed out
        self._progress = ttk.Progressbar(main, mode="indeterminate")
        self._progress.pack(side=tk.BOTTOM, fill=tk.X, pady=(4, 0))

        # Output console fills remaining space
        console_frame = ttk.LabelFrame(main, text="Output", padding=4)
        console_frame.pack(fill=tk.BOTH, expand=True)

        self._console = tk.Text(
            console_frame,
            state=tk.DISABLED,
            wrap=tk.WORD,
            bg="#1e1e1e",
            fg="#d4d4d4",
            font=("Monospace", 9),
            relief=tk.FLAT,
            cursor="arrow",
        )
        scrollbar = ttk.Scrollbar(console_frame, command=self._console.yview)
        self._console.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._console.pack(fill=tk.BOTH, expand=True)

        for _tag, _colour, _ in LOGGER_LEVEL_STYLES.values():
            self._console.tag_configure(_tag, foreground=_colour)

    def _on_action_change(self) -> None:
        pass

    def _browse_kicad(self) -> None:
        is_footprint = self._type.get() == "footprint"
        if self._mode.get() == "directory":
            title = "Select footprint library directory (*.pretty)" if is_footprint else "Select KiCad symbol directory"
            path = filedialog.askdirectory(title=title)
            if path and is_footprint and not path.endswith(".pretty"):
                self._console_write("[WARNING] Selected directory does not end in .pretty", logging.WARNING)
        else:
            sym_types = [("KiCad symbol files", "*.kicad_sym"), ("All files", "*.*")]
            fp_types = [("KiCad footprint files", "*.kicad_mod"), ("All files", "*.*")]
            filetypes = sym_types if not is_footprint else fp_types
            path = filedialog.askopenfilename(title="Select KiCad file", filetypes=filetypes)
        if path:
            self._kicad_path.set(path)

    def _browse_csv(self) -> None:
        if self._action.get() == "import":
            path = filedialog.askopenfilename(
                title="Select CSV file",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            )
        else:
            path = filedialog.asksaveasfilename(
                title="Save CSV file",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            )
        if path:
            self._csv_path.set(path)

    def _console_write(self, text: str, levelno: int = logging.INFO) -> None:
        tag, _, __ = LOGGER_LEVEL_STYLES.get(levelno, ("info", "", ""))
        self._console.configure(state=tk.NORMAL)
        self._console.insert(tk.END, text + "\n", tag)
        self._console.see(tk.END)
        self._console.configure(state=tk.DISABLED)

    def _status(self, text: str) -> None:
        self._log_queue.put((text, logging.INFO))

    def _poll_log_queue(self) -> None:
        try:
            while True:
                text, levelno = self._log_queue.get_nowait()
                self._console_write(text, levelno)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log_queue)

    def _toggle(self) -> None:
        self._start()

    def _start(self) -> None:
        kicad_path = self._kicad_path.get().strip()
        csv_path = self._csv_path.get().strip()

        self._console.configure(state=tk.NORMAL)
        self._console.delete("1.0", tk.END)
        self._console.configure(state=tk.DISABLED)

        try:
            validate_paths(self._action.get(), kicad_path, csv_path)
        except ValueError as e:
            self._console_write(f"[ERROR  ] {e}", logging.ERROR)
            return

        self._stop_event.clear()
        self._run_btn.configure(text="Stop", command=self._stop)
        self._progress.start(10)

        level = getattr(logging, self._log_level.get(), logging.INFO)

        formatter = logging.Formatter(LOGGER_MESSAGE_FORMAT)
        queue_handler = _QueueHandler(self._log_queue)
        queue_handler.setFormatter(formatter)
        handlers: list[logging.Handler] = [queue_handler]
        if self._log_to_file.get():
            file_handler = logging.FileHandler(resolve_log_file(), mode="w")
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        logging.basicConfig(level=level, handlers=handlers, force=True)

        args_type = self._type.get()
        args_action = self._action.get()
        stop = self._stop_event
        debug = level == logging.DEBUG

        logger.debug(f"{__app_name__} v{__version__}")
        logger.debug("Running in CLI mode")
        logger.debug(f"Action: {args_action}")
        logger.debug(f"Type: {args_type}")
        logger.debug(f"KiCad path: {kicad_path}")
        logger.debug(f"CSV path: {csv_path}")

        def _worker() -> None:
            try:
                if args_type == "symbol":
                    from src.core.symbol import Symbol as Comp
                else:
                    from src.core.footprint import Footprint as Comp

                if stop.is_set():
                    self._status("Stopped.")
                    return

                if args_action == "export":
                    comps = Comp.load(kicad_path)
                    if stop.is_set():
                        self._status("Stopped.")
                        return
                    if not comps:
                        logger.error(f"No {args_type}s found.")
                    else:
                        if debug:
                            logger.debug(Comp.format_debug_output(comps))
                        success = Comp.export(comps, csv_path)
                        issues = Comp.format_issues_summary(comps)
                        if issues:
                            logger.warning(issues)
                        self._status("Done.") if success else logger.error("Export failed.")
                else:
                    success = Comp.import_from_csv(csv_path, kicad_path, debug=debug)
                    self._status("Done.") if success else logger.error("Import failed.")
            except Exception as exc:
                logger.error(str(exc))
            finally:
                self.root.after(0, self._on_done)

        threading.Thread(target=_worker, daemon=True).start()
        self._console_write("Processing...")

    def _stop(self) -> None:
        self._stop_event.set()
        self._run_btn.configure(state=tk.DISABLED)
        self._console_write("Stopping...")

    def _on_done(self) -> None:
        self._progress.stop()
        self._run_btn.configure(text="Start", command=self._toggle, state=tk.NORMAL)

    def run(self) -> None:
        self.root.mainloop()


def launch_ui() -> None:
    """Launch the UI application."""
    root = tk.Tk()
    MainWindow(root).run()
