#!/usr/bin/env python3
"""
MongoDB Docker Manager CLI
A simple tool to manage MongoDB Docker containers and images using Rich and Typer.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(help="MongoDB Docker Manager - Manage MongoDB containers and images")
console = Console()

# Default configuration
DEFAULT_IMAGE_NAME = "whatdataiamgiving-mongodb"
DEFAULT_CONTAINER_NAME = "whatdataiamgiving-mongodb"
DOCKERFILE_PATH = "../docker/mongodb/Dockerfile"
MONGODB_PORT = "27017"
VOLUME_NAME = "mongodb_data"


def run_command(command: str, show_output: bool = True) -> tuple[bool, str]:
    """Run a shell command and return success status and output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        
        if show_output and result.stdout:
            console.print(f"[dim]{result.stdout}[/dim]")
        
        if result.stderr and result.returncode != 0:
            console.print(f"[red]Error: {result.stderr}[/red]")
            return False, result.stderr
        
        return result.returncode == 0, result.stdout
    
    except Exception as e:
        console.print(f"[red]Command failed: {e}[/red]")
        return False, str(e)


@app.command("build")
def build_image(
    tag: str = typer.Option(DEFAULT_IMAGE_NAME, "--tag", "-t", help="Image tag/name"),
    dockerfile: str = typer.Option(DOCKERFILE_PATH, "--dockerfile", "-f", help="Path to Dockerfile")
):
    """Build a Docker image from the MongoDB Dockerfile."""
    
    dockerfile_path = Path(dockerfile)
    if not dockerfile_path.exists():
        console.print(f"[red]Error: Dockerfile not found at {dockerfile_path}[/red]")
        raise typer.Exit(1)
    
    console.print(Panel(f"Building Docker image: [bold cyan]{tag}[/bold cyan]", title="🐳 Docker Build"))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(description="Building image...", total=None)
        
        build_context = dockerfile_path.parent
        command = f"docker build -t {tag} -f {dockerfile} {build_context}"
        success, output = run_command(command)
    
    if success:
        console.print(f"[green]✅ Successfully built image: {tag}[/green]")
    else:
        console.print(f"[red]❌ Failed to build image: {tag}[/red]")
        raise typer.Exit(1)


@app.command("create")
def create_container(
    image: str = typer.Option(DEFAULT_IMAGE_NAME, "--image", "-i", help="Image name to create container from"),
    name: str = typer.Option(DEFAULT_CONTAINER_NAME, "--name", "-n", help="Container name"),
    port: str = typer.Option(MONGODB_PORT, "--port", "-p", help="Port mapping (host:container)"),
    volume: str = typer.Option(VOLUME_NAME, "--volume", "-v", help="Volume name for data persistence")
):
    """Create a container from an existing image."""
    
    console.print(Panel(f"Creating container: [bold cyan]{name}[/bold cyan] from image: [bold yellow]{image}[/bold yellow]", title="📦 Container Creation"))
    
    # Check if image exists
    check_command = f"docker image inspect {image}"
    exists, _ = run_command(check_command, show_output=False)
    
    if not exists:
        console.print(f"[red]❌ Image '{image}' not found. Build it first with: docker-manager build --tag {image}[/red]")
        raise typer.Exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(description="Creating container...", total=None)
        
        command = f"docker run -d --name {name} -p {port}:{MONGODB_PORT} -v {volume}:/data/db {image}"
        success, output = run_command(command)
    
    if success:
        console.print(f"[green]✅ Successfully created container: {name}[/green]")
        console.print(f"[dim]MongoDB accessible at: localhost:{port}[/dim]")
    else:
        console.print(f"[red]❌ Failed to create container: {name}[/red]")
        raise typer.Exit(1)


