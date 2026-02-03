#!/usr/bin/env python3
"""
Marlowe-to-Move Compiler CLI

Command-line interface for generating Move smart contracts from Marlowe specs.
"""

import argparse
import json
import os
import sys
from typing import Optional

# Rich for beautiful terminal output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.syntax import Syntax
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' not installed. Install with: pip install rich")

# Local imports
from parser import parse_contract
from fsm_model import parse_contract_to_infos
from move_generator import generate_module, build_stage_lookup, generate_test_module
from ts_generator import generate_ts_sdk

# Path setup
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
SPECS_DIR = os.path.join(ROOT_DIR, "specs")
CONTRACT_DIR = os.path.join(ROOT_DIR, "contract")
SDK_DIR = os.path.join(ROOT_DIR, "sdk")
DEPLOYMENT_FILE = os.path.join(ROOT_DIR, "deployments", "deployment.json")

console = Console() if RICH_AVAILABLE else None


def get_specs() -> list[str]:
    """Get list of available spec files."""
    if not os.path.exists(SPECS_DIR):
        return []
    return [f for f in os.listdir(SPECS_DIR) 
            if f.endswith(".json") and f != "test.json"]


def print_success(msg: str):
    if RICH_AVAILABLE:
        console.print(f"[green]✓[/green] {msg}")
    else:
        print(f"✓ {msg}")


def print_error(msg: str):
    if RICH_AVAILABLE:
        console.print(f"[red]✗[/red] {msg}")
    else:
        print(f"✗ {msg}")


def print_info(msg: str):
    if RICH_AVAILABLE:
        console.print(f"[blue]ℹ[/blue] {msg}")
    else:
        print(f"ℹ {msg}")


def cmd_list(args):
    """List available spec files."""
    specs = get_specs()
    
    if not specs:
        print_error("No spec files found in specs/ directory")
        return 1
    
    if RICH_AVAILABLE:
        table = Table(title="Available Specs")
        table.add_column("Name", style="cyan")
        table.add_column("File", style="dim")
        table.add_column("Size", justify="right")
        
        for spec in specs:
            path = os.path.join(SPECS_DIR, spec)
            size = os.path.getsize(path)
            name = os.path.splitext(spec)[0]
            table.add_row(name, spec, f"{size} bytes")
        
        console.print(table)
    else:
        print("Available Specs:")
        print("-" * 40)
        for spec in specs:
            name = os.path.splitext(spec)[0]
            print(f"  • {name}")
    
    return 0


def cmd_validate(args):
    """Validate a spec file."""
    specs = get_specs()
    
    if args.spec:
        target_specs = [f"{args.spec}.json" if not args.spec.endswith('.json') else args.spec]
    else:
        target_specs = specs
    
    success_count = 0
    fail_count = 0
    
    for spec in target_specs:
        if spec not in specs:
            print_error(f"Spec '{spec}' not found")
            fail_count += 1
            continue
        
        json_path = os.path.join(SPECS_DIR, spec)
        name = os.path.splitext(spec)[0]
        
        try:
            with open(json_path, "r") as f:
                json_data = json.load(f)
            
            # Try parsing
            contract_ast = parse_contract(json_data)
            (infos, _) = parse_contract_to_infos(contract_ast, stage=0)
            
            print_success(f"{name}: Valid ({len(infos)} stages)")
            success_count += 1
            
        except json.JSONDecodeError as e:
            print_error(f"{name}: Invalid JSON - {e}")
            fail_count += 1
        except Exception as e:
            print_error(f"{name}: Parse error - {e}")
            fail_count += 1
    
    print()
    print_info(f"Results: {success_count} valid, {fail_count} invalid")
    return 0 if fail_count == 0 else 1


def build_single_spec(spec_file: str, output_dir: Optional[str] = None) -> bool:
    """Build a single spec file."""
    module_name = os.path.splitext(spec_file)[0]
    json_path = os.path.join(SPECS_DIR, spec_file)
    
    try:
        # Parse
        with open(json_path, "r") as f:
            json_data = json.load(f)
        
        contract_ast = parse_contract(json_data)
        (infos, _) = parse_contract_to_infos(contract_ast, stage=0)
        stage_lookup = build_stage_lookup(infos)
        
        # Generate Move
        move_code = generate_module(infos, stage_lookup, module_name=module_name)
        output_path = os.path.join(output_dir or CONTRACT_DIR, "sources", f"{module_name}.move")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(move_code)
        
        # Generate Tests
        test_code = generate_test_module(infos, package_name=module_name)
        test_path = os.path.join(output_dir or CONTRACT_DIR, "tests", f"{module_name}_tests.move")
        os.makedirs(os.path.dirname(test_path), exist_ok=True)
        with open(test_path, "w") as f:
            f.write(test_code)
        
        # Generate TypeScript SDK
        ts_code = generate_ts_sdk(infos, deployment_path=DEPLOYMENT_FILE, module_name=module_name)
        ts_path = os.path.join(SDK_DIR, f"{module_name}_sdk.ts")
        os.makedirs(os.path.dirname(ts_path), exist_ok=True)
        with open(ts_path, "w") as f:
            f.write(ts_code)
        
        return True
        
    except Exception as e:
        print_error(f"Build failed for {module_name}: {e}")
        return False


