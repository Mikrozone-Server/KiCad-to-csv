"""CSV Handler for reading and writing CSV files."""

import csv
from typing import Dict, List

from src.core.logger import get_logger

logger = get_logger(__name__)


class CSVHandler:
    @staticmethod
    def read(file_path: str) -> List[Dict[str, str]]:
        """Read CSV file and return list of row dictionaries.

        Args:
            file_path: Path to CSV file

        Returns:
            List of dictionaries, one per row (empty list on error)
        """
        logger.debug(f"Reading CSV file: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            logger.info(f"Read {len(rows)} rows from {file_path}")
            return rows

        except Exception as e:
            logger.error(f"Failed to read CSV file {file_path}: {e}")
            return []

    @staticmethod
    def write(file_path: str, rows: List[Dict[str, str]], columns: List[str]) -> bool:
        """Write rows to CSV file with specified columns.

        Args:
            file_path: Path for output CSV file
            rows: List of row dictionaries
            columns: List of column names in desired order

        Returns:
            True if write successful, False otherwise
        """
        if not rows:
            logger.warning("No rows to write")
            return False

        if not columns:
            logger.error("No columns specified")
            return False

        logger.debug(f"Writing {len(rows)} rows to {file_path}")

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")

                # Write header
                writer.writeheader()

                # Write rows
                for row in rows:
                    writer.writerow(row)

            logger.info(f"Successfully wrote {len(rows)} rows to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write CSV file {file_path}: {e}")
            return False
