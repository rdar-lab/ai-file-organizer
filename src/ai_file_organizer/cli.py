"""CLI interface for AI File Organizer."""

import argparse
import sys

import yaml

from .organizer import FileOrganizer


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI File Organizer - Organize files using AI/LLM models"
    )

    parser.add_argument(
        "-i", "--input", required=True, help="Input folder containing files to organize"
    )

    parser.add_argument(
        "-o", "--output", required=True, help="Output folder for organized files"
    )

    parser.add_argument(
        "-l", "--labels", nargs="+", help="List of category labels (space-separated)"
    )

    parser.add_argument("-c", "--config", help="Path to configuration file (YAML)")

    parser.add_argument(
        "--provider",
        choices=["openai", "azure", "local"],
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
        "--base-url", help="Base URL for local LLM (for local provider)"
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

    args = parser.parse_args()

    # Load configuration
    if args.config:
        config = load_config(args.config)
        ai_config = config.get("ai", {})
        labels = config.get("labels", [])
    else:
        ai_config = {
            "provider": args.provider,
            "model": args.model,
            "temperature": args.temperature,
        }

        if args.api_key:
            ai_config["api_key"] = args.api_key

        if args.azure_endpoint:
            ai_config["azure_endpoint"] = args.azure_endpoint

        if args.base_url:
            ai_config["base_url"] = args.base_url

        labels = args.labels or []

    # Validate labels
    if not labels:
        print("Error: No labels specified. Use --labels or provide a config file.")
        sys.exit(1)

    # Create organizer and process files
    try:
        organizer = FileOrganizer(ai_config, labels)
        print("Starting file organization...")
        print(f"Input folder: {args.input}")
        print(f"Output folder: {args.output}")
        print(f"Labels: {', '.join(labels)}")
        print(f"Provider: {ai_config['provider']}")
        print(f"Model: {ai_config['model']}")

        if args.dry_run:
            print("\n*** DRY RUN MODE - No files will be moved ***\n")

        stats = organizer.organize_files(args.input, args.output, dry_run=args.dry_run)

        print("\n" + ("=" * 50))
        print("Organization Complete!")
        print("=" * 50)
        print(f"Total files: {stats['total_files']}")
        print(f"Processed: {stats['processed']}")
        print(f"Failed: {stats['failed']}")
        print("\nCategorization:")
        for label, count in stats["categorization"].items():
            print(f"  {label}: {count} files")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
