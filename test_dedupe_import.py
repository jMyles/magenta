#!/usr/bin/env python
"""
Test script to verify import deduplication logic.

This tests that importing the same JSONL files twice doesn't create duplicate messages.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'memory_viewer.settings')
django.setup()

from conversations.models import TYPES_TO_TRACK
from conversations.management.commands.import_claude_code_jsonl import Command as ImportCommand


def get_counts():
    """Get current database counts."""
    counts = {}
    for thing_to_count in TYPES_TO_TRACK:
        counts[thing_to_count] = thing_to_count.objects.count()
    return counts

def main():
    print("=" * 60)
    print("Testing Import Deduplication Logic")
    print("=" * 60)

    # Get baseline
    before = get_counts()
    print("BEFORE FIRST IMPORT:")
    print(before)

    # Find a small JSONL file to test with
    backup_dir = '/home/magent/.claude/projects/-home-jmyles-projects-JustinHolmesMusic-arthel'
    jsonl_files = [f for f in os.listdir(backup_dir) if f.endswith('.jsonl')]

    if not jsonl_files:
        print("\nERROR: No JSONL files found in backup directory")
        return

    # Use the first file for testing
    test_file = os.path.join(backup_dir, jsonl_files[0])
    print(f"\nTest file: {test_file}")

    # First import
    print("\n" + "-" * 60)
    print("FIRST IMPORT - Should create new records")
    print("-" * 60)

    importer = ImportCommand()
    importer.watchlist = set()  # Initialize watchlist
    importer.handle(
        file=test_file,
        directory=None,
        era_id=None,
        era_name='Test Deduplication Era'
    )

    after_first = get_counts()
    print("AFTER FIRST IMPORT")
    print(after_first)

    # Get import stats
    first_stats = ImportCommand.last_import_stats
    if first_stats and 'import_counts' in first_stats:
        print("\nFirst import counts (from importer):")
        for model_name, counts in first_stats['import_counts'].items():
            print(f"  {model_name}: {counts['created']} created, {counts['not_created']} skipped")

    # Calculate what was added
    first_delta = {
        key: after_first[key] - before[key]
        for key in before.keys()
    }
    print("\nFirst import added (from database):")
    for key, count in first_delta.items():
        print(f"  {key.__name__}: +{count}")

    # Second import (should be idempotent)
    print("\n" + "-" * 60)
    print("SECOND IMPORT - Should NOT create duplicates")
    print("-" * 60)

    importer = ImportCommand()
    importer.watchlist = set()  # Initialize watchlist
    importer.handle(
        file=test_file,
        directory=None,
        era_id=None,
        era_name='Test Deduplication Era'
    )

    after_second = get_counts()
    print("AFTER SECOND IMPORT")
    print(after_second)

    # Get import stats
    second_stats = ImportCommand.last_import_stats
    if second_stats and 'import_counts' in second_stats:
        print("\nSecond import counts (from importer):")
        for model_name, counts in second_stats['import_counts'].items():
            print(f"  {model_name}: {counts['created']} created, {counts['not_created']} skipped")

    # Calculate what was added in second import
    second_delta = {
        key: after_second[key] - after_first[key]
        for key in before.keys()
    }
    print("\nSecond import added (from database):")
    for key, count in second_delta.items():
        print(f"  {key.__name__}: +{count}")

    # Verify deduplication worked
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    # Check database deltas
    if all(count == 0 for count in second_delta.values()):
        print("✅ Database: Second import created NO duplicate records")
    else:
        print("❌ Database: Second import created duplicates:")
        for key, count in second_delta.items():
            if count > 0:
                print(f"     {key.__name__}: +{count}")

    # Check importer counts
    if second_stats and 'import_counts' in second_stats:
        all_skipped = all(
            counts['created'] == 0
            for counts in second_stats['import_counts'].values()
        )
        if all_skipped:
            print("✅ Importer: All objects were skipped (not_created > 0)")
        else:
            print("❌ Importer: Some objects were created:")
            for model_name, counts in second_stats['import_counts'].items():
                if counts['created'] > 0:
                    print(f"     {model_name}: {counts['created']} created")

    print("=" * 60)


if __name__ == '__main__':
    main()
