"""Migration script for autofix evaluation data.

This script migrates existing autofix evaluation data from the legacy format
to the new consolidated eval storage framework.
"""

import argparse
import logging
from pathlib import Path

from .config import EVAL_BASE_DIR, ensure_eval_directories
from .eval_adapter import AutofixEvalAdapter

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main migration function."""
    parser = argparse.ArgumentParser(
        description="Migrate autofix evaluation data to new storage format",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually migrating",
    )
    parser.add_argument(
        "--legacy-dir",
        type=Path,
        default=Path(".solve/eval/results/llm"),
        help="Path to legacy evaluation directory (default: .solve/eval/results/llm)",
    )

    args = parser.parse_args()

    # Check if legacy directory exists
    if not args.legacy_dir.exists():
        logger.info(
            f"Legacy directory {args.legacy_dir} does not exist. Nothing to migrate."
        )
        return

    # Ensure new directory structure exists
    ensure_eval_directories()
    logger.info(f"New evaluation data will be stored in: {EVAL_BASE_DIR}")

    # Create adapter
    adapter = AutofixEvalAdapter()

    if args.dry_run:
        # Just show what would be migrated
        logger.info("DRY RUN - Checking what would be migrated...")

        # Check for all_evals.jsonl
        master_log = args.legacy_dir / "all_evals.jsonl"
        if master_log.exists():
            with open(master_log) as f:
                line_count = sum(1 for _ in f)
            logger.info(f"Found {line_count} evaluations in {master_log}")

        # Check for individual eval files
        eval_files = list(args.legacy_dir.glob("eval_*.json"))
        if eval_files:
            logger.info(f"Found {len(eval_files)} individual evaluation files")

        if not master_log.exists() and not eval_files:
            logger.info("No evaluation data found to migrate")
    else:
        # Perform actual migration
        logger.info("Starting migration...")

        try:
            migrated = adapter.migrate_legacy_data()
            logger.info(f"Successfully migrated {migrated} evaluations")

            # Show where data was migrated to
            logger.info(f"Data migrated to: {EVAL_BASE_DIR}")
            logger.info("Legacy data has been preserved in its original location")
            logger.info(
                "The autofix system will now write to both locations for backward compatibility",
            )

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise


if __name__ == "__main__":
    main()
