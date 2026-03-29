"""Main entry point"""

import argparse
import os
from pathlib import Path
import sys

from src import __app_name__, __version__
from src.core.logger import get_logger, setup_logging

logger = get_logger(__name__)


def validate_paths(action: str, kicad_path: str, csv_path: str) -> None:
    """Validate all source and target paths before processing begins.

    For export:
        - kicad_path must exist and be readable.
        - csv_path must not be an existing directory; its parent must be writable.
    For import:
        - csv_path must exist as a readable file.
        - kicad_path must exist; its directory must be writable.

    Args:
        action: 'export' or 'import'.
        kicad_path: Path to the KiCad source file or directory.
        csv_path: Path to the CSV file.

    Raises:
        ValueError: with a descriptive message when validation fails.
    """
    kp = Path(kicad_path)
    cp = Path(csv_path)
    parent = cp.parent if cp.parent != Path("") else Path(".")

    if action == "export":
        checks = [
            (not kp.exists(), f"KiCad path '{kicad_path}' does not exist"),
            (not os.access(kp, os.R_OK), f"KiCad path '{kicad_path}' is not readable"),
            (cp.is_dir(), f"CSV path '{csv_path}' is a directory, not a file"),
            (not parent.exists(), f"CSV output directory '{parent}' does not exist"),
            (not os.access(parent, os.W_OK), f"CSV output directory '{parent}' is not writable"),
        ]
    else:
        kp_dir = kp if kp.is_dir() else kp.parent
        checks = [
            (not cp.exists(), f"CSV file '{csv_path}' does not exist"),
            (not cp.is_file(), f"CSV path '{csv_path}' is not a file"),
            (not os.access(cp, os.R_OK), f"CSV file '{csv_path}' is not readable"),
            (not kp.exists(), f"KiCad path '{kicad_path}' does not exist"),
            (not os.access(kp_dir, os.W_OK), f"KiCad path '{kicad_path}' is not writable"),
        ]

    for failed, message in checks:
        if failed:
            raise ValueError(message)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"{__app_name__} v{__version__} - Convert KiCad symbol and footprint libraries to/from CSV format"
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit",
    )
    parser.add_argument("-d", "--debug", action="store_true", help="Display debug output")
    parser.add_argument("-g", "--gui", action="store_true", help="Launch the graphical user interface")
    parser.add_argument(
        "-l",
        "--enable-logging",
        action="store_true",
        help="Enable logging to file 'kicad_csv-<timestamp>.log' in the current directory",
    )

    # CLI-only arguments (ignored in GUI mode)
    parser.add_argument(
        "-a",
        "--action",
        choices=["import", "export"],
        help="Action to be used for processing (import|export) - required for CLI mode",
    )
    parser.add_argument(
        "-t",
        "--type",
        choices=["symbol", "footprint"],
        help="Type of library to process (symbol|footprint) - required for CLI mode",
    )
    parser.add_argument(
        "kicad_dirfile",
        nargs="?",
        help="Path to directory or single file (.kicad_sym|.pretty) - required for CLI mode",
    )
    parser.add_argument(
        "csv_dirfile",
        nargs="?",
        help="Path to directory or single file (.csv) - required for CLI mode",
    )

    args = parser.parse_args()

    # If GUI mode, we're done - ignore all other args
    if args.gui:
        return args

    # For CLI mode, validate required arguments
    missing_args = []
    if not args.action:
        missing_args.append("-a/--action")
    if not args.type:
        missing_args.append("-t/--type")
    if not args.kicad_dirfile:
        missing_args.append("kicad_dirfile")
    if not args.csv_dirfile:
        missing_args.append("csv_dirfile")

    if missing_args:
        parser.error(f"the following arguments are required for CLI mode: {', '.join(missing_args)}")

    return args


def run_cli(args: argparse.Namespace) -> None:
    logger.debug(f"{__app_name__} v{__version__}")
    logger.debug("Running in CLI mode")
    logger.debug(f"Action: {args.action}")
    logger.debug(f"Type: {args.type}")
    logger.debug(f"KiCad path: {args.kicad_dirfile}")
    logger.debug(f"CSV path: {args.csv_dirfile}")

    try:
        validate_paths(args.action, args.kicad_dirfile, args.csv_dirfile)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    if args.type == "symbol":
        from src.core.symbol import Symbol as Comp
    elif args.type == "footprint":
        from src.core.footprint import Footprint as Comp

    if args.action == "export":
        print("Processing...")

        comps = Comp.load(args.kicad_dirfile)
        if not comps:
            logger.error(f"No {args.type}s found")
            sys.exit(1)

        if args.debug:
            logger.debug(Comp.format_debug_output(comps))

        success = Comp.export(comps, args.csv_dirfile)

        issues_summary = Comp.format_issues_summary(comps)
        if issues_summary:
            logger.info(issues_summary)

        print("Done." if success else "Export failed.")

        sys.exit(0 if success else 1)

    else:
        logger.info(f"Importing {args.type}s from CSV...")

        if not Comp.import_from_csv(args.csv_dirfile, args.kicad_dirfile, debug=args.debug):
            logger.error("Import failed")
            sys.exit(1)

        logger.info("Import completed successfully")
        sys.exit(0)


def run_gui() -> None:
    logger.debug("Running in GUI mode")

    try:
        from src.ui import launch_ui

        launch_ui()
    except ImportError as e:
        logger.error(f"Failed to import UI module: {e}")
        logger.error("Make sure tkinter is installed (python3-tk on Linux)")
        sys.exit(1)


def main() -> None:
    import logging

    args = parse_arguments()

    try:
        setup_logging(
            level=logging.DEBUG if args.debug else logging.INFO,
            log_to_file=getattr(args, "enable_logging", False),
        )
    except ValueError as e:
        print(f"[ERROR  ] {e}", file=sys.stderr)
        sys.exit(1)

    run_gui() if args.gui else run_cli(args)


if __name__ == "__main__":
    main()