@app.command("build-and-run")
def build_and_run(
    tag: str = typer.Option(DEFAULT_IMAGE_NAME, "--tag", "-t", help="Image tag/name"),
    name: str = typer.Option(DEFAULT_CONTAINER_NAME, "--name", "-n", help="Container name"),
    dockerfile: str = typer.Option(DOCKERFILE_PATH, "--dockerfile", "-f", help="Path to Dockerfile"),
    port: str = typer.Option(MONGODB_PORT, "--port", "-p", help="Port mapping (host:container)"),
    volume: str = typer.Option(VOLUME_NAME, "--volume", "-v", help="Volume name for data persistence")
):
    """Build Docker image and immediately create a container from it."""
    
    console.print(Panel(f"Building image [bold cyan]{tag}[/bold cyan] and creating container [bold yellow]{name}[/bold yellow]", title="🚀 Build & Run"))
    
    # First, build the image
    console.print("[bold]Step 1:[/bold] Building image...")
    try:
        build_image(tag, dockerfile)
    except typer.Exit:
        return
    
    # Then, create the container
    console.print(f"\n[bold]Step 2:[/bold] Creating container...")
    try:
        create_container(tag, name, port, volume)
    except typer.Exit:
        return
    
    console.print(f"\n[green]🎉 Successfully built and started MongoDB![/green]")
    console.print(f"[dim]Connect to: mongodb://localhost:{port}/whatdataiamgiving[/dim]")


@app.command("delete-image")
def delete_image(
    tag: str = typer.Argument(..., help="Image tag/name to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Force removal of image")
):
    """Delete a Docker image."""
    
    console.print(Panel(f"Deleting image: [bold red]{tag}[/bold red]", title="🗑️ Image Deletion"))
    
    # Check if image exists
    check_command = f"docker image inspect {tag}"
    exists, _ = run_command(check_command, show_output=False)
    
    if not exists:
        console.print(f"[yellow]⚠️ Image '{tag}' not found.[/yellow]")
        return
    
    force_flag = "-f" if force else ""
    command = f"docker rmi {force_flag} {tag}"
    success, output = run_command(command)
    
    if success:
        console.print(f"[green]✅ Successfully deleted image: {tag}[/green]")
    else:
        console.print(f"[red]❌ Failed to delete image: {tag}[/red]")
        if not force:
            console.print("[dim]Try using --force flag if containers are using this image[/dim]")
        raise typer.Exit(1)


@app.command("delete-container")
def delete_container(
    name: str = typer.Argument(..., help="Container name to delete")
):
    """Delete a container."""
    
    console.print(Panel(f"Deleting container: [bold red]{name}[/bold red]", title="🗑️ Container Deletion"))
    
    # Check if container exists
    check_command = f"docker container inspect {name}"
    exists, _ = run_command(check_command, show_output=False)
    
    if not exists:
        console.print(f"[yellow]⚠️ Container '{name}' not found.[/yellow]")
        return
    
    # Stop and remove container
    console.print("Stopping and removing container...")
    stop_command = f"docker stop {name}"
    remove_command = f"docker rm {name}"
    
    run_command(stop_command, show_output=False)  # Stop might fail if already stopped
    success, output = run_command(remove_command)
    
    if success:
        console.print(f"[green]✅ Successfully deleted container: {name}[/green]")
    else:
        console.print(f"[red]❌ Failed to delete container: {name}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_resources():
    """List all MongoDB-related Docker images and containers."""
    
    console.print(Panel("MongoDB Docker Resources", title="📋 Resource List"))
    
    # List containers
    console.print("[bold]Containers:[/bold]")
    containers_command = "docker ps -a --filter name=mongodb --format table"
    success, output = run_command(containers_command)
    
    if not success or not output.strip():
        console.print("[dim]No MongoDB containers found[/dim]")
    
    console.print()
    
    # List images
    console.print("[bold]Images:[/bold]")
    images_command = "docker images --filter reference='*mongodb*' --format table"
    success, output = run_command(images_command)
    
    if not success or not output.strip():
        console.print("[dim]No MongoDB images found[/dim]")


@app.command("status")
def status(
    name: str = typer.Option(DEFAULT_CONTAINER_NAME, "--name", "-n", help="Container name to check")
):
    """Check the status of MongoDB container."""
    
    # Check container status
    status_command = f"docker container inspect {name} --format '{{{{.State.Status}}}}'"
    success, output = run_command(status_command, show_output=False)
    
    if success and output.strip():
        status_text = output.strip()
        if status_text == "running":
            console.print(f"[green]✅ Container '{name}' is running[/green]")
            
            # Get port info
            port_command = f"docker port {name}"
            port_success, port_output = run_command(port_command, show_output=False)
            if port_success and port_output:
                console.print(f"[dim]Port mapping: {port_output.strip()}[/dim]")
        else:
            console.print(f"[yellow]⚠️ Container '{name}' is {status_text}[/yellow]")
    else:
        console.print(f"[red]❌ Container '{name}' not found[/red]")


if __name__ == "__main__":
    app()
