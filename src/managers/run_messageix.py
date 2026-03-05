#!/usr/bin/env python3
"""
run_messageix.py — Standalone MESSAGEix solver script.

Invoked as a subprocess by SolverWorker.  Accepts CLI arguments, loads the
input Excel file into a temporary ixmp Platform, solves with the requested
LP solver, writes the results to an Excel file, and prints the result file
path so the parent process can pick it up.

Output line conventions (parsed by SolverWorker)::

    [RESULT_FILE] <absolute-path>   — path to the generated results Excel file
    [ERROR] <message>               — fatal error (also written to stderr)
    All other lines                 — forwarded verbatim to the console

Exit codes:
    0 — success
    1 — failure (error messages already printed)
"""

import argparse
import os
import shutil
import sys
import tempfile

# ---------------------------------------------------------------------------
# Make project's src/ directory importable when run as a standalone script
# ---------------------------------------------------------------------------
_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)


# ---------------------------------------------------------------------------
# Environment setup — must happen before ixmp/jpype are imported
# ---------------------------------------------------------------------------

def _setup_environment() -> bool:
    """
    Configure environment variables required by ixmp/GAMS before any imports.

    Returns True on success, False if a fatal prerequisite is missing.
    """
    # ------------------------------------------------------------------
    # 1. JVM — JPype 1.6+ requires Java 11+; org.jpype.jar is v55 bytecode.
    #    If JAVA_HOME is not set, try to auto-detect an installed JDK 11+.
    # ------------------------------------------------------------------
    if not os.environ.get("JAVA_HOME"):
        java_home = _find_java_home()
        if java_home:
            os.environ["JAVA_HOME"] = java_home
            print(f"Set JAVA_HOME={java_home}", flush=True)

    try:
        import jpype
        jvmpath = jpype.getDefaultJVMPath()
        print(f"JVM found: {jvmpath}", flush=True)
    except Exception:
        java_home = os.environ.get("JAVA_HOME", "(not set)")
        print("[ERROR] No Java Virtual Machine (JVM) found.", flush=True)
        print(f"[ERROR] JAVA_HOME={java_home}", flush=True)
        print("[ERROR] JPype 1.6+ requires Java 11 or newer.", flush=True)
        print(r"[ERROR] Install Java 11+ and set JAVA_HOME, e.g.:", flush=True)
        print(r"[ERROR]   setx JAVA_HOME C:\Program Files\Java\jdk-25", flush=True)
        print("[ERROR] Download from: https://adoptium.net/", flush=True)
        return False

    # ------------------------------------------------------------------
    # 2. GAMS path — ixmp uses IXMP_GAMS_PATH to locate the GAMS exe.
    #    If GAMS is not on PATH, try GAMSDIR env var or known locations.
    # ------------------------------------------------------------------
    if not os.environ.get("IXMP_GAMS_PATH"):
        gams_dir = _find_gams_dir()
        if gams_dir:
            os.environ["IXMP_GAMS_PATH"] = gams_dir
            print(f"Set IXMP_GAMS_PATH={gams_dir}", flush=True)
        else:
            print("[ERROR] GAMS installation not found.", flush=True)
            print("[ERROR] Set GAMSDIR environment variable to the GAMS directory.", flush=True)
            return False

    return True


def _find_java_home() -> str:
    """
    Auto-detect a Java 11+ installation and return its home directory.

    Searches common Windows paths.  Returns empty string when not found.
    """
    import glob as _glob

    candidates: list[str] = []

    # Standard Windows JDK locations (Oracle, Eclipse Adoptium, Microsoft, etc.)
    for base in (
        r"C:\Program Files\Java",
        r"C:\Program Files\Eclipse Adoptium",
        r"C:\Program Files\Microsoft",
        r"C:\Program Files\Zulu",
        r"C:\Program Files\BellSoft",
    ):
        if os.path.isdir(base):
            for entry in os.listdir(base):
                full = os.path.join(base, entry)
                jvm = os.path.join(full, "bin", "server", "jvm.dll")
                if os.path.isfile(jvm):
                    candidates.append(full)

    if not candidates:
        return ""

    # Prefer highest version number — sort directories by name descending.
    def _version_key(path: str) -> tuple:
        import re
        nums = re.findall(r"\d+", os.path.basename(path))
        return tuple(int(n) for n in nums)

    candidates.sort(key=_version_key, reverse=True)
    return candidates[0]


def _find_gams_dir() -> str:
    """Return the GAMS system directory, or empty string if not found."""
    # Already on PATH?
    if shutil.which("gams"):
        import pathlib
        return str(pathlib.Path(shutil.which("gams")).parent)

    # GAMSDIR environment variable
    gams_dir = os.environ.get("GAMSDIR", "")
    if gams_dir:
        for exe in ("gams.exe", "gams"):
            if os.path.isfile(os.path.join(gams_dir, exe)):
                return gams_dir

    # Common Windows installation paths (GAMS 35–50)
    for base in (r"C:\GAMS", r"C:\bin\GAMS"):
        if os.path.isdir(base):
            for entry in sorted(os.listdir(base), reverse=True):
                candidate = os.path.join(base, entry)
                if os.path.isfile(os.path.join(candidate, "gams.exe")):
                    return candidate

    return ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log(msg: str) -> None:
    """Print a plain console line (forwarded to SolverWorker.output_line)."""
    print(msg, flush=True)


def _error(msg: str) -> None:
    """Print a fatal error line; also echoed to stderr."""
    print(f"[ERROR] {msg}", flush=True)
    print(f"[ERROR] {msg}", file=sys.stderr, flush=True)


