import os
from pathlib import Path
import sqlite3
from contextlib import closing
from tempfile import NamedTemporaryFile

import click
from flask.cli import with_appcontext

from . import db


def copy_database(source, destination):
    """Take a consistent copy and publish it only after checking its integrity."""
    if destination.exists():
        raise click.ClickException(f"{destination} already exists. Choose a new file.")

    scratch = None
    try:
        with NamedTemporaryFile(dir=destination.parent, prefix=".portfolio-", delete=False) as file:
            scratch = Path(file.name)
        with (
            closing(sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True)) as original,
            closing(sqlite3.connect(scratch)) as copied,
        ):
            original.backup(copied)
            if copied.execute("PRAGMA quick_check").fetchone() != ("ok",):
                raise click.ClickException("The copied database did not pass its integrity check.")
        os.link(scratch, destination)
    except (OSError, sqlite3.Error) as error:
        raise click.ClickException(f"Could not copy the database: {error}") from error
    finally:
        if scratch is not None:
            scratch.unlink(missing_ok=True)


@click.command("backup-db")
@click.argument("destination", type=click.Path(path_type=Path, dir_okay=False))
@with_appcontext
def backup_db(destination):
    """Write a private, verified backup to a new file."""
    source = db.engine.url.database
    if not source or source == ":memory:":
        raise click.ClickException("A file-backed SQLite database is required.")
    copy_database(Path(source), destination)
    click.echo(f"Backup verified: {destination}")


@click.command("restore-db")
@click.argument("source", type=click.Path(path_type=Path, exists=True, dir_okay=False))
@click.argument("destination", type=click.Path(path_type=Path, dir_okay=False))
def restore_db(source, destination):
    """Verify a backup and restore it to a new SQLite file."""
    copy_database(source, destination)
    click.echo(f"Restore verified: {destination}")
