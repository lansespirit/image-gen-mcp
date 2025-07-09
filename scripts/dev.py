#!/usr/bin/env python3
"""Development script for the Image Gen MCP Server."""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path


def setup_env():
    """Set up development environment."""
    print("🔧 Setting up development environment...")
    
    # Create .env file if it doesn't exist
    env_file = Path(".env")
    if not env_file.exists():
        print("📝 Creating .env file from example...")
        example_file = Path(".env.example")
        if example_file.exists():
            env_file.write_text(example_file.read_text())
            print("✅ Created .env file. Please edit it with your OpenAI API key.")
        else:
            env_file.write_text("OPENAI_API_KEY=your-api-key-here\n")
            print("✅ Created basic .env file. Please add your OpenAI API key.")
    
    # Create storage directories
    storage_path = Path("storage")
    storage_path.mkdir(exist_ok=True)
    (storage_path / "images").mkdir(exist_ok=True)
    (storage_path / "cache").mkdir(exist_ok=True)
    (storage_path / "logs").mkdir(exist_ok=True)
    print("✅ Created storage directories")


def run_tests():
    """Run the test suite."""
    print("🧪 Running tests...")
    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "tests/", "-v"],
            check=False,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ pytest not found. Install with: uv add --dev pytest")
        return False


def run_server():
    """Run the MCP server in development mode."""
    print("🚀 Starting Image Gen MCP Server...")
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set")
        print("   Please set it in your .env file or environment")
        return False
    
    try:
        subprocess.run(
            ["uv", "run", "python", "-m", "gpt_image_mcp.server"],
            check=True
        )
        return True
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")
        return False


def run_example():
    """Run the basic usage example."""
    print("📖 Running basic usage example...")
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set")
        print("   Please set it in your .env file or environment")
        return False
    
    try:
        subprocess.run(
            ["uv", "run", "python", "examples/basic_usage.py"],
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Example failed: {e}")
        return False


def lint_code():
    """Run code linting."""
    print("🔍 Running code linting...")
    
    # Run ruff
    try:
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "gpt_image_mcp/"],
            check=False,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ No linting issues found")
        else:
            print(f"⚠️  Found {result.returncode} linting issues")
        
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ ruff not found. Install with: uv add --dev ruff")
        return False


def format_code():
    """Format code with black."""
    print("🎨 Formatting code...")
    
    try:
        subprocess.run(
            ["uv", "run", "black", "gpt_image_mcp/", "tests/", "examples/"],
            check=True
        )
        print("✅ Code formatted successfully")
        return True
    except FileNotFoundError:
        print("❌ black not found. Install with: uv add --dev black")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Formatting failed: {e}")
        return False


def check_dependencies():
    """Check if all dependencies are installed."""
    print("📦 Checking dependencies...")
    
    try:
        result = subprocess.run(
            ["uv", "pip", "check"],
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ All dependencies are satisfied")
        else:
            print("❌ Dependency issues found:")
            print(result.stdout)
            print(result.stderr)
        
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ uv not found. Please install uv first")
        return False


def main():
    """Main development script."""
    parser = argparse.ArgumentParser(description="Image Gen MCP Server Development Tools")
    parser.add_argument(
        "command",
        choices=["setup", "test", "server", "example", "lint", "format", "check"],
        help="Command to run"
    )
    
    args = parser.parse_args()
    
    if args.command == "setup":
        success = True
        success &= check_dependencies()
        setup_env()
        
    elif args.command == "test":
        success = run_tests()
        
    elif args.command == "server":
        success = run_server()
        
    elif args.command == "example":
        success = run_example()
        
    elif args.command == "lint":
        success = lint_code()
        
    elif args.command == "format":
        success = format_code()
        
    elif args.command == "check":
        success = check_dependencies()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()