"""Core file organizer module."""

import csv
import json
import logging
import os
import shutil
import threading
from typing import Any, Dict, List, Optional, Union

from .ai_facade import AIFacade
from .file_analyzer import FileAnalyzer

logger = logging.getLogger(__name__)

CSV_HEADERS = [
    "file_name",
    "file_size",
    "file_type",
    "mime_type",
    "is_executable",
    "file_info",
    "llm_response",
    "category",
    "sub_category",
    "error",
]


class FileOrganizer:
    """Organize files using AI categorization."""

    def __init__(
        self,
        ai_config: Dict[str, Any],
        labels: Union[List[str], Dict[str, List[str]]],
        input_folder: str,
        output_folder: str,
        dry_run: bool = False,
        csv_report_path: Optional[str] = None,
        is_debug=False,
        cancel_event: Optional[threading.Event] = None,
    ):
        """
        Initialize the file organizer.

        Args:
            ai_config: Configuration for AI/LLM
            labels: List of category labels or hierarchical dict of labels with sub-labels
                   Examples:
                   - Flat list: ['Documents', 'Images', 'Videos']
                   - Hierarchical: {'Documents': ['Work', 'Personal'], 'Images': [], 'Videos': []}
            input_folder: Source folder containing files to organize
            output_folder: Destination folder for organized files
            dry_run: If True, don't actually move files, just show what would happen
            csv_report_path: Optional path to save CSV report of file classification
            is_debug: If True, enable debug logging
            cancel_event: Optional threading.Event to signal cancellation
        """
        self.is_debug = is_debug
        self.cancel_event = cancel_event
        self.ai_facade = AIFacade(ai_config, cancel_event=self.cancel_event)
        self.file_analyzer = FileAnalyzer()

        # Normalize labels to hierarchical format
        if isinstance(labels, list):
            # Convert flat list to hierarchical dict with empty sub-labels
            self.labels = {label: [] for label in labels}
        else:
            self.labels = labels

        # Ensure 'Other' category exists
        if "Other" not in self.labels:
            self.labels["Other"] = []

        self.input_folder = input_folder
        self.output_folder = output_folder
        self.dry_run = dry_run
        self.csv_report_path = csv_report_path

        # Validate input folder
        if not os.path.exists(input_folder):
            raise ValueError(f"Input folder does not exist: {input_folder}")

        # Create output folder if it doesn't exist
        if not dry_run:
            if output_folder is None or len(output_folder) == 0:
                raise ValueError("Output folder must be specified")
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

        # Create subdirectories for each label and sub-label
        if not dry_run:
            for label, sub_labels in self.labels.items():
                label_dir = os.path.join(output_folder, label)
                if not os.path.exists(label_dir):
                    os.makedirs(label_dir)
                # Create sub-directories if sub-labels exist
                for sub_label in sub_labels:
                    sub_label_dir = os.path.join(label_dir, sub_label)
                    if not os.path.exists(sub_label_dir):
                        os.makedirs(sub_label_dir)

    def organize_files(self) -> Dict[str, Any]:
        """
        Organize files from input folder to output folder.

        Returns:
            Dictionary with statistics about the organization
        """
        # Process files
        stats = {
            "total_files": 0,
            "processed": 0,
            "failed": 0,
            "categorization": {label: 0 for label in self.labels},
        }

        for root, _, files in os.walk(self.input_folder):
            for filename in files:
                # Check for cancellation request before processing each file
                if self.cancel_event is not None and self.cancel_event.is_set():
                    logger.info("Cancellation requested, stopping organization")
                    return stats

                stats["total_files"] += 1
                file_path = os.path.join(root, filename)
                file_info = None
                llm_response = None

                try:
                    # Analyze file
                    file_info = self.file_analyzer.analyze_file(file_path)

                    # Categorize using AI (returns "Category" or "Category/SubCategory")
                    llm_response, category_parts = self.ai_facade.categorize_file(file_info, self.labels)

                    if category_parts is None:
                        logger.warning(f"AI returned no category for file {filename}, assigning to 'Other'")
                        category = "Other"
                        sub_category = None
                    else:
                        category = category_parts[0]
                        sub_category = category_parts[1] if len(category_parts) > 1 else None

                    if not self.dry_run:
                        self._move_file(filename, file_path, category, sub_category)

                    stats["processed"] += 1
                    stats["categorization"][category] += 1

                    message = f"{'[DRY RUN] ' if self.dry_run else ''}Moved {filename} -> {category}/"
                    logger.info(message)

                    self._record_file_processing(filename, file_info, llm_response, category, sub_category, "")

                except Exception as e:
                    stats["failed"] += 1
                    error_msg = f"Error processing {filename}: {repr(e)}"

                    if self.is_debug:
                        logger.exception(error_msg)
                    else:
                        logger.error(error_msg)

                    self._record_file_processing(filename, file_info, llm_response, "", "", repr(e))

        return stats

    def _move_file(self, filename: str, file_path: str, category: str, sub_category: str | None):
        dest_dir = os.path.join(self.output_folder, *([category, sub_category] if sub_category else [category]))

        # Create destination directory if it doesn't exist (for dry run or if missed)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        dest_path = os.path.join(dest_dir, filename)

        # Handle duplicate filenames
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            max_attempts = 1000
            while os.path.exists(dest_path) and counter < max_attempts:
                new_filename = f"{base}_{counter}{ext}"
                dest_path = os.path.join(dest_dir, new_filename)
                counter += 1

            if counter >= max_attempts:
                raise RuntimeError(f"Could not find unique filename for {filename} after {max_attempts} attempts")

        shutil.move(file_path, dest_path)

    def _record_file_processing(self, file_name: str, file_info: dict[str, Any], llm_response: str, category: str, sub_category: str, error: str):
        if self.csv_report_path:
            try:
                write_header = True
                if os.path.exists(self.csv_report_path) and os.path.getsize(self.csv_report_path) > 0:
                    write_header = False

                with open(self.csv_report_path, "a", newline="", encoding="utf-8") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADERS)
                    if write_header:
                        writer.writeheader()

                    row = {
                        "file_name": file_name,
                        "file_size": file_info.get("file_size", 0) if file_info else "",
                        "file_type": file_info.get("file_type", "unknown") if file_info else "",
                        "mime_type": file_info.get("mime_type", "unknown") if file_info else "",
                        "is_executable": file_info.get("is_executable", False) if file_info else "",
                        "file_info": json.dumps(file_info, ensure_ascii=False),
                        "llm_response": llm_response,
                        "category": category,
                        "sub_category": sub_category,
                        "error": error,
                    }

                    writer.writerow(row)
            except (IOError, OSError) as e:
                logger.error(f"Failed to append to CSV report {self.csv_report_path}: {e}")
