"""Run commands against cEOS lab devices."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    """Result from a command executed in a lab container."""

    stdout: str
    stderr: str
    returncode: int


class LabCommandError(RuntimeError):
    """Raised when a lab command exits unsuccessfully."""


def container_name(lab_name: str, node_name: str) -> str:
    """Return the Containerlab container name for a node."""
    return f"clab-{lab_name}-{node_name}"


def run_container_command(
    lab_name: str,
    node_name: str,
    command: list[str],
    check: bool = True,
) -> CommandResult:
    """Run a command inside a Containerlab node using docker exec."""
    docker_command = ["docker", "exec", container_name(lab_name, node_name), *command]
    result = subprocess.run(
        docker_command,
        capture_output=True,
        text=True,
        check=False,
    )

    if check and result.returncode != 0:
        raise LabCommandError(
            f"{node_name} command failed with exit code {result.returncode}: "
            f"{' '.join(command)}\n{result.stderr.strip()}"
        )

    return CommandResult(
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
    )


def run_eos_command(
    lab_name: str,
    device_name: str,
    command: str,
    json_output: bool = True,
) -> str:
    """Run an EOS CLI command and return raw command output."""
    eos_command = f"{command} | json" if json_output else command
    return run_container_command(
        lab_name=lab_name,
        node_name=device_name,
        command=["Cli", "-c", eos_command],
    ).stdout


def run_eos_json(lab_name: str, device_name: str, command: str) -> dict:
    """Run an EOS CLI command with JSON output and decode the response."""
    output = run_eos_command(lab_name, device_name, command, json_output=True)
    return json.loads(output)


def run_host_command(lab_name: str, host_name: str, command: list[str]) -> str:
    """Run a command inside a Linux host container and return stdout."""
    return run_container_command(
        lab_name=lab_name,
        node_name=host_name,
        command=command,
    ).stdout
