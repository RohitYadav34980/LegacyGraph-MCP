"""
benchmark_timing.py — LegacyGraph-MCP performance benchmarking.

Two profiles are provided:

  run_performance_benchmark(target, ...)
      Normal profile: uses all available cores (80 % cap).

  run_constrained_benchmark(target, *, max_workers, chunk_size_override, ...)
      Constrained profile: simulates low-spec / shared-host environments by
      capping workers and chunk size via the LEGACYMCP_MAX_WORKERS /
      LEGACYMCP_CHUNK_SIZE env-var overrides added to helpers.py.

Running this file directly (python tests/benchmark_timing.py) executes both
profiles on the configured target and prints a recommendation table.
"""

import os
import time
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# LegacyGraph-MCP imports
from src.utils.helpers import _clone_repo, _scan_directory
import src.utils.services as services
from src.core.graph import DependencyGraph

# Set up simple logging for the benchmark
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark")


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    label: str
    target: str
    files_parsed: int = 0
    files_skipped: int = 0
    node_count: int = 0
    clone_duration: float = 0.0
    build_duration: float = 0.0
    max_workers: Optional[int] = None
    chunk_size: Optional[int] = None
    error: Optional[str] = None

    @property
    def total_duration(self) -> float:
        return self.clone_duration + self.build_duration

    @property
    def speed(self) -> float:
        if self.build_duration > 0 and self.files_parsed > 0:
            return self.files_parsed / self.build_duration
        return 0.0


# ---------------------------------------------------------------------------
# Internal runner
# ---------------------------------------------------------------------------

def _run_benchmark(
    label: str,
    target: str,
    is_local_dir: bool = False,
) -> BenchmarkResult:
    """
    Core benchmark runner. Env vars LEGACYMCP_MAX_WORKERS / LEGACYMCP_CHUNK_SIZE
    must be set by the caller before invoking this function if overrides are desired.
    """
    result = BenchmarkResult(label=label, target=target)
    services.graph_service = DependencyGraph()
    clone_dir: Optional[Path] = None

    try:
        if not is_local_dir:
            logger.info(f"[{label}] Phase 1: Cloning repository...")
            t0 = time.perf_counter()
            clone_dir = _clone_repo(target)
            result.clone_duration = time.perf_counter() - t0
            logger.info(f"[{label}] Cloning complete in {result.clone_duration:.3f}s")
            scan_path = clone_dir
        else:
            scan_path = Path(target)
            logger.info(f"[{label}] Phase 1: Using local directory: {scan_path}")

        logger.info(f"[{label}] Phase 2: Scanning / parsing / building graph...")
        t0 = time.perf_counter()
        result.files_parsed, result.files_skipped, result.node_count = _scan_directory(scan_path)
        result.build_duration = time.perf_counter() - t0
        logger.info(f"[{label}] Build complete in {result.build_duration:.3f}s")

    except Exception as e:
        result.error = str(e)
        logger.error(f"[{label}] Benchmark failed: {e}")
    finally:
        if clone_dir and clone_dir.exists():
            shutil.rmtree(clone_dir, ignore_errors=True)
            logger.info(f"[{label}] Cleaned up temporary clone.")

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_performance_benchmark(target: str, is_local_dir: bool = False) -> BenchmarkResult:
    """
    Normal benchmark: uses the default worker / chunk-size heuristics
    (80 % of available cores, auto-calculated IPC chunk size).
    """
    os.environ.pop("LEGACYMCP_MAX_WORKERS", None)
    os.environ.pop("LEGACYMCP_CHUNK_SIZE", None)

    result = _run_benchmark("Normal", target, is_local_dir=is_local_dir)
    _print_result(result)
    return result


def run_constrained_benchmark(
    target: str,
    *,
    max_workers: int = 2,
    chunk_size_override: int = 5,
    is_local_dir: bool = False,
) -> BenchmarkResult:
    """
    Constrained benchmark: caps parallelism and chunk size to simulate
    low-spec environments (shared hosting, 1-2 vCPU containers).

    Uses the LEGACYMCP_MAX_WORKERS / LEGACYMCP_CHUNK_SIZE env-var overrides
    in helpers.py — no monkey-patching, no production code changes required.

    Args:
        target:              Git URL or local directory path.
        max_workers:         Hard cap on ProcessPoolExecutor worker count.
        chunk_size_override: Fixed IPC chunk size (files per batch).
        is_local_dir:        If True, skip git clone and use target as local path.
    """
    os.environ["LEGACYMCP_MAX_WORKERS"] = str(max_workers)
    os.environ["LEGACYMCP_CHUNK_SIZE"] = str(chunk_size_override)

    label = f"Constrained(workers={max_workers}, chunk={chunk_size_override})"
    try:
        result = _run_benchmark(label, target, is_local_dir=is_local_dir)
        result.max_workers = max_workers
        result.chunk_size = chunk_size_override
    finally:
        os.environ.pop("LEGACYMCP_MAX_WORKERS", None)
        os.environ.pop("LEGACYMCP_CHUNK_SIZE", None)

    _print_result(result)
    return result


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

