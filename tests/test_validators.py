import json
from pathlib import Path

from nvp.generate_configs import underlay_neighbors
from nvp.load_sot import load_fabric_intent
from nvp.validators import format_validation_results, validate_state


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def build_passing_state(tmp_path: Path) -> None:
    intent = load_fabric_intent()

    for device_name in intent.devices:
        peers = {
            neighbor.ip: {"peerState": "Established"}
            for neighbor in underlay_neighbors(intent, device_name)
        }
        write_json(
            tmp_path / f"{device_name}_show_ip_bgp_summary.json",
            {"vrfs": {"default": {"peers": peers}}},
        )

    for leaf_name in ["leaf1", "leaf2"]:
        write_json(tmp_path / f"{leaf_name}_show_vrf.json", {"vrfs": {"TENANT_A": {}}})
        write_json(
            tmp_path / f"{leaf_name}_show_vlan.json",
            {"vlans": {"10": {"name": "BLUE"}, "20": {"name": "GREEN"}}},
        )
        write_json(
            tmp_path / f"{leaf_name}_show_vxlan_vni.json",
            {"vnis": {"10010": {"vlan": 10}, "10020": {"vlan": 20}}},
        )

    write_text(
        tmp_path / "host1_ping_host3.txt",
        "3 packets transmitted, 3 received, 0% packet loss\n",
    )
    write_text(
        tmp_path / "host2_ping_host4.txt",
        "3 packets transmitted, 3 received, 0% packet loss\n",
    )


def test_validate_state_passes_with_expected_artifacts(tmp_path: Path) -> None:
    build_passing_state(tmp_path)

    results = validate_state(state_dir=tmp_path)

    assert results
    assert all(item.passed for item in results)
    assert format_validation_results(results).startswith("PASS")


def test_validate_state_fails_when_bgp_peer_is_idle(tmp_path: Path) -> None:
    build_passing_state(tmp_path)
    data = json.loads((tmp_path / "leaf1_show_ip_bgp_summary.json").read_text())
    data["vrfs"]["default"]["peers"]["10.0.11.0"]["peerState"] = "Idle"
    write_json(tmp_path / "leaf1_show_ip_bgp_summary.json", data)

    results = validate_state(state_dir=tmp_path)

    assert any(not item.passed for item in results)
    assert "FAIL" in format_validation_results(results)
    assert any("leaf1: peer 10.0.11.0" in item.message for item in results)


def test_validate_state_fails_when_vni_is_missing(tmp_path: Path) -> None:
    build_passing_state(tmp_path)
    write_json(tmp_path / "leaf2_show_vxlan_vni.json", {"vnis": {"10010": {}}})

    results = validate_state(state_dir=tmp_path)

    assert any(
        not item.passed and "leaf2: VLAN 20 VNI 10020" in item.message
        for item in results
    )
