"""Core file organizer module."""

import csv
import logging
import os
import shutil
from typing import Any, Dict, List, Union, Optional

from .ai_facade import AIFacade
from .file_analyzer import FileAnalyzer

logger = logging.getLogger(__name__)


class FileOrganizer:
    """Organize files using AI categorization."""

    def __init__(self, ai_config: Dict[str, Any], labels: Union[List[str], Dict[str, List[str]]]):
        """
        Initialize the file organizer.

        Args:
            ai_config: Configuration for AI/LLM
            labels: List of category labels or hierarchical dict of labels with sub-labels
                   Examples:
                   - Flat list: ['Documents', 'Images', 'Videos']
                   - Hierarchical: {'Documents': ['Work', 'Personal'], 'Images': [], 'Videos': []}
        """
        self.ai_facade = AIFacade(ai_config)
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

    def organize_files(
        self, input_folder: str, output_folder: str, dry_run: bool = False, csv_report_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Organize files from input folder to output folder.

        Args:
            input_folder: Source folder containing files to organize
            output_folder: Destination folder for organized files
            dry_run: If True, don't actually move files, just show what would happen
            csv_report_path: Optional path to save CSV report of file classification

        Returns:
            Dictionary with statistics about the organization
        """
        # Validate input folder
        if not os.path.exists(input_folder):
            raise ValueError(f"Input folder does not exist: {input_folder}")

        # Create output folder if it doesn't exist
        if not dry_run and not os.path.exists(output_folder):
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

        # Process files
        stats = {
            "total_files": 0,
            "processed": 0,
            "failed": 0,
            "categorization": {label: 0 for label in self.labels},
        }

        # CSV report data
        csv_data = []

        for root, _, files in os.walk(input_folder):
            for filename in files:
                stats["total_files"] += 1
                file_path = os.path.join(root, filename)

                try:
                    # Analyze file
                    file_info = self.file_analyzer.analyze_file(file_path)

                    # Categorize using AI (returns "Category" or "Category/SubCategory")
                    category = self.ai_facade.categorize_file(file_info, self.labels)

                    if category is None:
                        logger.warning(
                            f"AI returned no category for file {filename}, assigning to 'Other'"
                        )
                        category = "Other"

                    # Parse category path (handles both "Category" and "Category/SubCategory")
                    category_parts = category.split("/")
                    main_category = category_parts[0]
                    
                    # Ensure main category exists in labels
                    if main_category not in self.labels:
                        logger.warning(
                            f"AI returned unknown category '{main_category}' for file {filename}, assigning to 'Other'"
                        )
                        category = "Other"
                        main_category = "Other"
                    
                    # Build destination directory path
                    category_parts = category.split("/")
                    dest_dir = os.path.join(output_folder, *category_parts)
                    
                    # Create destination directory if it doesn't exist (for dry run or if missed)
                    if not dry_run and not os.path.exists(dest_dir):
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
                            raise RuntimeError(
                                f"Could not find unique filename for {filename} after {max_attempts} attempts"
                            )

                    if not dry_run:
                        shutil.move(file_path, dest_path)

                    stats["processed"] += 1
                    stats["categorization"][main_category] += 1

                    message = f"{'[DRY RUN] ' if dry_run else ''}Moved {filename} -> {category}/"
                    print(message)
                    logger.info(message)

                    # Collect CSV data
                    if csv_report_path:
                        csv_data.append({
                            "file_name": filename,
                            "file_type": file_info.get("file_type", "unknown"),
                            "file_size": file_info.get("file_size", 0),
                            "decided_label": category
                        })

                except (IOError, OSError, RuntimeError) as e:
                    stats["failed"] += 1
                    error_msg = f"Error processing {filename}: {str(e)}"
                    print(error_msg)
                    logger.error(error_msg)

        # Write CSV report if requested
        if csv_report_path and csv_data:
            try:
                with open(csv_report_path, "w", newline="", encoding="utf-8") as csvfile:
                    fieldnames = ["file_name", "file_type", "file_size", "decided_label"]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(csv_data)
                logger.info(f"CSV report saved to: {csv_report_path}")
            except (IOError, OSError) as e:
                logger.error(f"Failed to write CSV report: {str(e)}")

        return stats
