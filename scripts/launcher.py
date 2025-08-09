#!/usr/bin/env python3
"""
FastAPI Development Server Launcher
A beautiful CLI tool to launch your FastAPI application with various options.
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import print as rprint

app = typer.Typer(
    name="fastapi-launcher",
    help="🚀 Launch your FastAPI application with style!",
    rich_markup_mode="rich"
)
console = Console()

@app.command()
def dev(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind the server to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind the server to"),
    reload: bool = typer.Option(True, "--reload/--no-reload", help="Enable auto-reload on file changes"),
    log_level: str = typer.Option("info", "--log-level", "-l", help="Log level (debug, info, warning, error, critical)"),
    app_module: str = typer.Option("main:app", "--app", "-a", help="FastAPI app module (e.g., main:app)"),
):
    """
    🎯 Launch FastAPI development server with auto-reload
    """
    # Create a beautiful startup banner
    banner = Panel.fit(
        Text("🚀 FastAPI Development Server", style="bold blue", justify="center"),
        border_style="blue",
        padding=(1, 2)
    )
    console.print(banner)
    
    # Show configuration table
    config_table = Table(title="🔧 Server Configuration", show_header=True, header_style="bold magenta")
    config_table.add_column("Setting", style="cyan", no_wrap=True)
    config_table.add_column("Value", style="green")
    
    config_table.add_row("Host", host)
    config_table.add_row("Port", str(port))
    config_table.add_row("Auto-reload", "✅ Enabled" if reload else "❌ Disabled")
    config_table.add_row("Log Level", log_level.upper())
    config_table.add_row("App Module", app_module)
    
    console.print(config_table)
    console.print()
    
    # Build the uvicorn command - use python -m uvicorn for better compatibility
    cmd = [
        "uv", "run", "python", "-m", "uvicorn", app_module,
        "--host", host,
        "--port", str(port),
        "--log-level", log_level,
    ]
    
    if reload:
        cmd.append("--reload")
    
    # Show the command being executed
    cmd_text = " ".join(cmd)
    console.print(f"[bold yellow]Executing:[/bold yellow] [dim]{cmd_text}[/dim]")
    console.print()
    
    # Ensure we're in the correct directory (where main.py is located)
    script_dir = Path(__file__).parent.parent  # Go up from scripts/ to project root
    original_cwd = Path.cwd()
    
    # Change to the project directory
    os.chdir(script_dir)
    
    # Show server URLs for easy access
    if host == "0.0.0.0":
        # For 0.0.0.0, show localhost as the clickable URL since 0.0.0.0 isn't browsable
        display_host = "localhost"
        server_url = f"http://{display_host}:{port}"
        console.print("🌐 [bold green]Server URLs (Ctrl+Click to open):[/bold green]")
        console.print(f"   📖 API Docs:     [link={server_url}/docs]{server_url}/docs[/link]")
        console.print(f"   📚 ReDoc:        [link={server_url}/redoc]{server_url}/redoc[/link]")
        console.print(f"   🏠 Root:         [link={server_url}]{server_url}[/link]")
        console.print(f"   🌍 [dim]Note: Server accepts connections from any IP (0.0.0.0:{port})[/dim]")
    else:
        server_url = f"http://{host}:{port}"
        console.print("🌐 [bold green]Server URLs (Ctrl+Click to open):[/bold green]")
        console.print(f"   📖 API Docs:     [link={server_url}/docs]{server_url}/docs[/link]")
        console.print(f"   📚 ReDoc:        [link={server_url}/redoc]{server_url}/redoc[/link]")
        console.print(f"   🏠 Root:         [link={server_url}]{server_url}[/link]")
    console.print()
    
    # Show a loading spinner while starting
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(description="Starting FastAPI server...", total=None)
        
        try:
            # Start the server
            result = subprocess.run(cmd, check=True)
            progress.update(task, description="✅ Server started successfully!")
            
        except subprocess.CalledProcessError as e:
            progress.stop()
            console.print(f"[bold red]❌ Error starting server:[/bold red] {e}")
            raise typer.Exit(1)
        except KeyboardInterrupt:
            progress.stop()
            console.print("\n[yellow]👋 Server stopped by user[/yellow]")
            raise typer.Exit(0)
        finally:
            # Restore original directory
            os.chdir(original_cwd)

@app.command()
def prod(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind the server to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind the server to"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of worker processes"),
    app_module: str = typer.Option("main:app", "--app", "-a", help="FastAPI app module (e.g., main:app)"),
):
    """
    🏭 Launch FastAPI in production mode (no auto-reload)
    """
    banner = Panel.fit(
        Text("🏭 FastAPI Production Server", style="bold red", justify="center"),
        border_style="red",
        padding=(1, 2)
    )
    console.print(banner)
    
    # Show configuration
    config_table = Table(title="🔧 Production Configuration", show_header=True, header_style="bold magenta")
    config_table.add_column("Setting", style="cyan", no_wrap=True)
    config_table.add_column("Value", style="green")
    
    config_table.add_row("Host", host)
    config_table.add_row("Port", str(port))
    config_table.add_row("Workers", str(workers))
    config_table.add_row("App Module", app_module)
    config_table.add_row("Auto-reload", "❌ Disabled (Production)")
    
    console.print(config_table)
    console.print()
    
    # Build command - use python -m uvicorn for better compatibility
    cmd = [
        "uv", "run", "python", "-m", "uvicorn", app_module,
        "--host", host,
        "--port", str(port),
        "--workers", str(workers),
    ]
    
    cmd_text = " ".join(cmd)
    console.print(f"[bold yellow]Executing:[/bold yellow] [dim]{cmd_text}[/dim]")
    console.print()
    
    # Ensure we're in the correct directory (where main.py is located)
    script_dir = Path(__file__).parent.parent  # Go up from scripts/ to project root
    original_cwd = Path.cwd()
    
    # Change to the project directory
    os.chdir(script_dir)
    
    # Show server URLs for easy access
    if host == "0.0.0.0":
        # For 0.0.0.0, show localhost as the clickable URL since 0.0.0.0 isn't browsable
        display_host = "localhost"
        server_url = f"http://{display_host}:{port}"
        console.print("🌐 [bold green]Server URLs (Ctrl+Click to open):[/bold green]")
        console.print(f"   📖 API Docs:     [link={server_url}/docs]{server_url}/docs[/link]")
        console.print(f"   📚 ReDoc:        [link={server_url}/redoc]{server_url}/redoc[/link]")
        console.print(f"   🏠 Root:         [link={server_url}]{server_url}[/link]")
        console.print(f"   🌍 [dim]Note: Server accepts connections from any IP (0.0.0.0:{port})[/dim]")
    else:
        server_url = f"http://{host}:{port}"
        console.print("🌐 [bold green]Server URLs (Ctrl+Click to open):[/bold green]")
        console.print(f"   📖 API Docs:     [link={server_url}/docs]{server_url}/docs[/link]")
        console.print(f"   📚 ReDoc:        [link={server_url}/redoc]{server_url}/redoc[/link]")
        console.print(f"   🏠 Root:         [link={server_url}]{server_url}[/link]")
    console.print()
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]❌ Error starting server:[/bold red] {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Server stopped by user[/yellow]")
        raise typer.Exit(0)
    finally:
        # Restore original directory
        os.chdir(original_cwd)

@app.command()
def info():
    """
    📋 Show information about the FastAPI application
    """
    info_panel = Panel.fit(
        Text("📋 FastAPI Application Info", style="bold green", justify="center"),
        border_style="green",
        padding=(1, 2)
    )
    console.print(info_panel)
    
    # Check if main.py exists
    main_file = Path("main.py")
    if main_file.exists():
        console.print(f"[green]✅ main.py found[/green]")
        
        # Try to get app info
        try:
            with open(main_file, "r", encoding="utf-8") as f:
                content = f.read()
                if "FastAPI" in content:
                    console.print(f"[green]✅ FastAPI app detected in main.py[/green]")
                else:
                    console.print(f"[yellow]⚠️  FastAPI not detected in main.py[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ Error reading main.py: {e}[/red]")
    else:
        console.print(f"[red]❌ main.py not found[/red]")
    
    # Show available URLs
    urls_table = Table(title="🌐 Available URLs (when server is running)", show_header=True, header_style="bold blue")
    urls_table.add_column("Endpoint", style="cyan")
    urls_table.add_column("URL", style="green")
    urls_table.add_column("Description", style="white")
    
    urls_table.add_row("API Root", "http://127.0.0.1:8000/", "Main API endpoint")
    urls_table.add_row("Interactive Docs", "http://127.0.0.1:8000/docs", "Swagger UI documentation")
    urls_table.add_row("Alternative Docs", "http://127.0.0.1:8000/redoc", "ReDoc documentation")
    urls_table.add_row("OpenAPI Schema", "http://127.0.0.1:8000/openapi.json", "OpenAPI JSON schema")
    
    console.print(urls_table)

if __name__ == "__main__":
    app()