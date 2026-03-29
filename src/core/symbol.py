"""Symbol class for KiCad symbol library handling.

Represents a KiCad symbol with its properties and provides methods
for parsing and exporting symbols.
"""

from pathlib import Path
import re
from typing import Dict, List

from src.core.component import Component
from src.core.logger import get_logger
from src.core.sparser import SParser

logger = get_logger(__name__)


class Symbol(Component):
    # Standard properties - determines export column order
    PROPERTIES = [
        "Lib_PATH+FILENAME",
        "COMPONENT",
        "Description",
        "ki_keywords",
        "Reference",
        "Value",
        "Footprint",
        "Datasheet",
        "Technology",
        "MFG",
        "MPN",
        "Device_Marking",
        "OC_LCSC",
        "OC_MOUSER",
        "OC_RS",
        "OC_DISTRELEC",
        "OC_TME",
        "OC_FARNELL",
        "OC_DIGIKEY",
        "OC_SOS",
        "Z-SYSCODE",
        "Assembly_Note",
        "Comment",
        "ki_fp_filters",
    ]

    def to_dict(self) -> Dict[str, str]:
        """Convert symbol to dictionary for CSV export.

        Returns:
            Dictionary with all symbol data
        """
        data = {
            "Lib_PATH+FILENAME": self.relpath(self.file_path),
            "COMPONENT": self.name,
        }

        # Add all properties, mapping ki_description -> Description
        for key, value in self.properties.items():
            if key != "ki_description":
                data[key] = value

        # Description maps to ki_description (old format) or Description (new format)
        data["Description"] = self.properties.get("ki_description") or self.properties.get("Description", "")

        return data

    @classmethod
    def parse_file(cls, file_path: str) -> List["Symbol"]:
        """Parse a .kicad_sym file and extract all symbols.

        Args:
            file_path: Path to .kicad_sym file

        Returns:
            List of Symbol objects
        """
        logger.debug(f"Parsing symbol file: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8", newline="") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return []

        # Extract symbols using sparser
        symbol_pattern = r'\(symbol\s+"([^"]+)"'
        expressions = SParser.extract_nested_expressions(content, symbol_pattern)

        if not expressions:
            logger.warning(f"No symbols found in {file_path}")
            return []

        symbols = []
        skipped_by_parent = {}  # Track skipped sub-symbols by parent name

        indentation = SParser.detect_indentation(content)
        logger.debug(f"Detected indentation: {repr(indentation)}")

        for name, expr_content, _, _ in expressions:
            # Check if this is a sub-symbol (graphical unit)
            if re.search(r"_\d+_\d+$", name):
                # Extract parent name
                parent_name = re.sub(r"_\d+_\d+$", "", name)
                if parent_name not in skipped_by_parent:
                    skipped_by_parent[parent_name] = []
                skipped_by_parent[parent_name].append(name)
                continue

            # Create Symbol and extract properties
            symbol = cls(name, file_path)
            symbol.indentation = indentation
            symbol.properties = SParser.extract_properties(expr_content)
            symbols.append(symbol)

        # Add skipped sub-symbols as issues to parent symbols
        for symbol in symbols:
            if symbol.name in skipped_by_parent:
                skipped = skipped_by_parent[symbol.name]
                symbol.add_issue(f"Skipped {len(skipped)} sub-symbols: {', '.join(skipped)}")

        logger.info(f"Found {len(symbols)} symbols in {Path(file_path).name}")

        return symbols

    @classmethod
    def parse_directory(cls, dir_path: str) -> List["Symbol"]:
        """Parse all .kicad_sym files in a directory.

        Args:
            dir_path: Path to directory

        Returns:
            List of Symbol objects from all files
        """
        directory = Path(dir_path)

        if not directory.is_dir():
            logger.error(f"Not a directory: {dir_path}")
            return []

        all_symbols = []
        symbol_files = list(directory.glob("*.kicad_sym"))

        if not symbol_files:
            logger.warning(f"No .kicad_sym files found in {dir_path}")
            return []

        logger.info(f"Found {len(symbol_files)} symbol files in {dir_path}")

        for file_path in symbol_files:
            symbols = cls.parse_file(str(file_path))
            all_symbols.extend(symbols)

        return all_symbols

    @classmethod
    def _get_component_name_from_row(cls, row: Dict[str, str]) -> str:
        return row.get("COMPONENT", "")

    @classmethod
    def _update_property_in_content(cls, content: str, symbol_name: str, prop_name: str, new_value: str) -> str:
        """Update a property value in S-expression content.

        Args:
            content: File content
            symbol_name: Symbol name
            prop_name: Property name
            new_value: New property value

        Returns:
            Updated content
        """

        # Handle special property name mappings
        if prop_name == "Description":
            # Try to update ki_description first, fall back to Description
            updated = cls._replace_property_value(content, symbol_name, "ki_description", new_value)
            if updated != content:
                return updated
            # If ki_description wasn't found, try Description
            return cls._replace_property_value(content, symbol_name, "Description", new_value)
        else:
            return cls._replace_property_value(content, symbol_name, prop_name, new_value)

    @staticmethod
    def _replace_property_value(content: str, symbol_name: str, prop_name: str, new_value: str) -> str:
        """Replace a property value in S-expression content.

        Args:
            content: File content
            symbol_name: Symbol name
            prop_name: Property name
            new_value: New property value

        Returns:
            Updated content
        """

        # Use SParser to find the symbol block properly
        symbol_pattern = rf'\(symbol\s+"({re.escape(symbol_name)})"'
        expressions = SParser.extract_nested_expressions(content, symbol_pattern)

        if not expressions:
            return content

        # Process each matching symbol (should be only one)
        for _, full_symbol_expr, start_pos, end_pos in expressions:
            # Find and replace the property within this symbol's expression
            # The full_symbol_expr includes the full (symbol ...) block
            prop_pattern = rf'(\(property\s+"{re.escape(prop_name)}"\s+)"([^"]*)"'

            def replace_prop(prop_match):
                old_value = prop_match.group(2)
                if old_value != new_value:
                    logger.debug(f"  {prop_name}: '{old_value}' -> '{new_value}'")
                    # Return the updated property
                    return prop_match.group(1) + f'"{new_value}"'
                else:
                    # No change needed
                    return prop_match.group(0)

            # Replace within the full symbol expression
            updated_expr = re.sub(prop_pattern, replace_prop, full_symbol_expr)

            if updated_expr != full_symbol_expr:
                # Replace in the original content
                content = content[:start_pos] + updated_expr + content[end_pos:]
                return content

        return content
