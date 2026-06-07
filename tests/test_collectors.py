from pathlib import Path

from nvp.collectors import collect_state
from nvp.eos_client import container_name


def test_container_name_matches_containerlab_naming() -> None:
    assert container_name("evpn-lab", "leaf1") == "clab-evpn-lab-leaf1"


def test_collect_state_writes_expected_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_run_eos_command(lab_name, device_name, command, json_output=True):
        assert lab_name == "evpn-lab"
        assert json_output is True
        return '{"command": "' + command + '", "device": "' + device_name + '"}'

    def fake_run_host_command(lab_name, host_name, command):
        assert lab_name == "evpn-lab"
        return f"{host_name}: {' '.join(command)}\n"

    monkeypatch.setattr("nvp.collectors.run_eos_command", fake_run_eos_command)
    monkeypatch.setattr("nvp.collectors.run_host_command", fake_run_host_command)

    artifacts = collect_state(output_dir=tmp_path)

    assert len(artifacts) == 42
    assert (tmp_path / "leaf1_show_vxlan_vni.json").exists()
    assert (tmp_path / "spine1_show_ip_bgp_summary.json").exists()
    assert (tmp_path / "host1_ip_addr.txt").exists()
    assert (tmp_path / "host1_ping_host3.txt").exists()
