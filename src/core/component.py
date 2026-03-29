"""Component base class for KiCad library handling.

Base class for Symbol and Footprint with common functionality.
"""

from abc import ABC, abstractmethod
import json
import os
from pathlib import Path
from typing import Dict, List

from src.core.logger import get_logger
from src.core.sparser import SParser

logger = get_logger(__name__)


class Component(ABC):
    """Abstract base class for KiCad components (symbols and footprints)."""

    # Subclasses must define PROPERTIES list
    PROPERTIES: List[str] = []

    def __init__(self, name: str, file_path: str = ""):
        self.name = name
        self.file_path = file_path
        self.properties: Dict[str, str] = {}
        self.issues: List[str] = []
        self.indentation: str = "  "  # detected during parse_file

    @staticmethod
    def relpath(path: str) -> str:
        if not path:
            return ""
        try:
            return os.path.relpath(path)
        except ValueError:
            return path

    def add_issue(self, message: str) -> None:
        self.issues.append(message)

    def set_property(self, key: str, value: str) -> None:
        self.properties[key] = value

    def get_property(self, key: str, default: str = "") -> str:
        return self.properties.get(key, default)

    @classmethod
    def format_debug_output(cls, components: List["Component"]) -> str:
        """Format components for debug output.

        Args:
            components: List of Component objects

        Returns:
            Formatted JSON string with issues displayed inline
        """
        if not components:
            return "[]"

        # Group components by file
        by_file: Dict[str, List[Dict]] = {}
        for comp in components:
            if comp.file_path not in by_file:
                by_file[comp.file_path] = []

            comp_data = {"name": comp.name}
            # Add non-empty properties
            comp_data.update({k: v for k, v in comp.properties.items() if v})

            # Add issues if any
            if comp.issues:
                comp_data[">>>ISSUES"] = comp.issues

            by_file[comp.file_path].append(comp_data)

        # Format as nested structure
        output = []
        for file_path, file_comps in by_file.items():
            output.append({file_path: file_comps})

        return json.dumps(output, indent=2, ensure_ascii=False)

    @classmethod
    def format_issues_summary(cls, components: List["Component"]) -> str:
        """Format a summary of components with issues.

        Args:
            components: List of Component objects

        Returns:
            Summary string of components with issues, empty if none
        """
        components_with_issues = [c for c in components if c.issues]

        if not components_with_issues:
            return ""

        lines = ["\nIssues found:"]
        for comp in components_with_issues:
            lines.append(f"  {comp.name}:")
            for issue in comp.issues:
                lines.append(f"    - {issue}")

        return "\n".join(lines)

    @abstractmethod
    def to_dict(self) -> Dict[str, str]:
        pass

    @classmethod
    @abstractmethod
    def parse_file(cls, file_path: str) -> List["Component"]:
        pass

    @classmethod
    @abstractmethod
    def parse_directory(cls, dir_path: str) -> List["Component"]:
        pass

    @classmethod
    def load(cls, input_path: str) -> List["Component"]:
        """Load components from file or directory.

        Args:
            input_path: Path to file or directory

        Returns:
            List of Component objects
        """
        path = Path(input_path)

        if path.is_file():
            return cls.parse_file(str(path))
        elif path.is_dir():
            return cls.parse_directory(str(path))
        else:
            logger.error(f"Path not found: {input_path}")
            return []

    @classmethod
    def export(cls, components: List["Component"], output_path: str) -> bool:
        """Export components to CSV file.

        Args:
            components: List of Component objects
            output_path: Output CSV file path

        Returns:
            True if successful, False otherwise
        """
        from src.core.csv_handler import CSVHandler

        if not components:
            logger.error("No components to export")
            return False

        logger.info(f"Exporting {len(components)} {cls.__name__.lower()}s to {output_path}")

        # Convert components to dictionaries
        rows = [component.to_dict() for component in components]

        # Use CSVHandler to write
        return CSVHandler.write(output_path, rows, cls._get_export_columns(rows))

    @classmethod
    def _get_export_columns(cls, rows: List[Dict[str, str]]) -> List[str]:
        """Get export column order based on PROPERTIES.

        Args:
            rows: List of row dictionaries

        Returns:
            Ordered list of column names
        """
        # Collect all unique keys
        all_keys = set()
        for row in rows:
            all_keys.update(row.keys())

        columns = []

        # Add standard properties that exist in data
        for prop in cls.PROPERTIES:
            if prop in all_keys:
                columns.append(prop)

        # Add any additional properties not in standard list
        for key in sorted(all_keys):
            if key not in cls.PROPERTIES and not key.startswith("_"):
                columns.append(key)

        return columns

    @classmethod
    def import_from_csv(cls, csv_path: str, kicad_dir: str, debug: bool = False) -> bool:
        """Import component data from CSV and update files.

        Args:
            csv_path: Path to CSV file
            kicad_dir: Directory containing files to update

        Returns:
            True if successful, False otherwise
        """
        from src.core.csv_handler import CSVHandler

        logger.info(f"Importing {cls.__name__.lower()}s from {csv_path}")

        # Read CSV
        rows = CSVHandler.read(csv_path)
        if not rows:
            logger.error("No data to import")
            return False

        logger.info(f"Read {len(rows)} rows from CSV")

        # Group updates by file
        updates_by_file: Dict[str, List[Dict[str, str]]] = {}
        for row in rows:
            file_path = row.get("Lib_PATH+FILENAME", "")
            if not file_path:
                logger.warning("Skipping row without file path")
                continue

            # Resolve the file path.
            # When kicad_dir points directly to a file (single-file GUI mode) use it
            # as-is — the user explicitly picked the target, so Lib_PATH+FILENAME is
            # only used to validate the filename, not to build a path.
            p = Path(file_path)
            kd = Path(kicad_dir)
            if kd.is_file():
                resolved = kd.resolve()
                if p.name != resolved.name:
                    component_name = cls._get_component_name_from_row(row)
                    logger.warning(
                        f"Skipping '{component_name}': file name mismatch "
                        f"(CSV has '{p.name}', selected file is '{resolved.name}')"
                    )
                    continue
            elif p.is_absolute():
                resolved = p.resolve()
            else:
                resolved = (kd / p).resolve()
            if not resolved.exists():
                component_name = cls._get_component_name_from_row(row)
                logger.warning(f"Skipping '{component_name}': file not found: {resolved}")
                continue
            file_path = str(resolved)

            if file_path not in updates_by_file:
                updates_by_file[file_path] = []
            updates_by_file[file_path].append(row)

        # Update each file
        written_count = 0
        unchanged_count = 0
        fail_count = 0

        for file_path, file_rows in updates_by_file.items():
            logger.info(f"Updating {len(file_rows)} {cls.__name__.lower()}(s) in {file_path}")
            result = cls._update_file(file_path, file_rows, debug=debug)
            if result is True:
                written_count += 1
            elif result is None:
                unchanged_count += 1
            else:
                fail_count += 1

        parts = [f"{written_count} file(s) written"]
        if unchanged_count:
            parts.append(f"{unchanged_count} unchanged")
        if fail_count:
            parts.append(f"{fail_count} failed")
        logger.info(f"Import completed: {', '.join(parts)}")
        return fail_count == 0

    @classmethod
    def _update_file(cls, file_path: str, updates: List[Dict[str, str]], debug: bool = False) -> bool | None:
        """Update a file with new property values.

        Args:
            file_path: Path to file
            updates: List of row dictionaries with updated values

        Returns:
            True if file was written, None if no changes were needed, False on error.
        """
        try:
            # Read file
            with open(file_path, "r", encoding="utf-8", newline="") as f:
                content = f.read()

            indentation = SParser.detect_indentation(content)
            logger.debug(f"Detected indentation: {repr(indentation)}")
            original_content = content

            # Parse file once for debug diff
            parsed_by_name = {}
            if debug:
                parsed_by_name = {c.name: c for c in cls.parse_file(file_path)}

            # Apply updates for each component
            for row in updates:
                component_name = cls._get_component_name_from_row(row)
                if not component_name:
                    logger.warning("Skipping update without component name")
                    continue

                if debug and component_name in parsed_by_name:
                    current = parsed_by_name[component_name].to_dict()
                    meta = {"Lib_PATH+FILENAME", "COMPONENT", "FOOTPRINT"}
                    changes = {
                        k: {"from": current.get(k, ""), "to": v}
                        for k, v in row.items()
                        if k not in meta and current.get(k, "") != v
                    }
                    if changes:
                        logger.debug(json.dumps({component_name: changes}, indent=2, ensure_ascii=False))

                logger.debug(f"Updating {cls.__name__.lower()}: {component_name}")
                content_before = content

                # Update each property
                for key, value in row.items():
                    # Skip metadata columns
                    if key in ["Lib_PATH+FILENAME", "COMPONENT", "FOOTPRINT"]:
                        continue

                    # Update the property in content
                    content = cls._update_property_in_content(content, component_name, key, value)

                if content == content_before:
                    logger.debug(f"  {cls.__name__} '{component_name}' not found in file")

            # Write back if changed
            if content != original_content:
                with open(file_path, "w", encoding="utf-8", newline="") as f:
                    f.write(content)
                logger.info(f"Updated {file_path}")
                return True
            else:
                logger.debug(f"No changes needed for {file_path}")
                return None

        except Exception as e:
            logger.error(f"Failed to update {file_path}: {e}")
            return False

    @classmethod
    @abstractmethod
    def _get_component_name_from_row(cls, row: Dict[str, str]) -> str:
        pass

    @classmethod
    @abstractmethod
    def _update_property_in_content(cls, content: str, component_name: str, prop_name: str, new_value: str) -> str:
        pass
