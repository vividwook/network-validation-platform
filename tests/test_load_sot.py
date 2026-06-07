from nvp.load_sot import load_fabric_intent, summarize_intent


def test_load_fabric_intent_from_default_sot() -> None:
    intent = load_fabric_intent()

    assert intent.fabric.name == "evpn-lab"
    assert len(intent.devices) == 4
    assert len(intent.hosts) == 4
    assert set(intent.overlay.vrfs) == {"TENANT_A"}
    assert intent.overlay.vlans[10].vni == 10010
    assert intent.overlay.vlans[20].vni == 10020


def test_summarize_intent_includes_key_counts() -> None:
    summary = summarize_intent(load_fabric_intent())

    assert "Devices: 4 (2 spines, 2 leafs)" in summary
    assert "Hosts: 4" in summary
    assert "VRFs: 1" in summary
    assert "VLANs: 2" in summary
