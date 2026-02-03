#!/usr/bin/env python3
"""
Marlowe-to-Move Compiler TUI

Interactive Terminal User Interface using Textual.
"""

import os
import json
import asyncio
from typing import Optional

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical
    from textual.widgets import (
        Header, Footer, Static, ListView, ListItem, 
        Label, Button, Log, RichLog
    )
    from textual.binding import Binding
    from textual.reactive import reactive
    from rich.syntax import Syntax
    from rich.panel import Panel
except ImportError:
    print("Error: 'textual' is not installed.")
    print("Install with: pip install textual")
    exit(1)

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


def get_specs() -> list[str]:
    """Get list of available spec files."""
    if not os.path.exists(SPECS_DIR):
        return []
    return [f for f in os.listdir(SPECS_DIR) 
            if f.endswith(".json") and f != "test.json"]


CSS = """
Screen {
    background: $surface;
}

#main-container {
    layout: horizontal;
    height: 1fr;
}

#sidebar {
    width: 30;
    background: $panel;
    border: round $primary;
    padding: 1;
}

#sidebar-title {
    text-align: center;
    background: $primary;
    color: $text;
    padding: 0 1;
    margin-bottom: 1;
}

#spec-list {
    height: 1fr;
}

#content {
    width: 1fr;
    layout: vertical;
}

#preview-container {
    height: 2fr;
    border: round $secondary;
    padding: 1;
}

#preview-title {
    text-align: center;
    background: $secondary;
    color: $text;
    padding: 0 1;
    margin-bottom: 1;
}

#preview {
    height: 1fr;
    overflow: auto scroll;
}

#log-container {
    height: 1fr;
    border: round $accent;
    padding: 1;
}

#log-title {
    text-align: center;
    background: $accent;
    color: $text;
    padding: 0 1;
    margin-bottom: 1;
}

#log-panel {
    height: 1fr;
}

#action-bar {
    height: 3;
    layout: horizontal;
    align: center middle;
    padding: 0 2;
}

Button {
    margin: 0 1;
}

.selected-item {
    background: $primary;
}

ListItem {
    padding: 0 1;
}

ListItem:hover {
    background: $primary 30%;
}
"""


class SpecItem(ListItem):
    """A spec item in the list."""
    
    def __init__(self, spec_name: str) -> None:
        super().__init__()
        self.spec_name = spec_name
    
    def compose(self) -> ComposeResult:
        yield Label(f"📄 {self.spec_name}")


