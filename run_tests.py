#!/usr/bin/env python3
"""
Test runner script for the ODAI API project.

This script provides convenient ways to run tests with different options.
"""

import sys
import subprocess
import argparse
import os
import shutil
from pathlib import Path


def get_python_executable():
    """Get the appropriate Python executable to use.
    
    Searches for Python executable in the following order:
    1. Virtual environment (env_odai_backend, env_odai_runner, venv, .venv)
    2. System python3 or python
    3. Fallback to sys.executable
    
    Returns:
        str: Path to the Python executable
    """
    # First check if we're in a virtual environment
    venv_paths = [
        Path("env_odai_backend/bin/python"),
        Path("env_odai_runner/bin/python"),
        Path("venv/bin/python"),
        Path(".venv/bin/python")
    ]

    for venv_path in venv_paths:
        if venv_path.exists():
            return str(venv_path.absolute())

    # Fall back to system python
    python_candidates = ["python3", "python"]
    for candidate in python_candidates:
        if shutil.which(candidate):
            return candidate

    # Last resort - use sys.executable but warn the user
    print("⚠️  Warning: Using sys.executable as fallback")
    return sys.executable


def run_command(cmd: list, description: str, env=None) -> bool:
    """Run a command and return success status.
    
    Args:
        cmd: List of command arguments to execute
        description: Human-readable description of the command
        env: Optional environment variables dictionary
        
    Returns:
        bool: True if command succeeded, False otherwise
    """
    print(f"\n🔄 {description}")
    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False, env=env)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        print("Make sure you have installed the test dependencies:")
        print("  pip install -r test_requirements.txt")
        return False


def main():
    """Main entry point for the test runner.
    
    Parses command line arguments and runs pytest with appropriate options.
    Supports coverage reporting, parallel execution, and filtering by file.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Run tests for the ODAI API project")
    parser.add_argument(
        "--file",
        "-f",
        help="Run tests for a specific file (e.g., auth_service)",
        default=""
    )
    parser.add_argument(
        "--coverage",
        "-c",
        action="store_true",
        help="Run tests with coverage report"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Run tests in verbose mode"
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies first"
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=1,
        help="Number of workers for parallel test execution (default: 16, use 0 to disable)"
    )

    args = parser.parse_args()

    # Get the appropriate Python executable
    python_executable = get_python_executable()
    print(f"📍 Using Python executable: {python_executable}")

    # Install dependencies if requested
    if args.install_deps:
        if not run_command(
            [python_executable, "-m", "pip", "install",
                "-r", "test_requirements.txt"],
            "Installing test dependencies",
            env=None
        ):
            return 1

    # Build the pytest command with PYTHONPATH and suppress warnings
    env = os.environ.copy()
    env['PYTHONPATH'] = '.'
    env['PYTHONWARNINGS'] = 'ignore'

    cmd = [python_executable, "-m", "pytest", "--disable-warnings"]

    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    # Add parallel execution if workers > 0
    if args.workers > 0:
        cmd.extend(["-n", str(args.workers)])
        print(f"🚀 Running tests in parallel with {args.workers} workers")
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend(["--cov=.", 
                   "--cov-config=.coveragerc",
                   "--cov-report=html", "--cov-report=term"])

    # Add specific file if provided
    if args.file:
        test_file = f"tests/test_{args.file}.py"
        if Path(test_file).exists():
            cmd.append(test_file)
        else:
            print(f"❌ Test file not found: {test_file}")
            return 1
    else:
        cmd.append("tests/")

    # Run the tests
    success = run_command(cmd, "Running tests", env=env)

    if args.coverage and success:
        print("\n📊 Coverage report generated in htmlcov/index.html")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
