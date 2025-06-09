#!/usr/bin/env python3
import os
import uuid
import json
import shutil
import zipfile
from datetime import datetime
import click

CONFIG_FOLDER = ".sync"
CONFIG_FILE = "config.json"
SNAPSHOTS_FOLDER = "snapshots"
HISTORY_FILE = "history.json"

def get_config(project_dir):
    config_path = os.path.join(project_dir, CONFIG_FOLDER, CONFIG_FILE)
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    return None

def save_config(project_dir, config):
    os.makedirs(os.path.join(project_dir, CONFIG_FOLDER), exist_ok=True)
    config_path = os.path.join(project_dir, CONFIG_FOLDER, CONFIG_FILE)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)

def get_usb_path(current, provided_path=None):
    config = get_config(current)
    if config is None:
        raise click.ClickException("Este proyecto no está inicializado. Usa `synu init`.")

    if provided_path:
        config["usb_path"] = os.path.abspath(provided_path)
        save_config(current, config)
        return config["usb_path"]

    usb_path = config.get("usb_path")
    if not usb_path:
        raise click.ClickException("No hay un path de USB configurado. Usa `--path` la primera vez.")
    return usb_path

@click.group()
def cli():
    """Synu: CLI de sincronización de proyectos estilo Git en dispositivos USB."""
    pass

@cli.command()
def init():
    """Inicializa el proyecto actual (crea .sync/)."""
    current = os.getcwd()
    sync_path = os.path.join(current, CONFIG_FOLDER)

    if os.path.exists(sync_path):
        click.echo("Este proyecto ya está inicializado.")
        return

    os.makedirs(os.path.join(sync_path, SNAPSHOTS_FOLDER), exist_ok=True)
    config = {
        "project_name": os.path.basename(current),
        "identifier": str(uuid.uuid4()),
        "usb_path": ""
    }
    save_config(current, config)
    click.echo(f"Proyecto '{config['project_name']}' inicializado con ID {config['identifier']}.")

@cli.command()
@click.option('--path', '-p', help='Ruta del USB (solo requerido la primera vez).')
@click.option('--message', '-m', required=True, help='Mensaje del respaldo.')
@click.option('--current', '-c', default='.', help='Ruta del proyecto actual.')
def backup(path, message, current):
    """Crea un respaldo comprimido del proyecto actual."""
    current = os.path.abspath(current)
    usb_path = get_usb_path(current, path)

    config = get_config(current)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_name = f"{config['project_name']}_{now}.zip"
    local_snapshots_dir = os.path.join(current, CONFIG_FOLDER, SNAPSHOTS_FOLDER)
    snapshot_path = os.path.join(local_snapshots_dir, snapshot_name)

    os.makedirs(local_snapshots_dir, exist_ok=True)

    # Crear snapshot ZIP con carpetas vacías y archivos vacíos incluidos
    with zipfile.ZipFile(snapshot_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(current):
            if CONFIG_FOLDER in root:
                continue
            rel_root = os.path.relpath(root, current)
            if rel_root != ".":
                zipf.writestr(rel_root + '/', '')  # incluir carpetas vacías

            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, current)
                if os.path.getsize(abs_path) == 0:
                    zipf.writestr(rel_path, '')  # incluir archivo vacío
                else:
                    zipf.write(abs_path, rel_path)

    # Copiar a USB
    usb_snapshots_dir = os.path.join(usb_path, SNAPSHOTS_FOLDER)
    os.makedirs(usb_snapshots_dir, exist_ok=True)
    shutil.copy(snapshot_path, os.path.join(usb_snapshots_dir, snapshot_name))

    # Guardar historial
    usb_history_path = os.path.join(usb_path, CONFIG_FOLDER, HISTORY_FILE)
    os.makedirs(os.path.dirname(usb_history_path), exist_ok=True)
    history = []
    if os.path.exists(usb_history_path):
        with open(usb_history_path) as f:
            history = json.load(f)
    history.append({"snapshot": snapshot_name, "message": message, "timestamp": now})
    with open(usb_history_path, 'w') as f:
        json.dump(history, f, indent=4)

    click.echo(f"Respaldo creado: {snapshot_name}")

@cli.command()
@click.option('--path', '-p', help='Ruta del USB (solo requerido si no está guardada).')
@click.option('--current', '-c', default='.', help='Ruta del proyecto actual.')
def restore(path, current):
    """Restaura el último respaldo desde el USB."""
    current = os.path.abspath(current)
    usb_path = get_usb_path(current, path)
    snapshots_dir = os.path.join(usb_path, SNAPSHOTS_FOLDER)

    if not os.path.exists(snapshots_dir):
        raise click.ClickException("No hay respaldos en el USB.")

    snapshots = sorted(os.listdir(snapshots_dir), reverse=True)
    if not snapshots:
        raise click.ClickException("No se encontraron respaldos en el USB.")

    latest = snapshots[0]
    with zipfile.ZipFile(os.path.join(snapshots_dir, latest), 'r') as zipf:
        zipf.extractall(current)

    click.echo(f"Restaurado desde snapshot: {latest}")

@cli.command()
@click.option('--path', '-p', help='Ruta del USB (solo requerido si no está guardada).')
@click.option('--snap', '-s', required=True, help='Nombre del snapshot a restaurar.')
@click.option('--current', '-c', default='.', help='Ruta del proyecto actual.')
def downgrade(path, snap, current):
    """Restaura un snapshot específico desde el USB."""
    current = os.path.abspath(current)
    usb_path = get_usb_path(current, path)
    snap_path = os.path.join(usb_path, SNAPSHOTS_FOLDER, snap)

    if not os.path.exists(snap_path):
        raise click.ClickException(f"Snapshot '{snap}' no encontrado en el USB.")

    with zipfile.ZipFile(snap_path, 'r') as zipf:
        zipf.extractall(current)

    click.echo(f"Restaurado desde snapshot: {snap}")

if __name__ == '__main__':
    cli()
