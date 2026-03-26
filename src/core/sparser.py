"""S-expression parser for KiCad files.

Generic parser for KiCad's S-expression format used in both
symbol libraries (.kicad_sym) and footprint libraries (.kicad_mod).
"""

import re
from typing import Optional

from src.core.logger import get_logger

logger = get_logger(__name__)


class SParser:
    @staticmethod
    def detect_indentation(content: str) -> str:
        """Detect indentation style (tabs or spaces).

        Args:
            content: File content

        Returns:
            Indentation string (tab or spaces)
        """
        lines = content.split("\n")
        for line in lines:
            if line and line[0] in (" ", "\t"):
                if line[0] == "\t":
                    return "\t"
                else:
                    spaces = len(line) - len(line.lstrip(" "))
                    if spaces > 0:
                        return " " * spaces
        return "  "  # Default to 2 spaces

    @staticmethod
    def find_matching_paren(content: str, start_pos: int) -> int:
        """Find matching closing parenthesis for an opening parenthesis.

        Args:
            content: File content
            start_pos: Position of opening parenthesis

        Returns:
            Position of matching closing parenthesis, or -1 if not found
        """
        count = 0
        in_string = False

        for i in range(start_pos, len(content)):
            char = content[i]

            if char == '"' and (i == 0 or content[i - 1] != "\\"):
                in_string = not in_string
            elif not in_string:
                if char == "(":
                    count += 1
                elif char == ")":
                    count -= 1
                    if count == 0:
                        return i + 1

        return -1

    @staticmethod
    def extract_nested_expressions(content: str, pattern: str) -> list[tuple[str, str, int, int]]:
        """Extract all matching S-expressions with their positions.

        Args:
            content: File content
            pattern: Regex pattern to match (e.g., r'\\(symbol\\s+"([^"]+)"')

        Returns:
            List of tuples: (matched_name, expression_content, start_pos, end_pos)
        """
        results = []
        matches = re.finditer(pattern, content)

        for match in matches:
            name = match.group(1)
            start_pos = match.start()
            end_pos = SParser.find_matching_paren(content, start_pos)

            if end_pos != -1:
                expression = content[start_pos:end_pos]
                results.append((name, expression, start_pos, end_pos))
            else:
                logger.warning(f"Could not find end of expression for: {name}")

        return results

    @staticmethod
    def extract_properties(content: str) -> dict[str, str]:
        """Extract properties from S-expression content.

        Extracts (property "Name" "Value") pairs.

        Args:
            content: S-expression content

        Returns:
            Dictionary of property names to values
        """
        properties = {}
        property_pattern = r'\(property\s+"([^"]+)"\s+"([^"]*)"'

        for match in re.finditer(property_pattern, content):
            prop_name = match.group(1)
            prop_value = match.group(2)
            properties[prop_name] = prop_value

        return properties

    @staticmethod
    def extract_text_fields(content: str, field_type: str) -> dict[str, str]:
        """Extract text fields from footprint S-expression.

        Extracts (fp_text type "value" ...) or similar patterns.

        Args:
            content: S-expression content
            field_type: Type of field to extract (e.g., "fp_text")

        Returns:
            Dictionary of field types to values
        """
        fields = {}
        # Pattern: (fp_text reference "REF**" ...)
        pattern = rf'\({field_type}\s+(\w+)\s+"([^"]*)"'

        for match in re.finditer(pattern, content):
            field_name = match.group(1)
            field_value = match.group(2)
            fields[field_name] = field_value

        return fields

    @staticmethod
    def extract_simple_field(content: str, field_name: str) -> Optional[str]:
        """Extract a simple field value from S-expression.

        Extracts (field_name "value") patterns.

        Args:
            content: S-expression content
            field_name: Name of field to extract

        Returns:
            Field value or None if not found
        """
        pattern = rf'\({field_name}\s+"([^"]*)"'
        match = re.search(pattern, content)

        if match:
            return match.group(1)

        return None

    @staticmethod
    def extract_unquoted_field(content: str, field_name: str) -> Optional[str]:
        """Extract an unquoted field value from S-expression.

        Extracts (field_name value) patterns where value is a bare word,
        e.g. (attr smd) or (attr through_hole).

        Args:
            content: S-expression content
            field_name: Name of field to extract

        Returns:
            Field value (may be empty string) or None if field absent
        """
        pattern = rf"\({field_name}(?:\s+(\w+))?\s*\)"
        match = re.search(pattern, content)
        if match:
            return match.group(1) or ""
        return None