class MarloweCompilerApp(App):
    """Marlowe-to-Move Compiler TUI Application."""
    
    TITLE = "Marlowe → Move Compiler"
    CSS = CSS
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("b", "build", "Build"),
        Binding("v", "validate", "Validate"),
        Binding("d", "deploy", "Deploy"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "help", "Help"),
    ]
    
    selected_spec: reactive[Optional[str]] = reactive(None)
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Container(id="main-container"):
            with Vertical(id="sidebar"):
                yield Static("Specs", id="sidebar-title")
                yield ListView(id="spec-list")
            
            with Vertical(id="content"):
                with Vertical(id="preview-container"):
                    yield Static("Preview", id="preview-title")
                    yield Static("Select a spec to preview", id="preview")
                
                with Vertical(id="log-container"):
                    yield Static("Log", id="log-title")
                    yield RichLog(id="log-panel", highlight=True, markup=True)
        
        with Horizontal(id="action-bar"):
            yield Button("Build [b]", id="btn-build", variant="primary")
            yield Button("Validate [v]", id="btn-validate", variant="success")
            yield Button("Deploy [d]", id="btn-deploy", variant="warning")
            yield Button("Refresh [r]", id="btn-refresh", variant="default")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Load specs on mount."""
        self.load_specs()
        self.log_message("[bold green]Welcome to Marlowe Compiler![/]")
        self.log_message("Select a spec from the sidebar to preview.")
        self.log_message("Use keyboard shortcuts or buttons to perform actions.")
    
    def load_specs(self) -> None:
        """Load spec files into the list."""
        specs = get_specs()
        list_view = self.query_one("#spec-list", ListView)
        list_view.clear()
        
        for spec in specs:
            name = os.path.splitext(spec)[0]
            list_view.append(SpecItem(name))
        
        if not specs:
            self.log_message("[yellow]No specs found in specs/ directory[/]")
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle spec selection."""
        if isinstance(event.item, SpecItem):
            self.selected_spec = event.item.spec_name
            self.update_preview()
    
    def update_preview(self) -> None:
        """Update the preview panel with selected spec."""
        preview = self.query_one("#preview", Static)
        
        if not self.selected_spec:
            preview.update("Select a spec to preview")
            return
        
        spec_path = os.path.join(SPECS_DIR, f"{self.selected_spec}.json")
        
        try:
            with open(spec_path, "r") as f:
                content = f.read()
            
            syntax = Syntax(content, "json", theme="monokai", line_numbers=True)
            preview.update(syntax)
            
        except Exception as e:
            preview.update(f"[red]Error loading spec: {e}[/]")
    
    def log_message(self, message: str) -> None:
        """Add a message to the log panel."""
        log = self.query_one("#log-panel", RichLog)
        log.write(message)
    
    async def action_build(self) -> None:
        """Build the selected spec."""
        await self.do_build()
    
    async def action_validate(self) -> None:
        """Validate the selected spec."""
        await self.do_validate()
    
    async def action_deploy(self) -> None:
        """Deploy to Sui network."""
        await self.do_deploy()
    
    async def action_refresh(self) -> None:
        """Refresh the spec list."""
        self.load_specs()
        self.log_message("[blue]Spec list refreshed[/]")
    
    async def action_help(self) -> None:
        """Show help."""
        self.log_message("")
        self.log_message("[bold cyan]═══ Help ═══[/]")
        self.log_message("[b] Build    - Generate Move/TS code from selected spec")
        self.log_message("[v] Validate - Validate selected spec JSON")
        self.log_message("[d] Deploy   - Deploy contract to Sui network")
        self.log_message("[r] Refresh  - Reload spec list")
        self.log_message("[q] Quit     - Exit the application")
        self.log_message("")
    
    async def do_validate(self) -> None:
        """Validate the selected spec."""
        if not self.selected_spec:
            self.log_message("[yellow]Please select a spec first[/]")
            return
        
        spec_path = os.path.join(SPECS_DIR, f"{self.selected_spec}.json")
        self.log_message(f"[blue]Validating {self.selected_spec}...[/]")
        
        try:
            with open(spec_path, "r") as f:
                json_data = json.load(f)
            
            contract_ast = parse_contract(json_data)
            (infos, _) = parse_contract_to_infos(contract_ast, stage=0)
            
            self.log_message(f"[green]✓ {self.selected_spec} is valid ({len(infos)} stages)[/]")
            
        except json.JSONDecodeError as e:
            self.log_message(f"[red]✗ Invalid JSON: {e}[/]")
        except Exception as e:
            self.log_message(f"[red]✗ Parse error: {e}[/]")
    
    async def do_build(self) -> None:
        """Build the selected spec."""
        if not self.selected_spec:
            self.log_message("[yellow]Please select a spec first[/]")
            return
        
        spec_file = f"{self.selected_spec}.json"
        spec_path = os.path.join(SPECS_DIR, spec_file)
        
        self.log_message(f"[blue]Building {self.selected_spec}...[/]")
        
        try:
            # Parse
            with open(spec_path, "r") as f:
                json_data = json.load(f)
            
            contract_ast = parse_contract(json_data)
            (infos, _) = parse_contract_to_infos(contract_ast, stage=0)
            stage_lookup = build_stage_lookup(infos)
            
            self.log_message(f"  Parsed: {len(infos)} stages")
            
            # Generate Move
            move_code = generate_module(infos, stage_lookup, module_name=self.selected_spec)
            output_path = os.path.join(CONTRACT_DIR, "sources", f"{self.selected_spec}.move")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w") as f:
                f.write(move_code)
            self.log_message(f"  Move: [dim]{output_path}[/]")
            
            # Generate Tests
            test_code = generate_test_module(infos, package_name=self.selected_spec)
            test_path = os.path.join(CONTRACT_DIR, "tests", f"{self.selected_spec}_tests.move")
            os.makedirs(os.path.dirname(test_path), exist_ok=True)
            with open(test_path, "w") as f:
                f.write(test_code)
            self.log_message(f"  Tests: [dim]{test_path}[/]")
            
            # Generate TypeScript SDK
            ts_code = generate_ts_sdk(infos, deployment_path=DEPLOYMENT_FILE, module_name=self.selected_spec)
            ts_path = os.path.join(SDK_DIR, f"{self.selected_spec}_sdk.ts")
            os.makedirs(os.path.dirname(ts_path), exist_ok=True)
            with open(ts_path, "w") as f:
                f.write(ts_code)
            self.log_message(f"  SDK: [dim]{ts_path}[/]")
            
            self.log_message(f"[green]✓ Build complete![/]")
            
        except Exception as e:
            self.log_message(f"[red]✗ Build failed: {e}[/]")
    
    async def do_deploy(self) -> None:
        """Deploy to Sui network."""
        import subprocess
        
        self.log_message("[blue]Starting deployment to Sui network...[/]")
        
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["sui", "client", "publish", "--gas-budget", "100000000", "--json", "--skip-dependency-verification"],
                cwd=CONTRACT_DIR,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.log_message(f"[red]✗ Deployment failed: {result.stderr}[/]")
                return
            
            data = json.loads(result.stdout)
            
            package_id = None
            contract_id = None
            
            if "objectChanges" in data:
                for change in data["objectChanges"]:
                    if change["type"] == "published":
                        package_id = change["packageId"]
                    elif change["type"] == "created" and "::Contract" in change.get("objectType", ""):
                        contract_id = change["objectId"]
            
            if package_id:
                self.log_message(f"[green]✓ Deployment successful![/]")
                self.log_message(f"  Package ID: [cyan]{package_id}[/]")
                if contract_id:
                    self.log_message(f"  Contract ID: [cyan]{contract_id}[/]")
                
                # Save deployment info
                deployment_info = {
                    "package_id": package_id,
                    "contract_id": contract_id,
                    "network": "testnet",
                    "digest": data.get("digest", "")
                }
                os.makedirs(os.path.dirname(DEPLOYMENT_FILE), exist_ok=True)
                with open(DEPLOYMENT_FILE, "w") as f:
                    json.dump(deployment_info, f, indent=2)
                
                self.log_message(f"  Saved to: [dim]{DEPLOYMENT_FILE}[/]")
            else:
                self.log_message("[red]✗ Could not find Package ID[/]")
                
        except FileNotFoundError:
            self.log_message("[red]✗ Sui CLI not found. Please install it first.[/]")
        except Exception as e:
            self.log_message(f"[red]✗ Error: {e}[/]")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "btn-build":
            asyncio.create_task(self.do_build())
        elif button_id == "btn-validate":
            asyncio.create_task(self.do_validate())
        elif button_id == "btn-deploy":
            asyncio.create_task(self.do_deploy())
        elif button_id == "btn-refresh":
            self.load_specs()
            self.log_message("[blue]Spec list refreshed[/]")


def main():
    app = MarloweCompilerApp()
    app.run()


if __name__ == "__main__":
    main()
