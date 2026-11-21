import typer

app = typer.Typer(no_args_is_help=True)


@app.command()
def ingest() -> None:
    """Import published retailer price lists."""
    typer.echo("Ingest pipeline is not configured yet.")


@app.callback()
def main() -> None:
    """Korpa data tools."""
