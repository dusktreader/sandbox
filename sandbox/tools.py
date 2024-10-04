import shlex
import subprocess

from loguru import logger


def run_command(command) -> tuple[str | None, str | None]:
    proc = subprocess.run(shlex.split(command))
    (stdout, stderr) = (proc.stdout.decode(), proc.stderr.decode())
    return (stdout, stderr)


def run_command_logged(command):
    logger.debug(f"Issuing subprocess {command=}")
    proc = subprocess.Popen(
        shlex.split(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc_name = proc.args[0]
    last_err_line = ""
    while proc.poll() is None:
        while True:
            stderr_line = proc.stderr.readline().decode()
            if stderr_line:
                last_err_line = stderr_line
                logger.debug(f"Subprocess {proc_name} => {stderr_line}")
            else:
                break
    if proc.returncode != 0:
        raise RuntimeError(f"Subprocess {proc_name} error: {last_err_line}")
