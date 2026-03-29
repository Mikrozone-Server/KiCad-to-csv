"""Footprint class for KiCad footprint library handling.

Represents a KiCad footprint with its properties and provides methods
for parsing and exporting footprints.
"""

from pathlib import Path
import re
from typing import Dict, List

from src.core.component import Component
from src.core.logger import get_logger
from src.core.sparser import SParser

logger = get_logger(__name__)


class Footprint(Component):
    # Mapping of property names to KiCad field names and update methods
    # Format: "Property": ("field_name", "method_type")
    PROPERTY_MAP = {
        "Description": ("descr", "simple"),
        "Tags": ("tags", "simple"),
        "Layer": ("layer", "simple"),
        "Attribute": ("attr", "attr"),
        "Reference": ("reference", "fp_text"),
        "Value": ("value", "fp_text"),
    }

    # Standard properties - determines export column order
    PROPERTIES = [
        "Lib_PATH+FILENAME",
        "FOOTPRINT",
    ] + list(PROPERTY_MAP.keys())

    def to_dict(self) -> Dict[str, str]:
        """Convert footprint to dictionary for CSV export.

        Returns:
            Dictionary with all footprint data
        """
        data = {
            "Lib_PATH+FILENAME": self.relpath(self.file_path),
            "FOOTPRINT": self.name,
        }

        # Add all properties
        for key, value in self.properties.items():
            data[key] = value

        return data

    @classmethod
    def parse_file(cls, file_path: str) -> List["Footprint"]:
        """Parse a .kicad_mod file and extract footprint.

        Args:
            file_path: Path to .kicad_mod file

        Returns:
            List with single Footprint object (or empty if error)
        """
        logger.debug(f"Parsing footprint file: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8", newline="") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return []

        # Extract footprint using sparser
        footprint_pattern = r'\(footprint\s+"([^"]+)"'
        expressions = SParser.extract_nested_expressions(content, footprint_pattern)

        if not expressions:
            logger.warning(f"No footprint found in {file_path}")
            return []

        footprints = []
        indentation = SParser.detect_indentation(content)
        logger.debug(f"Detected indentation: {repr(indentation)}")

        for name, expr_content, _, _ in expressions:
            # Create Footprint and extract properties
            footprint = cls(name, file_path)
            footprint.indentation = indentation
            for prop_name, (field_name, method_type) in cls.PROPERTY_MAP.items():
                if method_type == "simple":
                    value = SParser.extract_simple_field(expr_content, field_name)
                    footprint.set_property(prop_name, value)
                elif method_type == "attr":
                    value = SParser.extract_unquoted_field(expr_content, field_name)
                    footprint.set_property(prop_name, value)
                elif method_type == "fp_text":
                    text_fields = SParser.extract_text_fields(expr_content, "fp_text")
                    footprint.set_property(prop_name, text_fields.get(field_name, ""))

            footprints.append(footprint)

        logger.info(f"Found {len(footprints)} footprint(s) in {Path(file_path).name}")
        return footprints

    @classmethod
    def parse_directory(cls, dir_path: str) -> List["Footprint"]:
        """Parse all .kicad_mod files in a directory or .pretty folder.

        Args:
            dir_path: Path to directory

        Returns:
            List of Footprint objects from all files
        """
        directory = Path(dir_path)

        if not directory.is_dir():
            logger.error(f"Not a directory: {dir_path}")
            return []

        all_footprints = []

        # Find all .kicad_mod files (directly in dir or in .pretty subdirs)
        footprint_files = list(directory.glob("*.kicad_mod"))
        footprint_files.extend(directory.glob("*.pretty/*.kicad_mod"))

        if not footprint_files:
            logger.warning(f"No .kicad_mod files found in {dir_path}")
            return []

        logger.info(f"Found {len(footprint_files)} footprint files in {dir_path}")

        for file_path in footprint_files:
            footprints = cls.parse_file(str(file_path))
            all_footprints.extend(footprints)

        return all_footprints

    @classmethod
    def _get_component_name_from_row(cls, row: Dict[str, str]) -> str:
        return row.get("FOOTPRINT", "")

    @classmethod
    def _update_property_in_content(cls, content: str, footprint_name: str, prop_name: str, new_value: str) -> str:
        """Update a property value in footprint S-expression content.

        Args:
            content: File content
            footprint_name: Footprint name
            prop_name: Property name
            new_value: New property value

        Returns:
            Updated content
        """
        # Use SParser to find the footprint block
        footprint_pattern = rf'\(footprint\s+"({re.escape(footprint_name)})"'
        expressions = SParser.extract_nested_expressions(content, footprint_pattern)

        if not expressions:
            return content

        # Process each matching footprint (should be only one)
        for _, full_footprint_expr, start_pos, end_pos in expressions:
            updated_expr = full_footprint_expr

            # Check if this property is in our mapping
            prop_info = cls.PROPERTY_MAP.get(prop_name)
            if prop_info:
                field_name, method_type = prop_info

                if method_type == "simple":
                    updated_expr = cls._replace_simple_field(updated_expr, field_name, new_value)
                elif method_type == "attr":
                    updated_expr = cls._replace_attr_field(updated_expr, new_value)
                elif method_type == "fp_text":
                    updated_expr = cls._replace_fp_text(updated_expr, field_name, new_value)

            if updated_expr != full_footprint_expr:
                # Replace in the original content
                content = content[:start_pos] + updated_expr + content[end_pos:]
                return content

        return content

    @staticmethod
    def _replace_simple_field(content: str, field_name: str, new_value: str) -> str:
        """Replace a simple field like (descr "value") or (tags "value").

        Only replaces the first occurrence (footprint-level field).

        Args:
            content: Footprint content
            field_name: Field name (descr, tags, layer)
            new_value: New value

        Returns:
            Updated content
        """
        pattern = rf'(\({field_name}\s+)"([^"]*)"'

        def replace_field(match):
            old_value = match.group(2)
            if old_value != new_value:
                logger.debug(f"  {field_name}: '{old_value}' -> '{new_value}'")
                return match.group(1) + f'"{new_value}"'
            return match.group(0)

        # Only replace first occurrence (footprint-level field)
        return re.sub(pattern, replace_field, content, count=1)

    @staticmethod
    def _replace_attr_field(content: str, new_value: str) -> str:
        """Replace attr field like (attr smd) - no quotes.

        Args:
            content: Footprint content
            new_value: New attribute value

        Returns:
            Updated content
        """
        pattern = r"(\(attr\s+)(\w+)"

        def replace_attr(match):
            old_value = match.group(2)
            if old_value != new_value:
                logger.debug(f"  attr: '{old_value}' -> '{new_value}'")
                return match.group(1) + new_value
            return match.group(0)

        return re.sub(pattern, replace_attr, content)

    @staticmethod
    def _replace_fp_text(content: str, text_type: str, new_value: str) -> str:
        """Replace fp_text field like (fp_text reference "REF**" ...).

        Args:
            content: Footprint content
            text_type: Type (reference or value)
            new_value: New value

        Returns:
            Updated content
        """
        pattern = rf'(\(fp_text\s+{text_type}\s+)"([^"]*)"'

        def replace_text(match):
            old_value = match.group(2)
            if old_value != new_value:
                logger.debug(f"  fp_text {text_type}: '{old_value}' -> '{new_value}'")
                return match.group(1) + f'"{new_value}"'
            return match.group(0)

        return re.sub(pattern, replace_text, content)
