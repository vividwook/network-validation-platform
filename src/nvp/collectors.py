"""Collect actual operational state from devices and hosts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from nvp.eos_client import run_eos_command, run_host_command
from nvp.load_sot import DEFAULT_SOT_DIR, load_fabric_intent
from nvp.models import FabricIntent


DEFAULT_STATE_DIR = Path("artifacts/state")

EOS_JSON_COMMANDS = {
    "show_ip_interface_brief": "show ip interface brief",
    "show_ip_bgp_summary": "show ip bgp summary",
    "show_bgp_evpn_summary": "show bgp evpn summary",
    "show_vxlan_vni": "show vxlan vni",
    "show_vlan": "show vlan",
    "show_vrf": "show vrf",
    "show_interfaces_vxlan1": "show interfaces vxlan 1",
    "show_mac_address_table": "show mac address-table",
}

HOST_COMMANDS = {
    "ip_addr": ["ip", "addr"],
    "ip_route": ["ip", "route"],
}


@dataclass(frozen=True)
class CollectedArtifact:
    """A state artifact written to disk."""

    node: str
    command_name: str
    path: Path


def write_text_artifact(
    output_dir: Path,
    node_name: str,
    command_name: str,
    content: str,
    suffix: str,
) -> CollectedArtifact:
    """Write one collected command output artifact."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{node_name}_{command_name}.{suffix}"
    path.write_text(content, encoding="utf-8")
    return CollectedArtifact(node=node_name, command_name=command_name, path=path)


def collect_eos_state(
    intent: FabricIntent,
    lab_name: str,
    output_dir: Path,
) -> list[CollectedArtifact]:
    """Collect show command output from all cEOS devices."""
    artifacts: list[CollectedArtifact] = []
    devices = [
        name
        for name, device in intent.devices.items()
        if device.platform == "arista_eos"
    ]

    for device_name in devices:
        for command_name, command in EOS_JSON_COMMANDS.items():
            output = run_eos_command(lab_name, device_name, command, json_output=True)
            artifacts.append(
                write_text_artifact(
                    output_dir=output_dir,
                    node_name=device_name,
                    command_name=command_name,
                    content=json.dumps(json.loads(output), indent=2, sort_keys=True),
                    suffix="json",
                )
            )

    return artifacts


def collect_host_state(
    intent: FabricIntent,
    lab_name: str,
    output_dir: Path,
) -> list[CollectedArtifact]:
    """Collect Linux host state from all lab hosts."""
    artifacts: list[CollectedArtifact] = []

    for host_name in intent.hosts:
        for command_name, command in HOST_COMMANDS.items():
            output = run_host_command(lab_name, host_name, command)
            artifacts.append(
                write_text_artifact(
                    output_dir=output_dir,
                    node_name=host_name,
                    command_name=command_name,
                    content=output,
                    suffix="txt",
                )
            )

    return artifacts


def collect_reachability_state(
    intent: FabricIntent,
    lab_name: str,
    output_dir: Path,
) -> list[CollectedArtifact]:
    """Run ping checks declared in overlay reachability intent."""
    artifacts: list[CollectedArtifact] = []

    for check in intent.overlay.same_vlan_reachability:
        destination_ip = intent.hosts[check.destination].ip
        output = run_host_command(
            lab_name,
            check.source,
            ["ping", "-c", "3", destination_ip],
        )
        artifacts.append(
            write_text_artifact(
                output_dir=output_dir,
                node_name=check.source,
                command_name=f"ping_{check.destination}",
                content=output,
                suffix="txt",
            )
        )

    return artifacts


def collect_state(
    sot_dir: Path | str = DEFAULT_SOT_DIR,
    output_dir: Path | str = DEFAULT_STATE_DIR,
    lab_name: str | None = None,
) -> list[CollectedArtifact]:
    """Collect EOS, host, and reachability state artifacts."""
    intent = load_fabric_intent(sot_dir)
    resolved_lab_name = lab_name or intent.fabric.name
    destination = Path(output_dir)

    artifacts: list[CollectedArtifact] = []
    artifacts.extend(collect_eos_state(intent, resolved_lab_name, destination))
    artifacts.extend(collect_host_state(intent, resolved_lab_name, destination))
    artifacts.extend(collect_reachability_state(intent, resolved_lab_name, destination))
    return artifacts
