from pathlib import Path

from nvp.generate_configs import generate_configs, render_device_config
from nvp.load_sot import load_fabric_intent


def test_render_leaf_config_contains_overlay_config() -> None:
    intent = load_fabric_intent()

    rendered = render_device_config(intent, "leaf1")

    assert "hostname leaf1" in rendered
    assert "interface Vxlan1" in rendered
    assert "vxlan vlan 10 vni 10010" in rendered
    assert "vxlan vlan 20 vni 10020" in rendered
    assert "vxlan vrf TENANT_A vni 50001" in rendered
    assert "neighbor 10.0.11.0 remote-as 65001" in rendered


def test_render_spine_config_contains_underlay_only() -> None:
    intent = load_fabric_intent()

    rendered = render_device_config(intent, "spine1")

    assert "hostname spine1" in rendered
    assert "neighbor 10.0.11.1 remote-as 65101" in rendered
    assert "neighbor 10.0.12.1 remote-as 65102" in rendered
    assert "interface Vxlan1" not in rendered


def test_generate_configs_writes_one_file_per_device(tmp_path: Path) -> None:
    written_files = generate_configs(output_dir=tmp_path)

    assert sorted(path.name for path in written_files) == [
        "leaf1.cfg",
        "leaf2.cfg",
        "spine1.cfg",
        "spine2.cfg",
    ]
    assert (tmp_path / "leaf2.cfg").read_text(encoding="utf-8").startswith("!")
