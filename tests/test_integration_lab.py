import os
from pathlib import Path

import pytest

from nvp.collectors import collect_state
from nvp.validators import format_validation_results, validate_state


pytestmark = pytest.mark.integration


RUN_LIVE_TESTS = os.getenv("NVP_RUN_LIVE_TESTS") == "1"
LAB_NAME = os.getenv("NVP_LAB_NAME", "evpn-lab")


@pytest.mark.skipif(
    not RUN_LIVE_TESTS,
    reason="set NVP_RUN_LIVE_TESTS=1 to run live Containerlab integration tests",
)
def test_live_lab_collects_state_artifacts(tmp_path: Path) -> None:
    artifacts = collect_state(output_dir=tmp_path, lab_name=LAB_NAME)

    assert artifacts
    assert (tmp_path / "leaf1_show_vxlan_vni.json").exists()
    assert (tmp_path / "spine1_show_ip_bgp_summary.json").exists()
    assert (tmp_path / "host1_ip_addr.txt").exists()
    assert (tmp_path / "host1_ping_host3.txt").exists()


@pytest.mark.skipif(
    not RUN_LIVE_TESTS,
    reason="set NVP_RUN_LIVE_TESTS=1 to run live Containerlab integration tests",
)
def test_live_lab_validates_against_sot(tmp_path: Path) -> None:
    collect_state(output_dir=tmp_path, lab_name=LAB_NAME)
    results = validate_state(state_dir=tmp_path)
    failed = [item.message for item in results if not item.passed]

    assert not failed, format_validation_results(results)
