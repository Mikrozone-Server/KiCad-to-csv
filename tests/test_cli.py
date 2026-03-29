"""CLI integration tests: export and import round-trip for symbols and footprints."""

import csv
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import pytest

REPO = Path(__file__).parent.parent
CLI = [sys.executable, str(REPO / "kicad-from-to-csv.py")]

SYMBOL_FILES = sorted((REPO / "tests/symbols").glob("*.kicad_sym"))
FOOTPRINT_DIRS = sorted((REPO / "tests/footprints").glob("*.pretty"))


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(CLI + list(args), capture_output=True, text=True, cwd=REPO)


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Symbol tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sym_file", SYMBOL_FILES, ids=lambda p: p.stem)
def test_symbol_export(sym_file, tmp_path):
    csv_out = tmp_path / "out.csv"
    result = run_cli("-a", "export", "-t", "symbol", str(sym_file), str(csv_out))
    assert result.returncode == 0, result.stderr
    rows = read_csv(csv_out)
    assert rows, "CSV is empty"
    assert "COMPONENT" in rows[0]
    assert "Description" in rows[0]
    assert "Lib_PATH+FILENAME" in rows[0]


@pytest.mark.parametrize("sym_file", SYMBOL_FILES, ids=lambda p: p.stem)
def test_symbol_roundtrip(sym_file, tmp_path):
    sym_copy = tmp_path / sym_file.name
    shutil.copy(sym_file, sym_copy)

    csv_path = tmp_path / "sym.csv"
    run_cli("-a", "export", "-t", "symbol", str(sym_copy), str(csv_path))

    rows = read_csv(csv_path)
    marker = f"TEST_{uuid.uuid4().hex[:12]}"
    rows[0]["Description"] = marker
    write_csv(csv_path, rows)

    result = run_cli("-a", "import", "-t", "symbol", str(REPO), str(csv_path))
    assert result.returncode == 0, result.stderr
    assert marker in sym_copy.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Footprint tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fp_dir", FOOTPRINT_DIRS, ids=lambda p: p.name)
def test_footprint_export(fp_dir, tmp_path):
    csv_out = tmp_path / "out.csv"
    result = run_cli("-a", "export", "-t", "footprint", str(fp_dir), str(csv_out))
    assert result.returncode == 0, result.stderr
    rows = read_csv(csv_out)
    assert rows, "CSV is empty"
    assert "FOOTPRINT" in rows[0]
    assert "Description" in rows[0]
    assert "Lib_PATH+FILENAME" in rows[0]


@pytest.mark.parametrize("fp_dir", FOOTPRINT_DIRS, ids=lambda p: p.name)
def test_footprint_roundtrip(fp_dir, tmp_path):
    fp_copy = tmp_path / fp_dir.name
    shutil.copytree(fp_dir, fp_copy)

    csv_path = tmp_path / "fp.csv"
    run_cli("-a", "export", "-t", "footprint", str(fp_copy), str(csv_path))

    rows = read_csv(csv_path)
    marker = f"TEST_{uuid.uuid4().hex[:12]}"
    rows[0]["Description"] = marker
    write_csv(csv_path, rows)

    result = run_cli("-a", "import", "-t", "footprint", str(REPO), str(csv_path))
    assert result.returncode == 0, result.stderr
    modified = any(marker in f.read_text(encoding="utf-8") for f in fp_copy.glob("*.kicad_mod"))
    assert modified, f"Marker '{marker}' not found in any .kicad_mod file under {fp_copy}"
