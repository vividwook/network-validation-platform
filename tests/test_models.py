import pytest

from nvp.models import Device


def test_leaf_requires_vtep_loopback() -> None:
    with pytest.raises(ValueError, match="loopback1"):
        Device.from_dict(
            "leaf1",
            {
                "hostname": "leaf1",
                "role": "leaf",
                "platform": "arista_eos",
                "asn": 65101,
                "loopback0": "10.255.0.11/32",
                "interfaces": {},
            },
        )
