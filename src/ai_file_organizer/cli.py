"""CLI interface for AI File Organizer."""

import argparse
import logging
import os
import sys
import time
from argparse import Namespace
from typing import Optional

import yaml

from .organizer import FileOrganizer

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def _str_to_bool(val: Optional[str]) -> bool:
    if val is None:
        return False
    return str(val).lower() in ("1", "true", "yes", "y")


def _env_or_none(name: str) -> Optional[str]:
    v = os.getenv(name)
    return v if v is not None and v != "" else None


def _read_config(
    config_obj,
    args_obj,
    config_key,
    arg_key,
    env_key,
    parse_env_func=None,
    default_value=None,
):
    # First priority - read from args
    arg_val = getattr(args_obj, arg_key, None)
    if arg_val is not None:
        return arg_val
    # Second priority - read from config
    if config_obj and config_key in config_obj:
        return config_obj[config_key]
    # Last priority - read from env var
    env_val = _env_or_none(env_key)
    if parse_env_func and env_val is not None:
        return parse_env_func(env_val)

    return default_value


def main():
    # Initialize logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("Starting up...")

    args = _init_args_parser()

    # Load configuration from file if provided (CLI arg takes precedence)
    config = {}
    config_path = args.config or _env_or_none("CONFIG_PATH")
    if config_path:
        config = load_config(args.config)

    ai_config = config.get("ai", {})

    provider = _read_config(ai_config, args, "provider", "provider", "PROVIDER", None, "openai")
    model = _read_config(ai_config, args, "model", "model", "MODEL", None, "gpt-3.5-turbo")
    temperature = _read_config(ai_config, args, "temperature", "temperature", "TEMPERATURE", float, 0.3)
    api_key = _read_config(ai_config, args, "api_key", "api_key", "API_KEY")
    azure_endpoint = _read_config(ai_config, args, "azure_endpoint", "azure_endpoint", "AZURE_ENDPOINT")
    base_url = _read_config(
        ai_config,
        args,
        "base_url",
        "base_url",
        "BASE_URL",
        None,
        "http://localhost:11434/v1",
    )
    ensure_model = _read_config(
        ai_config,
        args,
        "ensure_model",
        "ensure_model",
        "ENSURE_MODEL",
        _str_to_bool,
        True,
    )

    ai_config = {
        "provider": provider,
        "model": model,
        "temperature": float(temperature) if temperature is not None else None,
        "api_key": api_key,
        "azure_endpoint": azure_endpoint,
        "base_url": base_url,
        "ensure_model": bool(ensure_model) if ensure_model is not None else True,
    }

    labels = _read_config(config, args, "labels", "labels", "LABELS", _parse_cs_to_list, [])
    # Validate labels
    if not labels:
        logger.error("No labels specified. Use --labels, provide them in config, or set the LABELS env variable.")
        sys.exit(1)

    dry_run = _read_config(config, args, "dry_run", "dry_run", "DRY_RUN", _str_to_bool, False)
    csv_report = _read_config(config, args, "csv_report", "csv_report", "CSV_REPORT")

    input_folder = _read_config(config, args, "input_folder", "input", "INPUT_FOLDER")

    # Validate input
    if not input_folder:
        logger.error("No input folder specified. Use --input, provide it in config, or set INPUT_FOLDER env variable.")
        sys.exit(1)

    output_folder = _read_config(
        config,
        args,
        "output_folder",
        "output",
        "OUTPUT_FOLDER",
    )
    continuous = _read_config(config, args, "continuous", "continuous", "CONTINUOUS", _str_to_bool, False)

    interval = _read_config(config, args, "interval", "interval", "INTERVAL", int)

    # Build masked ai_config for logging (don't print api_key)
    masked_ai_config = {k: v for k, v in ai_config.items() if k != "api_key"}

    logger.info("Starting file organization...")
    logger.info(f"Using AI Config: {masked_ai_config}")
    logger.info(f"Input folder: {input_folder}")
    logger.info(f"Output folder: {output_folder}")
    logger.info(f"Labels: {', '.join(labels)}")

    if dry_run:
        logging.info("*** DRY RUN MODE - No files will be moved ***")
    if csv_report:
        logging.info(f"CSV report will be saved to: {csv_report}")

    try:
        if continuous:
            logger.info(f"Running in continuous mode with {interval}s interval")
            while True:
                try:
                    _run_once(
                        ai_config,
                        labels,
                        input_folder,
                        output_folder,
                        dry_run,
                        csv_report,
                    )
                    logger.info(f"Sleeping for {interval} seconds...")
                    time.sleep(interval)
                except KeyboardInterrupt:
                    logger.info("Interrupted by user")
                    break
                except Exception as e:
                    logger.exception(f"Error during organization cycle: {e}")
                    time.sleep(interval)
        else:
            _run_once(ai_config, labels, input_folder, output_folder, dry_run, csv_report)
    except SystemExit:
        # propagate SystemExit so callers (like docker-runner) can handle it
        raise
    except Exception as e:
        logger.error(f"Error in CLI: {e}")
        sys.exit(1)


def _run_once(ai_config, labels, input_folder, output_folder, dry_run, csv_report):
    logger.info("Starting organization cycle...")
    organizer = FileOrganizer(
        ai_config,
        labels,
        input_folder,
        output_folder,
        dry_run=dry_run,
        csv_report_path=csv_report,
    )
    stats = organizer.organize_files()

    logger.info("\n" + ("=" * 50))
    logger.info("Organization Complete!")
    logger.info("=" * 50)
    # Some organizer implementations use 'total_files' or 'processed'
    if "total_files" in stats:
        logger.info(f"Total files: {stats['total_files']}")
    if "processed" in stats:
        logger.info(f"Processed: {stats['processed']}")
    if "failed" in stats:
        logger.info(f"Failed: {stats['failed']}")
    logger.info("Categorization:")
    for label, count in stats.get("categorization", {}).items():
        logger.info(f"  {label}: {count} files")


def _parse_cs_to_list(values: str) -> list[str]:
    return [p.strip() for p in values.replace(";", ",").split(",") if p.strip()]


def _init_args_parser() -> Namespace:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="AI File Organizer - Organize files using AI/LLM models")

    # Make --input optional; it can be provided in config or via env var
    parser.add_argument("-i", "--input", help="Input folder containing files to organize")

    parser.add_argument("-o", "--output", help="Output folder for organized files")

    parser.add_argument("-l", "--labels", nargs="+", help="List of category labels (space-separated)")

    parser.add_argument("-c", "--config", help="Path to configuration file (YAML)")

    parser.add_argument(
        "--provider",
        choices=["openai", "azure", "google", "local"],
        help="LLM provider",
    )

    parser.add_argument("--model", help="Model name")

    parser.add_argument("--api-key", help="API key for the LLM provider")

    parser.add_argument("--azure-endpoint", help="Azure endpoint URL (for Azure provider)")

    parser.add_argument(
        "--base-url",
        help="Base URL for local LLM (for local provider)",
    )

    parser.add_argument(
        "--ensure-model",
        help="If to ensure the model is available locally (for local provider)",
        action="store_true",
    )

    parser.add_argument(
        "--temperature",
        type=float,
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

    # Continuous mode options (can also be set via environment variables)
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run in continuous mode (poll at interval)",
    )

    parser.add_argument(
        "--interval",
        type=int,
        help="Interval in seconds for continuous mode (default: 60)",
    )

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()