def _print_result(r: BenchmarkResult) -> None:
    logger.info(f"--- [{r.label}] Summary ---")
    if r.error:
        logger.error(f"  Error: {r.error}")
        return
    logger.info(f"  Target        : {r.target}")
    logger.info(f"  Files Parsed  : {r.files_parsed}")
    logger.info(f"  Files Skipped : {r.files_skipped}")
    logger.info(f"  Total Nodes   : {r.node_count}")
    logger.info(f"  Clone Time    : {r.clone_duration:.3f}s")
    logger.info(f"  Parse/Graph   : {r.build_duration:.3f}s")
    logger.info(f"  Total Time    : {r.total_duration:.3f}s")
    if r.speed > 0:
        logger.info(f"  Speed         : {r.speed:.2f} files/sec")
    if r.max_workers is not None:
        logger.info(f"  Workers Cap   : {r.max_workers}")
    if r.chunk_size is not None:
        logger.info(f"  Chunk Size    : {r.chunk_size}")


def _print_comparison(normal: BenchmarkResult, constrained: BenchmarkResult) -> None:
    """Print a side-by-side recommendation table to guide tuning of defaults."""
    sep = "-" * 60
    print(f"\n{sep}")
    print(f"{'Metric':<24} {'Normal':>16} {'Constrained':>16}")
    print(sep)

    rows = [
        ("Files parsed",     str(normal.files_parsed),       str(constrained.files_parsed)),
        ("Total nodes",      str(normal.node_count),          str(constrained.node_count)),
        ("Build time (s)",   f"{normal.build_duration:.3f}",  f"{constrained.build_duration:.3f}"),
        ("Speed (files/s)",  f"{normal.speed:.2f}",           f"{constrained.speed:.2f}"),
        ("Workers",          "auto",                           str(constrained.max_workers)),
        ("Chunk size",       "auto",                           str(constrained.chunk_size)),
    ]
    for metric, nval, cval in rows:
        print(f"{metric:<24} {nval:>16} {cval:>16}")

    print(sep)

    if constrained.speed > 0 and normal.speed > 0:
        ratio = normal.speed / constrained.speed
        print(f"\n  Throughput ratio (normal / constrained): {ratio:.2f}x")
        if ratio < 1.3:
            print(
                f"  Recommendation: constrained defaults are nearly as fast.\n"
                f"  Safe to ship LEGACYMCP_MAX_WORKERS={constrained.max_workers}, "
                f"LEGACYMCP_CHUNK_SIZE={constrained.chunk_size} as low-spec defaults."
            )
        elif ratio < 2.5:
            print(
                "  Recommendation: notable slowdown under constraints.\n"
                "  Consider raising max_workers to 4 on production hosts."
            )
        else:
            print(
                "  Recommendation: severe throughput loss under constraints.\n"
                "  Increase max_workers or chunk_size for acceptable performance."
            )
    print(sep + "\n")


# ---------------------------------------------------------------------------
# __main__ — runs both profiles and prints a comparison table
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # ── Configuration ──────────────────────────────────────────────
    local_target = os.environ.get("LEGACYMCP_BENCHMARK_LOCAL_DIR")
    USE_LOCAL_DIR = bool(local_target)
    TARGET = local_target or "https://github.com/nlohmann/json"

    # ── Profile 1: normal ──────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("PROFILE 1: Normal (default heuristics)")
    logger.info("=" * 60)
    normal_result = run_performance_benchmark(TARGET, is_local_dir=USE_LOCAL_DIR)

    # ── Profile 2: constrained (2 workers, chunk_size=5) ──────────
    logger.info("=" * 60)
    logger.info("PROFILE 2: Constrained (2 workers, chunk_size=5)")
    logger.info("=" * 60)
    constrained_result = run_constrained_benchmark(
        TARGET,
        max_workers=2,
        chunk_size_override=5,
        is_local_dir=USE_LOCAL_DIR,
    )

    # ── Comparison & recommendation ────────────────────────────────
    _print_comparison(normal_result, constrained_result)
