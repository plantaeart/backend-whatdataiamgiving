# MongoDB Docker Manager

A simple CLI tool to manage MongoDB Docker containers and images with Rich UI and Typer commands.

## Installation

The dependencies are in your `pyproject.toml`. Install them with:

```bash
cd backend-whatdataiamgiving
uv sync
```

## Usage

**Important**: Use `uv run` to execute the script with the virtual environment:

### Make sure you're in the project root

```bash
cd "c:\Users\Plantae\Documents\02 - Web dev projects\WhatDataIAmGiving\backend-whatdataiamgiving"
```

**Note**: Replace all `python docker_manager.py` commands below with `uv run python scripts/docker_manager.py`

### Commands Available

#### 1. Build Docker Image

```bash
# Build with default tag
python docker_manager.py build

# Build with custom tag
python docker_manager.py build --tag my-mongodb:latest

# Build with custom dockerfile path
python docker_manager.py build --tag my-mongodb --dockerfile ./docker/mongodb/Dockerfile
```

#### 2. Create Container from Image

```bash
# Create container with defaults
python docker_manager.py create

# Create with custom parameters
python docker_manager.py create --image my-mongodb --name my-container --port 27018
```

#### 3. Build Image AND Create Container (One Command)

```bash
# Build and run with defaults
python docker_manager.py build-and-run

# Build and run with custom parameters
python docker_manager.py build-and-run --tag my-mongodb:v1 --name my-mongo-container --port 27018
```

#### 4. Delete Image

```bash
# Delete specific image
python docker_manager.py delete-image my-mongodb

# Force delete (even if containers are using it)
python docker_manager.py delete-image my-mongodb --force
```

#### 5. Delete Container

```bash
# Delete container (simple and clean!)
python docker_manager.py delete-container my-container
```

#### 6. Delete Image

```bash
# Delete specific image
python docker_manager.py delete-image my-mongodb

# Force delete (even if containers are using it)
python docker_manager.py delete-image my-mongodb --force
```

#### 7. List Resources

```bash
# Show all MongoDB-related containers and images
python docker_manager.py list
```

#### 8. Check Status

```bash
# Check default container status
python docker_manager.py status

# Check specific container
python docker_manager.py status --name my-container
```

## Examples

### Quick Start (Build and Run MongoDB)

```bash
python docker_manager.py build-and-run
```

This will:

1. Build image as `whatdataiamgiving-mongodb`
2. Create container as `whatdataiamgiving-mongodb`
3. Map to port `27017`
4. Create persistent volume `mongodb_data`

### Custom Setup

```bash
# Build custom image
python docker_manager.py build --tag myapp-mongo:v2

# Create container with custom port
python docker_manager.py create --image myapp-mongo:v2 --name mongo-dev --port 27018

# Check if it's running
python docker_manager.py status --name mongo-dev
```

### Cleanup

```bash
# Delete container
python docker_manager.py delete-container mongo-dev

# Delete image separately if needed
python docker_manager.py delete-image myapp-mongo:v2
```

## Default Configuration

- **Image Name**: `whatdataiamgiving-mongodb`
- **Container Name**: `whatdataiamgiving-mongodb`
- **Port**: `27017`
- **Volume**: `mongodb_data`
- **Dockerfile**: `./docker/mongodb/Dockerfile`

All defaults can be overridden with command line options.
