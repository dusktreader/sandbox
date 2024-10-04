import snick
import typer

from sandbox.subapps import apptainer
from sandbox.exceptions import handle_abort
from sandbox.cache import init_cache
from sandbox.logging import init_logs
from sandbox.format import terminal_message, render_json
from sandbox.config import clear_settings, attach_settings, init_settings, dump_settings
from sandbox.context import CliContext

app = typer.Typer()
app.add_typer(apptainer.app, name="apptainer")


@app.callback(invoke_without_command=True)
@handle_abort
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, help="Enable verbose logging to the terminal"),
):
    """
    Welcome to the Sandbox CLI!

    More information can be shown for each command listed below by running it with the
    --help option.
    """

    if ctx.invoked_subcommand is None:
        terminal_message(
            snick.conjoin(
                "No command provided. Please check [bold magenta]usage[/bold magenta]",
                "",
                f"[yellow]{ctx.get_help()}[/yellow]",
            ),
            subject="Need a Sandbox command",
        )
        raise typer.Exit()

    init_logs(verbose=verbose)
    ctx.obj = CliContext()


@app.command()
@init_cache
def set_config(
    aws_access_key_id: str = typer.Option(..., help="The access key id used by apptainer subcommand"),
    aws_secret_access_key: str = typer.Option(..., help="The secret access key used by apptainer subcommand"),
    aws_ecr_public_registry: str = typer.Option(..., help="The public registry to use"),
):
    settings = init_settings(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_ecr_public_registry=aws_ecr_public_registry,
    )
    dump_settings(settings)


@app.command()
@handle_abort
@init_cache
@attach_settings
def show_config(ctx: typer.Context):
    """
    Show the current config.
    """
    render_json(ctx.obj.settings.model_dump())


@app.command()
@handle_abort
@init_cache
def clear_config():
    """
    Show the current config.
    """
    clear_settings()
