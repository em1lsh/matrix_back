"""
Compare baseline and optimized load test results
"""

import csv
from pathlib import Path


def read_stats(csv_path):
    """Read stats from Locust CSV file"""
    stats = {}

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Name"] == "Aggregated":
                stats = {
                    "requests": int(row["Request Count"]),
                    "failures": int(row["Failure Count"]),
                    "median": float(row["Median Response Time"]),
                    "p95": float(row["95%"]),
                    "p99": float(row["99%"]),
                    "avg": float(row["Average Response Time"]),
                    "min": float(row["Min Response Time"]),
                    "max": float(row["Max Response Time"]),
                    "rps": float(row["Requests/s"]),
                }
                break

    return stats


def calculate_improvement(baseline, optimized):
    """Calculate improvement percentage"""
    if baseline == 0:
        return 0
    return ((optimized - baseline) / baseline) * 100


def main():
    """Main comparison function"""
    results_dir = Path(__file__).parent / "results"

    baseline_csv = results_dir / "baseline" / "stats_stats.csv"
    optimized_csv = results_dir / "optimized" / "stats_stats.csv"

    if not baseline_csv.exists():
        print(f"Baseline results not found: {baseline_csv}")
        return

    if not optimized_csv.exists():
        print(f"Optimized results not found: {optimized_csv}")
        return

    print("Loading test results...")
    baseline = read_stats(baseline_csv)
    optimized = read_stats(optimized_csv)

    # Generate comparison report
    report = []
    report.append("=" * 80)
    report.append("LOAD TEST COMPARISON REPORT")
    report.append("=" * 80)
    report.append("")

    report.append("BASELINE (Before Refactoring)")
    report.append("-" * 80)
    report.append(f"Total Requests:        {baseline['requests']:,}")
    report.append(f"Failed Requests:       {baseline['failures']:,}")
    report.append(f"Error Rate:            {(baseline['failures']/baseline['requests']*100):.2f}%")
    report.append(f"Requests/sec:          {baseline['rps']:.2f}")
    report.append(f"Response Time (avg):   {baseline['avg']:.2f} ms")
    report.append(f"Response Time (p50):   {baseline['median']:.2f} ms")
    report.append(f"Response Time (p95):   {baseline['p95']:.2f} ms")
    report.append(f"Response Time (p99):   {baseline['p99']:.2f} ms")
    report.append(f"Response Time (max):   {baseline['max']:.2f} ms")
    report.append("")

    report.append("OPTIMIZED (After Refactoring)")
    report.append("-" * 80)
    report.append(f"Total Requests:        {optimized['requests']:,}")
    report.append(f"Failed Requests:       {optimized['failures']:,}")
    report.append(f"Error Rate:            {(optimized['failures']/optimized['requests']*100):.2f}%")
    report.append(f"Requests/sec:          {optimized['rps']:.2f}")
    report.append(f"Response Time (avg):   {optimized['avg']:.2f} ms")
    report.append(f"Response Time (p50):   {optimized['median']:.2f} ms")
    report.append(f"Response Time (p95):   {optimized['p95']:.2f} ms")
    report.append(f"Response Time (p99):   {optimized['p99']:.2f} ms")
    report.append(f"Response Time (max):   {optimized['max']:.2f} ms")
    report.append("")

    report.append("IMPROVEMENT")
    report.append("-" * 80)

    # Calculate improvements
    rps_improvement = calculate_improvement(baseline["rps"], optimized["rps"])
    avg_improvement = calculate_improvement(baseline["avg"], optimized["avg"])
    p95_improvement = calculate_improvement(baseline["p95"], optimized["p95"])
    error_rate_baseline = baseline["failures"] / baseline["requests"] * 100
    error_rate_optimized = optimized["failures"] / optimized["requests"] * 100
    error_improvement = calculate_improvement(error_rate_baseline, error_rate_optimized)

    report.append(f"Requests/sec:          {rps_improvement:+.2f}% ({baseline['rps']:.2f} -> {optimized['rps']:.2f})")
    report.append(
        f"Response Time (avg):   {avg_improvement:+.2f}% ({baseline['avg']:.2f} -> {optimized['avg']:.2f} ms)"
    )
    report.append(
        f"Response Time (p95):   {p95_improvement:+.2f}% ({baseline['p95']:.2f} -> {optimized['p95']:.2f} ms)"
    )
    report.append(
        f"Error Rate:            {error_improvement:+.2f}% ({error_rate_baseline:.2f}% -> {error_rate_optimized:.2f}%)"
    )
    report.append("")

    report.append("SUMMARY")
    report.append("-" * 80)

    if rps_improvement > 0:
        report.append(f"✓ Throughput improved by {rps_improvement:.1f}%")
    else:
        report.append(f"✗ Throughput decreased by {abs(rps_improvement):.1f}%")

    if avg_improvement < 0:
        report.append(f"✓ Average response time improved by {abs(avg_improvement):.1f}%")
    else:
        report.append(f"✗ Average response time increased by {avg_improvement:.1f}%")

    if p95_improvement < 0:
        report.append(f"✓ P95 response time improved by {abs(p95_improvement):.1f}%")
    else:
        report.append(f"✗ P95 response time increased by {p95_improvement:.1f}%")

    if error_improvement < 0:
        report.append(f"✓ Error rate improved by {abs(error_improvement):.1f}%")
    else:
        report.append(f"✗ Error rate increased by {error_improvement:.1f}%")

    report.append("")
    report.append("=" * 80)

    # Print report
    report_text = "\n".join(report)
    print(report_text)

    # Save report
    report_path = results_dir / "comparison_report.txt"
    with open(report_path, "w") as f:
        f.write(report_text)

    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
