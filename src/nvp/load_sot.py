"""Load YAML Source of Truth files into typed fabric intent models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nvp.models import (
    Device,
    FabricIntent,
    FabricMetadata,
    Host,
    Overlay,
    Services,
    Underlay,
    ValidationSettings,
    require_mapping,
)


DEFAULT_SOT_DIR = Path("sot")


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping from disk."""
    with path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")

    return data


def load_fabric_intent(sot_dir: Path | str = DEFAULT_SOT_DIR) -> FabricIntent:
    """Load all SoT files and return a typed fabric intent."""
    root = Path(sot_dir)

    fabric_source = load_yaml(root / "fabric.yml")
    underlay_source = load_yaml(root / "underlay.yml")
    overlay_source = load_yaml(root / "overlay.yml")
    services_source = load_yaml(root / "services.yml")
    validation_source = load_yaml(root / "validation.yml")

    raw_devices = require_mapping(fabric_source.get("devices"), "devices")
    raw_hosts = require_mapping(fabric_source.get("hosts"), "hosts")

    intent = FabricIntent(
        fabric=FabricMetadata.from_dict(
            require_mapping(fabric_source.get("fabric"), "fabric")
        ),
        devices={
            name: Device.from_dict(name, require_mapping(value, f"devices.{name}"))
            for name, value in raw_devices.items()
        },
        hosts={
            name: Host.from_dict(name, require_mapping(value, f"hosts.{name}"))
            for name, value in raw_hosts.items()
        },
        underlay=Underlay.from_dict(
            require_mapping(underlay_source.get("underlay"), "underlay")
        ),
        overlay=Overlay.from_dict(
            require_mapping(overlay_source.get("overlay"), "overlay")
        ),
        services=Services.from_dict(
            require_mapping(services_source.get("services"), "services")
        ),
        validation=ValidationSettings.from_dict(
            require_mapping(validation_source.get("validation"), "validation")
        ),
    )
    intent.validate_references()
    return intent


def summarize_intent(intent: FabricIntent) -> str:
    """Return a compact human-readable intent summary."""
    spine_count = sum(1 for device in intent.devices.values() if device.role == "spine")
    leaf_count = sum(1 for device in intent.devices.values() if device.role == "leaf")
    enabled_levels = [
        name for name, level in intent.validation.levels.items() if level.enabled
    ]

    return "\n".join(
        [
            f"Fabric: {intent.fabric.name}",
            f"Devices: {len(intent.devices)} ({spine_count} spines, {leaf_count} leafs)",
            f"Hosts: {len(intent.hosts)}",
            f"VRFs: {len(intent.overlay.vrfs)}",
            f"VLANs: {len(intent.overlay.vlans)}",
            "VNIs: "
            + ", ".join(str(vlan.vni) for vlan in intent.overlay.vlans.values()),
            "Enabled validation levels: " + ", ".join(enabled_levels),
        ]
    )