def cmd_build(args):
    """Build Move contracts from specs."""
    specs = get_specs()
    
    if args.spec:
        target_file = f"{args.spec}.json" if not args.spec.endswith('.json') else args.spec
        if target_file not in specs:
            print_error(f"Spec '{args.spec}' not found")
            return 1
        target_specs = [target_file]
    else:
        target_specs = specs
    
    if not target_specs:
        print_error("No specs to build")
        return 1
    
    success_count = 0
    fail_count = 0
    
    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("Building specs...", total=len(target_specs))
            
            for spec in target_specs:
                name = os.path.splitext(spec)[0]
                progress.update(task, description=f"Building {name}...")
                
                if build_single_spec(spec, args.output):
                    print_success(f"Built {name}")
                    success_count += 1
                else:
                    fail_count += 1
                
                progress.advance(task)
    else:
        for spec in target_specs:
            name = os.path.splitext(spec)[0]
            print(f"Building {name}...")
            
            if build_single_spec(spec, args.output):
                print_success(f"Built {name}")
                success_count += 1
            else:
                fail_count += 1
    
    print()
    print_info(f"Build complete: {success_count} succeeded, {fail_count} failed")
    return 0 if fail_count == 0 else 1


def cmd_deploy(args):
    """Deploy contract to Sui network."""
    import subprocess
    
    print_info("Starting deployment to Sui network...")
    
    try:
        result = subprocess.run(
            ["sui", "client", "publish", "--gas-budget", "100000000", "--json", "--skip-dependency-verification"],
            cwd=CONTRACT_DIR,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_error(f"Deployment failed: {result.stderr}")
            return 1
        
        data = json.loads(result.stdout)
        
        # Parse output
        package_id = None
        contract_id = None
        upgrade_cap_id = None
        
        if "objectChanges" in data:
            for change in data["objectChanges"]:
                if change["type"] == "published":
                    package_id = change["packageId"]
                elif change["type"] == "created":
                    obj_type = change["objectType"]
                    if "::Contract" in obj_type:
                        contract_id = change["objectId"]
                    if "::package::UpgradeCap" in obj_type:
                        upgrade_cap_id = change["objectId"]
        
        if not package_id:
            print_error("Failed to find Package ID in output")
            return 1
        
        print_success("Deployment successful!")
        
        if RICH_AVAILABLE:
            table = Table(title="Deployment Info")
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("Package ID", package_id)
            table.add_row("Contract ID", contract_id or "N/A")
            table.add_row("Upgrade Cap ID", upgrade_cap_id or "N/A")
            console.print(table)
        else:
            print(f"  Package ID: {package_id}")
            print(f"  Contract ID: {contract_id or 'N/A'}")
            print(f"  Upgrade Cap ID: {upgrade_cap_id or 'N/A'}")
        
        # Save deployment info
        deployment_info = {
            "package_id": package_id,
            "contract_id": contract_id,
            "upgrade_cap_id": upgrade_cap_id,
            "network": "testnet",
            "digest": data.get("digest", "")
        }
        
        os.makedirs(os.path.dirname(DEPLOYMENT_FILE), exist_ok=True)
        with open(DEPLOYMENT_FILE, "w") as f:
            json.dump(deployment_info, f, indent=2)
        
        print_info(f"Artifacts saved to {DEPLOYMENT_FILE}")
        
        # Regenerate SDKs
        print_info("Regenerating SDKs with new contract IDs...")
        cmd_build(argparse.Namespace(spec=None, output=None))
        
        return 0
        
    except FileNotFoundError:
        print_error("Sui CLI not found. Please install it first.")
        return 1
    except Exception as e:
        print_error(f"Deployment error: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        prog="marlowe-cli",
        description="Marlowe-to-Move Compiler CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                    List all available specs
  %(prog)s build                   Build all specs
  %(prog)s build --spec swap_ada   Build specific spec
  %(prog)s validate                Validate all specs
  %(prog)s deploy                  Deploy to Sui network
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available spec files")
    list_parser.set_defaults(func=cmd_list)
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate spec files")
    validate_parser.add_argument("--spec", "-s", help="Specific spec to validate")
    validate_parser.set_defaults(func=cmd_validate)
    
    # Build command
    build_parser = subparsers.add_parser("build", help="Build Move contracts from specs")
    build_parser.add_argument("--spec", "-s", help="Specific spec to build")
    build_parser.add_argument("--output", "-o", help="Output directory")
    build_parser.set_defaults(func=cmd_build)
    
    # Deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy to Sui network")
    deploy_parser.set_defaults(func=cmd_deploy)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
