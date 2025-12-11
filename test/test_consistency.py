#!/usr/bin/env python3
"""
Test consistency of Claude's gauge readings by running analysis multiple times
on the same image.
"""

import sys
import sys; import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); from check_oil_level import analyze_oil_gauge

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 test_consistency.py <image_path> <num_runs>")
        print(
            "Example: python3 test_consistency.py ../images/oil_snapshot_20251210_230931.jpg 10"
        )
        sys.exit(1)

    image_path = sys.argv[1]
    num_runs = int(sys.argv[2])

    print(f"Testing consistency on: {image_path}")
    print(f"Running {num_runs} times...")
    print("=" * 80)

    # Read image once
    with open(image_path, "rb") as f:
        image_data = f.read()

    results = []

    for i in range(num_runs):
        print(f"\nRun {i + 1}/{num_runs}...")
        result, percentage = analyze_oil_gauge(image_data)

        if percentage is not None:
            results.append(percentage)
            print(f"  Result: {percentage}%")
        else:
            print(f"  Result: Could not parse percentage")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"Total runs: {num_runs}")
    print(f"Successful parses: {len(results)}")

    if results:
        print(f"Percentages: {results}")
        print(f"Min: {min(results)}%")
        print(f"Max: {max(results)}%")
        print(f"Average: {sum(results) / len(results):.1f}%")
        print(f"Range: {max(results) - min(results)}%")

        # Group by value
        from collections import Counter

        counts = Counter(results)
        print(f"\nFrequency:")
        for percentage, count in sorted(counts.items()):
            print(f"  {percentage}%: {count} times")

    print("=" * 80)
