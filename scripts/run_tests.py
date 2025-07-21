#!/usr/bin/env python3
"""
Test runner for AI Engine components
"""
import os
import sys
import subprocess
import argparse

def run_tests(test_type="all", verbose=False, coverage=False):
    """Run tests with specified options"""
    
    # Add project root to Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    
    # Add coverage
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])
    
    # Select test files based on type
    if test_type == "all":
        cmd.append("tests/")
    elif test_type == "unit":
        cmd.extend([
            "tests/test_cost_optimizer.py",
            "tests/test_risk_manager.py", 
            "tests/test_learning_system.py"
        ])
    elif test_type == "integration":
        cmd.append("tests/test_ai_engine_integration.py")
    elif test_type == "existing":
        cmd.extend([
            "tests/test_ai_engine.py",
            "tests/test_auth.py",
            "tests/test_database.py",
            "tests/test_portfolio.py"
        ])
    else:
        cmd.append(f"tests/test_{test_type}.py")
    
    # Add markers for async tests
    cmd.extend(["-m", "not slow"])
    
    print(f"Running command: {' '.join(cmd)}")
    print(f"Working directory: {project_root}")
    
    # Run tests
    try:
        result = subprocess.run(cmd, cwd=project_root, check=False)
        return result.returncode
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description="Run AI Engine tests")
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "existing", "cost_optimizer", "risk_manager", "learning_system"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", "-c", action="store_true", help="Generate coverage report")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("AI Engine Test Runner")
    print("=" * 60)
    print(f"Test type: {args.type}")
    print(f"Verbose: {args.verbose}")
    print(f"Coverage: {args.coverage}")
    print("=" * 60)
    
    exit_code = run_tests(args.type, args.verbose, args.coverage)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code: {exit_code}")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())