"""Compare expected fabric intent against actual operational state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nvp.generate_configs import underlay_neighbors
from nvp.load_sot import DEFAULT_SOT_DIR, load_fabric_intent
from nvp.models import FabricIntent, ValidationResult


DEFAULT_STATE_DIR = Path("artifacts/state")


def artifact_path(state_dir: Path, node_name: str, command_name: str, suffix: str) -> Path:
    """Return the path for a collected state artifact."""
    return state_dir / f"{node_name}_{command_name}.{suffix}"


def read_json_artifact(state_dir: Path, node_name: str, command_name: str) -> dict[str, Any]:
    """Read a JSON state artifact."""
    path = artifact_path(state_dir, node_name, command_name, "json")
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def read_text_artifact(state_dir: Path, node_name: str, command_name: str) -> str:
    """Read a text state artifact."""
    return artifact_path(state_dir, node_name, command_name, "txt").read_text(
        encoding="utf-8"
    )


def result(check_name: str, passed: bool, message: str) -> ValidationResult:
    """Build a validation result."""
    return ValidationResult(check_name=check_name, passed=passed, message=message)


def contains_value(data: Any, expected: str) -> bool:
    """Return true if expected appears as a nested key or scalar value."""
    if isinstance(data, dict):
        return any(str(key) == expected or contains_value(value, expected) for key, value in data.items())
    if isinstance(data, list):
        return any(contains_value(item, expected) for item in data)
    return str(data) == expected


def find_bgp_peer(data: dict[str, Any], peer_ip: str) -> dict[str, Any] | None:
    """Find a BGP peer object in common EOS JSON shapes."""
    vrfs = data.get("vrfs")
    if isinstance(vrfs, dict):
        for vrf_data in vrfs.values():
            if isinstance(vrf_data, dict):
                peers = vrf_data.get("peers")
                if isinstance(peers, dict) and isinstance(peers.get(peer_ip), dict):
                    return peers[peer_ip]

    peers = data.get("peers")
    if isinstance(peers, dict) and isinstance(peers.get(peer_ip), dict):
        return peers[peer_ip]

    return None


def peer_is_established(peer_data: dict[str, Any]) -> bool:
    """Return true when a BGP peer is established in common EOS fields."""
    state = peer_data.get("peerState") or peer_data.get("state")
    if isinstance(state, str):
        return state.lower() == "established"

    if peer_data.get("peerStateIdleReason"):
        return False

    return bool(peer_data.get("established") or peer_data.get("up"))


def validate_underlay_bgp(intent: FabricIntent, state_dir: Path) -> list[ValidationResult]:
    """Validate expected underlay BGP sessions are established."""
    results: list[ValidationResult] = []

    for device_name in intent.underlay.devices:
        try:
            bgp_data = read_json_artifact(state_dir, device_name, "show_ip_bgp_summary")
        except FileNotFoundError:
            results.append(
                result("underlay_bgp_established", False, f"{device_name}: BGP summary artifact missing")
            )
            continue

        for neighbor in underlay_neighbors(intent, device_name):
            peer_data = find_bgp_peer(bgp_data, neighbor.ip)
            if peer_data is None:
                results.append(
                    result(
                        "underlay_bgp_established",
                        False,
                        f"{device_name}: peer {neighbor.ip} ({neighbor.name}) not found",
                    )
                )
                continue

            passed = peer_is_established(peer_data)
            state = peer_data.get("peerState") or peer_data.get("state") or "unknown"
            results.append(
                result(
                    "underlay_bgp_established",
                    passed,
                    f"{device_name}: peer {neighbor.ip} ({neighbor.name}) is {state}",
                )
            )

    return results


def validate_vrfs(intent: FabricIntent, state_dir: Path) -> list[ValidationResult]:
    """Validate expected VRFs exist on leaf devices."""
    results: list[ValidationResult] = []

    for vrf_name, vrf in intent.overlay.vrfs.items():
        for device_name in vrf.devices:
            try:
                vrf_data = read_json_artifact(state_dir, device_name, "show_vrf")
                passed = contains_value(vrf_data, vrf_name)
            except FileNotFoundError:
                passed = False
            results.append(
                result(
                    "vrfs_exist",
                    passed,
                    f"{device_name}: VRF {vrf_name} {'exists' if passed else 'missing'}",
                )
            )

    return results


def validate_vlans(intent: FabricIntent, state_dir: Path) -> list[ValidationResult]:
    """Validate expected VLANs exist on leaf devices."""
    results: list[ValidationResult] = []

    for vlan_id, vlan in intent.overlay.vlans.items():
        for device_name in vlan.devices:
            try:
                vlan_data = read_json_artifact(state_dir, device_name, "show_vlan")
                passed = contains_value(vlan_data, str(vlan_id))
            except FileNotFoundError:
                passed = False
            results.append(
                result(
                    "vlans_exist",
                    passed,
                    f"{device_name}: VLAN {vlan_id} ({vlan.name}) {'exists' if passed else 'missing'}",
                )
            )

    return results


def validate_vnis(intent: FabricIntent, state_dir: Path) -> list[ValidationResult]:
    """Validate expected VXLAN VNIs exist on leaf devices."""
    results: list[ValidationResult] = []

    for vlan_id, vlan in intent.overlay.vlans.items():
        for device_name in vlan.devices:
            try:
                vni_data = read_json_artifact(state_dir, device_name, "show_vxlan_vni")
                passed = contains_value(vni_data, str(vlan.vni))
            except FileNotFoundError:
                passed = False
            results.append(
                result(
                    "vnis_exist",
                    passed,
                    f"{device_name}: VLAN {vlan_id} VNI {vlan.vni} {'exists' if passed else 'missing'}",
                )
            )

    return results


def validate_reachability(intent: FabricIntent, state_dir: Path) -> list[ValidationResult]:
    """Validate host reachability ping artifacts show success."""
    results: list[ValidationResult] = []

    for check in intent.overlay.same_vlan_reachability:
        try:
            output = read_text_artifact(state_dir, check.source, f"ping_{check.destination}")
            passed = " 0% packet loss" in output or "0% packet loss" in output
        except FileNotFoundError:
            output = ""
            passed = False

        results.append(
            result(
                "same_vlan_host_reachability",
                passed,
                f"{check.source}: ping {check.destination} over VLAN {check.vlan}/VNI {check.vni} "
                f"{'passed' if passed else 'failed'}",
            )
        )

    return results


def validate_state(
    sot_dir: Path | str = DEFAULT_SOT_DIR,
    state_dir: Path | str = DEFAULT_STATE_DIR,
) -> list[ValidationResult]:
    """Validate collected actual state against expected fabric intent."""
    intent = load_fabric_intent(sot_dir)
    root = Path(state_dir)

    results: list[ValidationResult] = []
    results.extend(validate_underlay_bgp(intent, root))
    results.extend(validate_vrfs(intent, root))
    results.extend(validate_vlans(intent, root))
    results.extend(validate_vnis(intent, root))
    results.extend(validate_reachability(intent, root))
    return results


def format_validation_results(results: list[ValidationResult]) -> str:
    """Format validation results for CLI output."""
    overall = "PASS" if all(item.passed for item in results) else "FAIL"
    lines = [overall, ""]
    for item in results:
        marker = "[PASS]" if item.passed else "[FAIL]"
        lines.append(f"{marker} {item.message}")
    return "\n".join(lines)
