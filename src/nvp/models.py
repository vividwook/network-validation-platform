"""Typed data models for fabric intent and validation results."""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address, ip_interface
from typing import Any, Literal


DeviceRole = Literal["spine", "leaf"]
InterfaceType = Literal["routed", "access"]
Platform = Literal["arista_eos"]


def require_mapping(data: Any, label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")
    return data


def require_list(data: Any, label: str) -> list[Any]:
    if not isinstance(data, list):
        raise ValueError(f"{label} must be a list")
    return data


def require_str(data: Any, label: str) -> str:
    if not isinstance(data, str) or not data:
        raise ValueError(f"{label} must be a non-empty string")
    return data


def require_int(data: Any, label: str) -> int:
    if not isinstance(data, int):
        raise ValueError(f"{label} must be an integer")
    return data


def validate_ip(value: str, label: str) -> str:
    ip_address(value)
    return value


def validate_ip_interface(value: str, label: str) -> str:
    ip_interface(value)
    return value


@dataclass(frozen=True)
class FabricMetadata:
    name: str
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FabricMetadata":
        return cls(
            name=require_str(data.get("name"), "fabric.name"),
            description=str(data.get("description", "")),
        )


@dataclass(frozen=True)
class Interface:
    description: str
    type: InterfaceType
    peer: str
    peer_interface: str
    ip_address: str | None = None
    vlan: int | None = None

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "Interface":
        interface_type = require_str(data.get("type"), f"{name}.type")
        if interface_type not in ("routed", "access"):
            raise ValueError(f"{name}.type must be routed or access")

        ip_value = data.get("ip_address")
        vlan = data.get("vlan")

        if interface_type == "routed":
            if ip_value is None:
                raise ValueError(f"{name} routed interfaces require ip_address")
            ip_value = validate_ip_interface(str(ip_value), f"{name}.ip_address")

        if interface_type == "access":
            if vlan is None:
                raise ValueError(f"{name} access interfaces require vlan")
            vlan = require_int(vlan, f"{name}.vlan")

        return cls(
            description=require_str(data.get("description"), f"{name}.description"),
            type=interface_type,
            peer=require_str(data.get("peer"), f"{name}.peer"),
            peer_interface=require_str(
                data.get("peer_interface"), f"{name}.peer_interface"
            ),
            ip_address=ip_value,
            vlan=vlan,
        )


@dataclass(frozen=True)
class Device:
    hostname: str
    role: DeviceRole
    platform: Platform
    asn: int
    loopback0: str
    interfaces: dict[str, Interface]
    loopback1: str | None = None

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "Device":
        role = require_str(data.get("role"), f"devices.{name}.role")
        if role not in ("spine", "leaf"):
            raise ValueError(f"devices.{name}.role must be spine or leaf")

        platform = require_str(data.get("platform"), f"devices.{name}.platform")
        if platform != "arista_eos":
            raise ValueError(f"devices.{name}.platform must be arista_eos")

        loopback1 = data.get("loopback1")
        if loopback1 is not None:
            loopback1 = validate_ip_interface(str(loopback1), f"devices.{name}.loopback1")
        if role == "leaf" and loopback1 is None:
            raise ValueError(f"devices.{name} requires loopback1 for VTEP source")

        raw_interfaces = require_mapping(
            data.get("interfaces"), f"devices.{name}.interfaces"
        )

        return cls(
            hostname=require_str(data.get("hostname"), f"devices.{name}.hostname"),
            role=role,
            platform=platform,
            asn=require_int(data.get("asn"), f"devices.{name}.asn"),
            loopback0=validate_ip_interface(
                str(data.get("loopback0")), f"devices.{name}.loopback0"
            ),
            loopback1=loopback1,
            interfaces={
                interface_name: Interface.from_dict(
                    f"devices.{name}.interfaces.{interface_name}",
                    require_mapping(interface_data, interface_name),
                )
                for interface_name, interface_data in raw_interfaces.items()
            },
        )


@dataclass(frozen=True)
class Host:
    attached_to: str
    interface: str
    leaf_interface: str
    vlan: int
    ip: str
    prefix_length: int
    gateway: str

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "Host":
        prefix_length = require_int(data.get("prefix_length"), f"hosts.{name}.prefix_length")
        if prefix_length < 1 or prefix_length > 32:
            raise ValueError(f"hosts.{name}.prefix_length must be between 1 and 32")

        return cls(
            attached_to=require_str(data.get("attached_to"), f"hosts.{name}.attached_to"),
            interface=require_str(data.get("interface"), f"hosts.{name}.interface"),
            leaf_interface=require_str(
                data.get("leaf_interface"), f"hosts.{name}.leaf_interface"
            ),
            vlan=require_int(data.get("vlan"), f"hosts.{name}.vlan"),
            ip=validate_ip(str(data.get("ip")), f"hosts.{name}.ip"),
            prefix_length=prefix_length,
            gateway=validate_ip(str(data.get("gateway")), f"hosts.{name}.gateway"),
        )


@dataclass(frozen=True)
class UnderlayDevice:
    peer_group: str
    neighbors: list[str]
    advertised_networks: list[str]

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "UnderlayDevice":
        return cls(
            peer_group=require_str(data.get("peer_group"), f"underlay.devices.{name}.peer_group"),
            neighbors=[
                require_str(item, f"underlay.devices.{name}.neighbors")
                for item in require_list(
                    data.get("neighbors"), f"underlay.devices.{name}.neighbors"
                )
            ],
            advertised_networks=[
                require_str(item, f"underlay.devices.{name}.advertised_networks")
                for item in require_list(
                    data.get("advertised_networks"),
                    f"underlay.devices.{name}.advertised_networks",
                )
            ],
        )


@dataclass(frozen=True)
class Underlay:
    routing_protocol: Literal["ebgp"]
    maximum_paths: int
    devices: dict[str, UnderlayDevice]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Underlay":
        protocol = require_str(data.get("routing_protocol"), "underlay.routing_protocol")
        if protocol != "ebgp":
            raise ValueError("underlay.routing_protocol must be ebgp")

        defaults = require_mapping(data.get("defaults"), "underlay.defaults")
        maximum_paths = require_int(
            defaults.get("maximum_paths"), "underlay.defaults.maximum_paths"
        )
        if maximum_paths < 1:
            raise ValueError("underlay.defaults.maximum_paths must be >= 1")

        raw_devices = require_mapping(data.get("devices"), "underlay.devices")
        return cls(
            routing_protocol=protocol,
            maximum_paths=maximum_paths,
            devices={
                name: UnderlayDevice.from_dict(name, require_mapping(value, name))
                for name, value in raw_devices.items()
            },
        )


@dataclass(frozen=True)
class RouteTargets:
    import_value: str
    export: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RouteTargets":
        return cls(
            import_value=require_str(data.get("import"), "route_targets.import"),
            export=require_str(data.get("export"), "route_targets.export"),
        )


@dataclass(frozen=True)
class Vrf:
    vni: int
    route_distinguisher: str
    route_targets: RouteTargets
    devices: list[str]

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "Vrf":
        return cls(
            vni=require_int(data.get("vni"), f"overlay.vrfs.{name}.vni"),
            route_distinguisher=require_str(
                data.get("route_distinguisher"),
                f"overlay.vrfs.{name}.route_distinguisher",
            ),
            route_targets=RouteTargets.from_dict(
                require_mapping(data.get("route_targets"), f"overlay.vrfs.{name}.route_targets")
            ),
            devices=[
                require_str(item, f"overlay.vrfs.{name}.devices")
                for item in require_list(data.get("devices"), f"overlay.vrfs.{name}.devices")
            ],
        )


@dataclass(frozen=True)
class Vlan:
    name: str
    vrf: str
    vni: int
    gateway: str
    devices: list[str]

    @classmethod
    def from_dict(cls, vlan_id: int, data: dict[str, Any]) -> "Vlan":
        return cls(
            name=require_str(data.get("name"), f"overlay.vlans.{vlan_id}.name"),
            vrf=require_str(data.get("vrf"), f"overlay.vlans.{vlan_id}.vrf"),
            vni=require_int(data.get("vni"), f"overlay.vlans.{vlan_id}.vni"),
            gateway=validate_ip_interface(
                str(data.get("gateway")), f"overlay.vlans.{vlan_id}.gateway"
            ),
            devices=[
                require_str(item, f"overlay.vlans.{vlan_id}.devices")
                for item in require_list(
                    data.get("devices"), f"overlay.vlans.{vlan_id}.devices"
                )
            ],
        )


@dataclass(frozen=True)
class ReachabilityCheck:
    name: str
    source: str
    destination: str
    vlan: int
    vni: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReachabilityCheck":
        name = require_str(data.get("name"), "overlay.reachability.same_vlan.name")
        return cls(
            name=name,
            source=require_str(data.get("source"), f"reachability.{name}.source"),
            destination=require_str(
                data.get("destination"), f"reachability.{name}.destination"
            ),
            vlan=require_int(data.get("vlan"), f"reachability.{name}.vlan"),
            vni=require_int(data.get("vni"), f"reachability.{name}.vni"),
        )


@dataclass(frozen=True)
class Overlay:
    control_plane: Literal["evpn"]
    vtep_source_interface: Literal["Loopback1"]
    spine_route_servers: list[str]
    vrfs: dict[str, Vrf]
    vlans: dict[int, Vlan]
    same_vlan_reachability: list[ReachabilityCheck]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Overlay":
        control_plane = require_str(data.get("control_plane"), "overlay.control_plane")
        if control_plane != "evpn":
            raise ValueError("overlay.control_plane must be evpn")

        vtep_source = require_str(
            data.get("vtep_source_interface"), "overlay.vtep_source_interface"
        )
        if vtep_source != "Loopback1":
            raise ValueError("overlay.vtep_source_interface must be Loopback1")

        evpn = require_mapping(data.get("evpn"), "overlay.evpn")
        raw_vrfs = require_mapping(data.get("vrfs"), "overlay.vrfs")
        raw_vlans = require_mapping(data.get("vlans"), "overlay.vlans")
        reachability = require_mapping(data.get("reachability"), "overlay.reachability")

        return cls(
            control_plane=control_plane,
            vtep_source_interface=vtep_source,
            spine_route_servers=[
                require_str(item, "overlay.evpn.spine_route_servers")
                for item in require_list(
                    evpn.get("spine_route_servers"), "overlay.evpn.spine_route_servers"
                )
            ],
            vrfs={
                name: Vrf.from_dict(name, require_mapping(value, name))
                for name, value in raw_vrfs.items()
            },
            vlans={
                require_int(vlan_id, "overlay.vlans key"): Vlan.from_dict(
                    require_int(vlan_id, "overlay.vlans key"),
                    require_mapping(value, str(vlan_id)),
                )
                for vlan_id, value in raw_vlans.items()
            },
            same_vlan_reachability=[
                ReachabilityCheck.from_dict(require_mapping(item, "reachability item"))
                for item in require_list(
                    reachability.get("same_vlan"), "overlay.reachability.same_vlan"
                )
            ],
        )


@dataclass(frozen=True)
class Services:
    raw: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Services":
        return cls(raw=data)


@dataclass(frozen=True)
class ValidationLevel:
    enabled: bool
    checks: list[str]

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "ValidationLevel":
        enabled = data.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError(f"validation.levels.{name}.enabled must be boolean")
        return cls(
            enabled=enabled,
            checks=[
                require_str(item, f"validation.levels.{name}.checks")
                for item in require_list(data.get("checks"), f"validation.levels.{name}.checks")
            ],
        )


@dataclass(frozen=True)
class ValidationSettings:
    levels: dict[str, ValidationLevel]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationSettings":
        raw_levels = require_mapping(data.get("levels"), "validation.levels")
        return cls(
            levels={
                name: ValidationLevel.from_dict(name, require_mapping(value, name))
                for name, value in raw_levels.items()
            }
        )


@dataclass(frozen=True)
class FabricIntent:
    fabric: FabricMetadata
    devices: dict[str, Device]
    hosts: dict[str, Host]
    underlay: Underlay
    overlay: Overlay
    services: Services
    validation: ValidationSettings

    def validate_references(self) -> None:
        device_names = set(self.devices)
        host_names = set(self.hosts)

        for name, device in self.devices.items():
            if device.hostname != name:
                raise ValueError(f"device key {name} must match hostname {device.hostname}")
            for interface in device.interfaces.values():
                if interface.peer not in device_names | host_names:
                    raise ValueError(f"{name} references unknown peer {interface.peer}")

        for name, host in self.hosts.items():
            if host.attached_to not in device_names:
                raise ValueError(f"{name} references unknown leaf {host.attached_to}")

        for name, underlay_device in self.underlay.devices.items():
            if name not in device_names:
                raise ValueError(f"underlay references unknown device {name}")
            for neighbor in underlay_device.neighbors:
                if neighbor not in device_names:
                    raise ValueError(f"{name} underlay references unknown neighbor {neighbor}")

        leaf_names = {
            name for name, device in self.devices.items() if device.role == "leaf"
        }
        for vrf_name, vrf in self.overlay.vrfs.items():
            for device in vrf.devices:
                if device not in leaf_names:
                    raise ValueError(f"VRF {vrf_name} references non-leaf device {device}")

        for vlan_id, vlan in self.overlay.vlans.items():
            if vlan.vrf not in self.overlay.vrfs:
                raise ValueError(f"VLAN {vlan_id} references unknown VRF {vlan.vrf}")
            for device in vlan.devices:
                if device not in leaf_names:
                    raise ValueError(f"VLAN {vlan_id} references non-leaf device {device}")

        for check in self.overlay.same_vlan_reachability:
            if check.source not in host_names or check.destination not in host_names:
                raise ValueError(f"reachability check {check.name} references unknown host")
            if check.vlan not in self.overlay.vlans:
                raise ValueError(f"reachability check {check.name} references unknown VLAN")
            expected_vni = self.overlay.vlans[check.vlan].vni
            if check.vni != expected_vni:
                raise ValueError(
                    f"reachability check {check.name} VNI {check.vni} "
                    f"does not match VLAN {check.vlan} VNI {expected_vni}"
                )


@dataclass(frozen=True)
class ValidationResult:
    check_name: str
    passed: bool
    message: str
