"""Generate cEOS startup configs from fabric intent."""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_interface
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from nvp.load_sot import DEFAULT_SOT_DIR, load_fabric_intent
from nvp.models import Device, FabricIntent, Vlan, Vrf


DEFAULT_TEMPLATE_DIR = Path("templates")
DEFAULT_OUTPUT_DIR = Path("generated-configs")
DEFAULT_TEMPLATE_NAME = "eos_evpn.j2"


@dataclass(frozen=True)
class BgpNeighbor:
    name: str
    ip: str
    remote_as: int


def ip_without_prefix(value: str) -> str:
    """Return the IP portion of an interface string."""
    return str(ip_interface(value).ip)


def device_vlans(intent: FabricIntent, device_name: str) -> dict[int, Vlan]:
    """Return VLANs that should be configured on a device."""
    if intent.devices[device_name].role != "leaf":
        return {}

    return {
        vlan_id: vlan
        for vlan_id, vlan in intent.overlay.vlans.items()
        if device_name in vlan.devices
    }


def device_vrfs(intent: FabricIntent, device_name: str) -> dict[str, Vrf]:
    """Return VRFs that should be configured on a device."""
    if intent.devices[device_name].role != "leaf":
        return {}

    return {
        vrf_name: vrf
        for vrf_name, vrf in intent.overlay.vrfs.items()
        if device_name in vrf.devices
    }


def underlay_neighbors(intent: FabricIntent, device_name: str) -> list[BgpNeighbor]:
    """Build underlay BGP neighbor settings from fabric peer links."""
    device = intent.devices[device_name]
    underlay_device = intent.underlay.devices[device_name]
    neighbors: list[BgpNeighbor] = []

    for neighbor_name in underlay_device.neighbors:
        local_interface = next(
            (
                interface
                for interface in device.interfaces.values()
                if interface.peer == neighbor_name
            ),
            None,
        )
        if local_interface is None:
            raise ValueError(f"{device_name} has no interface toward {neighbor_name}")

        peer_device = intent.devices[neighbor_name]
        peer_interface = peer_device.interfaces.get(local_interface.peer_interface)
        if peer_interface is None or peer_interface.ip_address is None:
            raise ValueError(
                f"{neighbor_name} missing peer interface {local_interface.peer_interface}"
            )

        neighbors.append(
            BgpNeighbor(
                name=neighbor_name,
                ip=ip_without_prefix(peer_interface.ip_address),
                remote_as=peer_device.asn,
            )
        )

    return neighbors


def advertised_networks(intent: FabricIntent, device_name: str) -> list[str]:
    """Resolve advertised network tokens such as loopback0 into prefixes."""
    device = intent.devices[device_name]
    underlay_device = intent.underlay.devices[device_name]
    networks: list[str] = []

    for network in underlay_device.advertised_networks:
        if network == "loopback0":
            networks.append(device.loopback0)
        elif network == "loopback1":
            if device.loopback1 is None:
                raise ValueError(f"{device_name} cannot advertise missing loopback1")
            networks.append(device.loopback1)
        else:
            networks.append(network)

    return networks


def render_device_config(
    intent: FabricIntent,
    device_name: str,
    template_name: str = DEFAULT_TEMPLATE_NAME,
    template_dir: Path | str = DEFAULT_TEMPLATE_DIR,
) -> str:
    """Render one device startup config."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    template = env.get_template(template_name)
    device: Device = intent.devices[device_name]

    return template.render(
        fabric=intent.fabric,
        device=device,
        services=intent.services,
        underlay=intent.underlay,
        overlay=intent.overlay,
        router_id=ip_without_prefix(device.loopback0),
        bgp_neighbors=underlay_neighbors(intent, device_name),
        advertised_networks=advertised_networks(intent, device_name),
        vlans=device_vlans(intent, device_name),
        vrfs=device_vrfs(intent, device_name),
    )


def generate_configs(
    sot_dir: Path | str = DEFAULT_SOT_DIR,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    template_dir: Path | str = DEFAULT_TEMPLATE_DIR,
) -> list[Path]:
    """Generate startup configs for all fabric devices."""
    intent = load_fabric_intent(sot_dir)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    written_files: list[Path] = []
    for device_name in intent.devices:
        rendered = render_device_config(
            intent=intent,
            device_name=device_name,
            template_dir=template_dir,
        )
        path = destination / f"{device_name}.cfg"
        path.write_text(rendered, encoding="utf-8")
        written_files.append(path)

    return written_files
