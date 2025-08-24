#!/usr/bin/env python3
"""
Test runner script for the Review Gap Analyzer backend.
Provides convenient commands for running different types of tests.
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=False)
    return result.returncode == 0


def run_unit_tests(coverage=False, verbose=False):
    """Run unit tests."""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "not integration and not e2e"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term-missing"])
    
    return run_command(cmd)


def run_integration_tests(verbose=False):
    """Run integration tests."""
    cmd = ["python", "-m", "pytest", "tests/integration/", "-m", "integration"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd)


def run_e2e_tests(verbose=False):
    """Run end-to-end tests."""
    cmd = ["python", "-m", "pytest", "tests/e2e/", "-m", "e2e"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd)


def run_specific_tests(pattern, verbose=False):
    """Run tests matching a specific pattern."""
    cmd = ["python", "-m", "pytest", "-k", pattern]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd)


def run_linting():
    """Run code linting."""
    print("Running flake8...")
    flake8_success = run_command([
        "python", "-m", "flake8", "app", "tests", 
        "--max-line-length=100", "--exclude=migrations"
    ])
    
    print("Running black...")
    black_success = run_command([
        "python", "-m", "black", "--check", "app", "tests"
    ])
    
    print("Running isort...")
    isort_success = run_command([
        "python", "-m", "isort", "--check-only", "app", "tests"
    ])
    
    return flake8_success and black_success and isort_success


def run_type_checking():
    """Run type checking with mypy."""
    return run_command([
        "python", "-m", "mypy", "app", "--ignore-missing-imports"
    ])


def run_all_tests(coverage=False, verbose=False):
    """Run all tests."""
    print("Running all tests...")
    
    success = True
    
    print("\n=== Running Unit Tests ===")
    success &= run_unit_tests(coverage=coverage, verbose=verbose)
    
    print("\n=== Running Integration Tests ===")
    success &= run_integration_tests(verbose=verbose)
    
    print("\n=== Running End-to-End Tests ===")
    success &= run_e2e_tests(verbose=verbose)
    
    return success


def run_quality_checks():
    """Run all quality checks."""
    print("Running quality checks...")
    
    success = True
    
    print("\n=== Running Linting ===")
    success &= run_linting()
    
    print("\n=== Running Type Checking ===")
    success &= run_type_checking()
    
    return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test runner for Review Gap Analyzer backend")
    parser.add_argument(
        "command",
        choices=[
            "unit", "integration", "e2e", "all", "lint", "type-check", 
            "quality", "specific", "coverage"
        ],
        help="Type of tests to run"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-k", "--pattern", help="Pattern for specific tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    
    args = parser.parse_args()
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    success = True
    
    if args.command == "unit":
        success = run_unit_tests(coverage=args.coverage, verbose=args.verbose)
    elif args.command == "integration":
        success = run_integration_tests(verbose=args.verbose)
    elif args.command == "e2e":
        success = run_e2e_tests(verbose=args.verbose)
    elif args.command == "all":
        success = run_all_tests(coverage=args.coverage, verbose=args.verbose)
    elif args.command == "lint":
        success = run_linting()
    elif args.command == "type-check":
        success = run_type_checking()
    elif args.command == "quality":
        success = run_quality_checks()
    elif args.command == "specific":
        if not args.pattern:
            print("Error: --pattern is required for specific tests")
            sys.exit(1)
        success = run_specific_tests(args.pattern, verbose=args.verbose)
    elif args.command == "coverage":
        success = run_unit_tests(coverage=True, verbose=args.verbose)
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()