def _result_file(path: str) -> None:
    """Announce the result file path to the parent process."""
    print(f"[RESULT_FILE] {path}", flush=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """Run MESSAGEix solve pipeline.  Returns 0 on success, 1 on failure."""

    # Environment must be configured before ixmp/jpype are imported.
    if not _setup_environment():
        return 1

    parser = argparse.ArgumentParser(
        description="Run MESSAGEix solver on an input Excel file."
    )
    parser.add_argument("--input",       required=True,  help="Input Excel file path")
    parser.add_argument("--solver",      default="glpk", help="LP solver: glpk | cplex | gurobi")
    parser.add_argument("--model",       default="MESSAGEix", help="MESSAGEix model name")
    parser.add_argument("--scenario",    default="base", help="MESSAGEix scenario name")
    parser.add_argument("--output-dir",  default=None,   help="Directory for the results Excel file")
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Validate input file
    # ------------------------------------------------------------------
    if not os.path.isfile(args.input):
        _error(f"Input file not found: {args.input}")
        return 1

    output_dir = args.output_dir or os.path.dirname(os.path.abspath(args.input))
    os.makedirs(output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Import ixmp / message_ix
    # ------------------------------------------------------------------
    _log("Importing ixmp and message_ix...")
    try:
        import ixmp        # noqa: F401 — verified importable before use below
        import message_ix  # noqa: F401
    except ImportError as exc:
        _error(f"Cannot import ixmp / message_ix: {exc}")
        _error("Install with: pip install message-ix")
        return 1

    # ------------------------------------------------------------------
    # Create a temporary local ixmp Platform (HSQLDB in a temp directory)
    # ------------------------------------------------------------------
    tmp_dir = tempfile.mkdtemp(prefix="messageix_run_")
    _log(f"Using temporary ixmp platform directory: {tmp_dir}")

    try:
        db_url = f"jdbc:hsqldb:file:{tmp_dir}/ixmpdb"
        _log("Initialising ixmp platform (requires Java 11+)...")
        try:
            platform = ixmp.Platform(backend="jdbc", driver="hsqldb", url=db_url)
        except Exception as exc:
            err = str(exc)
            _error(f"Failed to create ixmp platform: {exc}")
            # Give a targeted hint for the most common failure modes.
            if "org.jpype.jar" in err or "UnsupportedClassVersion" in err \
                    or "older than required" in err:
                _error("JPype could not load its Java support library.")
                _error("This usually means Java 8 is still active as the default JVM.")
                _error("Set JAVA_HOME to your Java 11+ installation directory, e.g.:")
                _error(r"  set JAVA_HOME=C:\Program Files\Java\jdk-25")
            else:
                _error("Ensure Java 11+ is installed and JAVA_HOME points to it.")
            return 1

        # ------------------------------------------------------------------
        # Load scenario from Excel via ScenarioLoader
        # ------------------------------------------------------------------
        _log("Loading scenario from input Excel...")
        try:
            from managers.scenario_loader import ScenarioLoader
            scenario = ScenarioLoader.load_from_excel(
                platform=platform,
                input_file=args.input,
                model_name=args.model,
                scenario_name=args.scenario,
                log_fn=_log,
            )
        except Exception as exc:
            _error(f"Failed to load scenario from Excel: {exc}")
            return 1

        # ------------------------------------------------------------------
        # Solve
        # ------------------------------------------------------------------
        from managers.solver_manager import SolverManager
        solve_options = SolverManager.SOLVER_OPTIONS.get(args.solver, {})

        _log(f"Solving with {args.solver.upper()} (model=MESSAGE)...")
        try:
            scenario.solve(model="MESSAGE", solve_options=solve_options)
        except Exception as exc:
            _error(f"Solver failed: {exc}")
            return 1

        _log("Solve complete.  Checking solution status...")

        # ------------------------------------------------------------------
        # Export results to Excel
        # ------------------------------------------------------------------
        _log("Exporting results to Excel...")
        input_stem = os.path.splitext(os.path.basename(args.input))[0]
        output_path = os.path.join(output_dir, f"{input_stem}_results.xlsx")

        try:
            from managers.results_exporter import ResultsExporter
            ResultsExporter.export_to_excel(scenario, output_path, log_fn=_log)
        except Exception as exc:
            _error(f"Failed to export results: {exc}")
            return 1

        _log(f"Results written to: {output_path}")

        # Announce result file to parent process (SolverWorker will capture this)
        _result_file(output_path)

    finally:
        try:
            platform.close()
        except Exception:
            pass
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return 0


def _install_jpype_teardown_filter() -> None:
    """
    Override sys.unraisablehook to swallow the AttributeError that ixmp's
    JDBCBackend.__del__ raises during Python shutdown when the JPype JVM has
    already been torn down ('NoneType' has no attribute 'IxException').

    All other unraisable exceptions are forwarded to the default handler so
    real errors are not silently discarded.
    """
    default_hook = getattr(sys, "__unraisablehook__", None)

    def _hook(args):  # args: sys.UnraisableHookArgs
        if (
            args.exc_type is AttributeError
            and "IxException" in str(args.exc_value)
        ):
            return  # suppress known JPype/JVM teardown noise
        if default_hook is not None:
            default_hook(args)
        else:
            sys.__unraisablehook__(args)  # type: ignore[attr-defined]

    sys.unraisablehook = _hook  # type: ignore[attr-defined]


if __name__ == "__main__":
    _install_jpype_teardown_filter()
    sys.exit(main())
