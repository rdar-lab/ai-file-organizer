"""Core file organizer module."""

import logging
import os
import shutil
from typing import Any, Dict, List

from .ai_facade import AIFacade
from .file_analyzer import FileAnalyzer

logger = logging.getLogger(__name__)


class FileOrganizer:
    """Organize files using AI categorization."""

    def __init__(self, ai_config: Dict[str, Any], labels: List[str]):
        """
        Initialize the file organizer.

        Args:
            ai_config: Configuration for AI/LLM
            labels: List of category labels
        """
        self.ai_facade = AIFacade(ai_config)
        self.file_analyzer = FileAnalyzer()
        self.labels = labels

    def organize_files(
        self, input_folder: str, output_folder: str, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Organize files from input folder to output folder.

        Args:
            input_folder: Source folder containing files to organize
            output_folder: Destination folder for organized files
            dry_run: If True, don't actually move files, just show what would happen

        Returns:
            Dictionary with statistics about the organization
        """
        # Validate input folder
        if not os.path.exists(input_folder):
            raise ValueError(f"Input folder does not exist: {input_folder}")

        # Create output folder if it doesn't exist
        if not dry_run and not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Create subdirectories for each label
        if not dry_run:
            for label in self.labels:
                label_dir = os.path.join(output_folder, label)
                if not os.path.exists(label_dir):
                    os.makedirs(label_dir)

        # Process files
        stats = {
            "total_files": 0,
            "processed": 0,
            "failed": 0,
            "categorization": {label: 0 for label in self.labels},
        }

        for root, dirs, files in os.walk(input_folder):
            for filename in files:
                stats["total_files"] += 1
                file_path = os.path.join(root, filename)

                try:
                    # Analyze file
                    file_info = self.file_analyzer.analyze_file(file_path)

                    # Categorize using AI
                    category = self.ai_facade.categorize_file(file_info, self.labels)

                    # Move file to appropriate category folder
                    dest_dir = os.path.join(output_folder, category)
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
                    stats["categorization"][category] += 1

                    message = f"{'[DRY RUN] ' if dry_run else ''}Moved {filename} -> {category}/"
                    print(message)
                    logger.info(message)

                except (IOError, OSError, RuntimeError) as e:
                    stats["failed"] += 1
                    error_msg = f"Error processing {filename}: {str(e)}"
                    print(error_msg)
                    logger.error(error_msg)

        return stats
