"""CLI interface for AI File Organizer."""

import argparse
import logging
import sys

import yaml

from .organizer import FileOrganizer

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def main():
    # Initialize logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI File Organizer - Organize files using AI/LLM models"
    )

    parser.add_argument(
        "-i", "--input", required=True, help="Input folder containing files to organize"
    )

    parser.add_argument(
        "-o", "--output", help="Output folder for organized files"
    )

    parser.add_argument(
        "-l", "--labels", nargs="+", help="List of category labels (space-separated)"
    )

    parser.add_argument("-c", "--config", help="Path to configuration file (YAML)")

    parser.add_argument(
        "--provider",
        choices=["openai", "azure", "google", "local"],
        default="openai",
        help="LLM provider (default: openai)",
    )

    parser.add_argument(
        "--model", default="gpt-3.5-turbo", help="Model name (default: gpt-3.5-turbo)"
    )

    parser.add_argument("--api-key", help="API key for the LLM provider")

    parser.add_argument(
        "--azure-endpoint", help="Azure endpoint URL (for Azure provider)"
    )

    parser.add_argument(
        "--base-url",
        help="Base URL for local LLM (for local provider) - default http://localhost:11434/v1"
    )

    parser.add_argument(
        "--ensure-model",
        help="If to ensure the model is available locally (for local provider)",
        action="store_true",
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
        help="Temperature for LLM (default: 0.3)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without actually moving files",
    )

    parser.add_argument(
        "--csv-report",
        help="Path to save CSV report of file classification (useful with --dry-run)",
    )

    args = parser.parse_args()

    ai_config = None
    labels = None
    dry_run = False
    csv_report = None

    # Load configuration
    if args.config:
        config = load_config(args.config)
        ai_config = config.get("ai", {})
        labels = config.get("labels", [])
        dry_run = config.get('dry_run', False)
        csv_report = config.get('csv_report')

    if ai_config is None:
        ai_config = {}

    if labels is None:
        labels = []

    # Override config with CLI args if provided
    if args.provider:
        ai_config["provider"] = args.provider

    if args.model:
        ai_config["model"] = args.model

    if args.temperature is not None:
        ai_config["temperature"] = args.temperature

    if args.api_key:
        ai_config["api_key"] = args.api_key

    if args.azure_endpoint:
        ai_config["azure_endpoint"] = args.azure_endpoint

    if args.base_url:
        ai_config["base_url"] = args.base_url

    if args.ensure_model:
        ai_config["ensure_model"] = args.ensure_model

    if args.labels:
        labels = args.labels

    if args.dry_run:
        dry_run = True

    if args.csv_report:
        csv_report = args.csv_report

    # Validate labels
    if not labels:
        logger.error("No labels specified. Use --labels or provide a config file.")
        sys.exit(1)

    # Create organizer and process files
    try:
        masked_ai_config = {k: v for k, v in ai_config.items() if k != "api_key"}
        logger.info("Starting file organization...")
        logger.info(f"Using AI Config: {masked_ai_config}")
        logger.info(f"Input folder: {args.input}")
        logger.info(f"Output folder: {args.output}")
        logger.info(f"Labels: {', '.join(labels)}")
        logger.info(f"Dry run: {dry_run}")
        if csv_report:
            logger.info(f"CSV report: {csv_report}")

        if dry_run:
            logging.info("*** DRY RUN MODE - No files will be moved ***")

        organizer = FileOrganizer(ai_config, labels)

        stats = organizer.organize_files(
            args.input, args.output, dry_run=dry_run, csv_report_path=csv_report
        )

        logger.info("\n" + ("=" * 50))
        logger.info("Organization Complete!")
        logger.info("=" * 50)
        logger.info(f"Total files: {stats['total_files']}")
        logger.info(f"Processed: {stats['processed']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info("Categorization:")
        for label, count in stats["categorization"].items():
            logger.info(f"  {label}: {count} files")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
