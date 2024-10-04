import base64
from pathlib import Path

import boto3
import docker
import friendlywords
import typer
from loguru import logger

from sandbox.exceptions import handle_abort, Abort
from sandbox.config import attach_settings
from sandbox.format import terminal_message
from sandbox.tools import run_command, run_command_logged

app = typer.Typer(help="Commands to interact with apptainer")


@app.command()
@handle_abort
@attach_settings
def build(
    ctx: typer.Context,
    image_name: str | None = None,
    image_source: str = "./Dockerfile",
    output_dir: Path | None = None,
):
    """Build an apptainer .sif file from a Dockerfile"""
    settings = ctx.obj.settings

    if image_name is None:
        image_name = friendlywords.generate("po", separator="-")
        logger.debug(f"Image name was not supplied using {image_name=}")
    if output_dir is None:
        output_dir = Path()
        logger.debug(f"No output directory given using {output_dir=}")

    image_source_path = Path(image_source)
    if image_source_path.exists():
        with Abort.handle_errors(
            "Failed to build from file path.",
            raise_kwargs=dict(
                subject="Build failed",
                log_message=f"There was an error building docker image from {image_source_path=}",
            ),
        ):
            docker_client = docker.from_env()
            logger.debug(f"Building local docker image from {image_source_path}")
            local_tag = f"local/{image_name}:latest"
            docker_client.images.build(
                tag=local_tag,
                path=str(image_source_path.parent),
                dockerfile=image_source_path.name,
                rm=True,
            )
            logger.debug(f"Local docker image built as {local_tag=}")
            image_source = f"docker-daemon://{local_tag}"
            logger.debug(f"Set {image_source=}")

    with Abort.handle_errors(
        f"Failed to build apptainer image from {image_source=}",
        raise_kwargs=dict(
            subject="Build failed",
            log_message=f"There was an error building apptainer image from {image_source=}",
        ),
    ):
        logger.debug(f"Building apptainer image from {image_source=}")
        output_image_path = output_dir / f"{image_name}.sif"
        command = f"apptainer build {output_image_path} {image_source}"
        run_command_logged(command)
    final_message = f"Successfully built Apptainer image {output_image_path}"
    logger.debug(final_message)
    terminal_message(final_message)


@app.command()
@handle_abort
@attach_settings
def publish(
    ctx: typer.Context,
    image_path: Path = typer.Option(..., help="The path to the apptainer image (.sif) that is being published"),
    image_tag: str = typer.Option("latest", help="The tag to use for the image")
):
    """Publish an apptainer .sif image to public ECR."""
    logger.debug(f"Attempting to publish {image_path=} to ECR")
    image_name = image_path.stem
    image_target = f"{image_name}:{image_tag}"
    logger.debug(f"Using {image_target=}")

    # logger.debug(f"Extracting metadata from {image_path}")
    # (stdout, stderr) = run_command(f"apptainer inspect --json {image_path}")

    # ECR Public is only supported in th us-east-1 region apparently
    logger.debug("Setting up ECR Public client")
    settings = ctx.obj.settings
    aws_region = "us-east-1"
    logger.debug(f"Getting ECR client for region={aws_region}")
    ecr_client = boto3.client(
        "ecr-public",
        region_name=aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )

    logger.debug(f"Fetching authorization token and extracting username and password")
    response = ecr_client.get_authorization_token()
    token = response["authorizationData"]["authorizationToken"]
    (username, password) = base64.b64decode(token).decode().split(':')
    logger.debug(f"Unpacked {username=}")

    response = ecr_client.describe_registries()
    registry_list = response["registries"]
    Abort.require_condition(
        len(registry_list) == 1,
        "Did not find one and only one registry",
        raise_kwargs=dict(
            subject="Publish failed",
            log_message=f"Found {len(registry_list)} registries instead of one",
        ),
    )
    registry_data = registry_list[0]
    registry_id = registry_data["registryId"]
    registry_uri = registry_data["registryUri"]
    registry_domain = registry_uri.split("/")[0]

    try:
        response = ecr_client.get_repository_catalog_data(
            registryId=registry_id,
            repositoryName=image_name,
        )
    except ecr_client.exceptions.RepositoryNotFoundException:
        logger.debug(f"There is no repository for {image_name=}. Creating one...")
        # TODO: Figure out how to determine OS and Architecture for the image repository
        ecr_client.create_repository(repositoryName=image_name)

    logger.debug("Logging into public ecr via apptainer")
    command = f"apptainer registry login --username={username} --password={password} oras://{registry_domain}"
    run_command_logged(command)

    logger.debug("Pushing image to public ECR")
    publish_url = f"oras://{registry_uri}/{image_target}"
    command = f"apptainer push {image_path} {publish_url}"
    run_command_logged(command)

    final_message = f"Successfully published Apptainer image {image_path} to {publish_url}"
    logger.debug(final_message)
    terminal_message(final_message)
