#!/usr/bin/env python3
"""Continuous mode runner for AI File Organizer."""

import os
import sys
import time
import yaml
import logging
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, '/app/src')

from ai_file_organizer.organizer import FileOrganizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def run_continuous(config_path='/app/config.yml'):
    """Run organizer in continuous mode."""
    logger.info("Starting AI File Organizer in continuous mode")
    
    # Load configuration
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    
    config = load_config(config_path)
    
    # Extract configuration
    ai_config = config.get('ai', {})
    labels = config.get('labels', [])
    input_folder = config.get('input_folder', '/input')
    output_folder = config.get('output_folder', '/output')
    continuous = config.get('continuous', False)
    interval = config.get('interval', 60)  # Default 60 seconds
    
    if not labels:
        logger.error("No labels specified in configuration")
        sys.exit(1)
    
    # Create organizer
    organizer = FileOrganizer(ai_config, labels)
    
    logger.info(f"Input folder: {input_folder}")
    logger.info(f"Output folder: {output_folder}")
    logger.info(f"Labels: {', '.join(labels)}")
    logger.info(f"Continuous mode: {continuous}")
    
    if continuous:
        logger.info(f"Running in continuous mode with {interval}s interval")
        while True:
            try:
                logger.info("Starting organization cycle...")
                stats = organizer.organize_files(input_folder, output_folder, dry_run=False)
                logger.info(f"Cycle complete. Processed: {stats['processed']}, Failed: {stats['failed']}")
                
                for label, count in stats['categorization'].items():
                    if count > 0:
                        logger.info(f"  {label}: {count} files")
                
                logger.info(f"Sleeping for {interval} seconds...")
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error during organization cycle: {e}")
                time.sleep(interval)
    else:
        # Run once
        logger.info("Running in single-shot mode")
        stats = organizer.organize_files(input_folder, output_folder, dry_run=False)
        logger.info(f"Organization complete. Processed: {stats['processed']}, Failed: {stats['failed']}")
        
        for label, count in stats['categorization'].items():
            if count > 0:
                logger.info(f"  {label}: {count} files")


if __name__ == '__main__':
    config_path = os.getenv('CONFIG_PATH', '/app/config.yml')
    run_continuous(config_path)
