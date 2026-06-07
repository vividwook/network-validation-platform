# network-validation-platform

EVPN/VXLAN fabric validation platform built as the next step after the Containerlab Clos fabric automation lab.

The first target lab is:

- 2 spines
- 2 leafs
- 4 hosts
- 2 VLANs
- 2 VNIs
- 1 VRF

## Goal

Model network intent as data, generate cEOS lab configuration, collect actual device state, compare expected and actual state, and produce human-readable validation results.

```text
YAML Source of Truth
        |
SoT validation
        |
Jinja2 config generation
        |
Containerlab deployment
        |
State collection
        |
Validation engine
        |
Markdown report / pytest / CI
```

## Repository Layout

```text
src/nvp/              Python package for loaders, models, collectors, validators, CLI
sot/                  YAML Source of Truth
templates/            Jinja2 EOS templates
containerlab/         Containerlab topology
generated-configs/    Generated cEOS startup configs
artifacts/state/      Collected device and host state
artifacts/reports/    Generated validation reports
tests/                Unit and integration tests
examples/             Example intent and reports
```

## Source of Truth

The initial lab intent lives in:

```text
sot/fabric.yml      Devices, interfaces, links, and hosts
sot/underlay.yml    eBGP underlay intent
sot/overlay.yml     EVPN, VRF, VLAN, and VNI intent
sot/services.yml    Reusable EOS service settings
sot/validation.yml  Validation levels and checks
```

The example topology uses `spine1`, `spine2`, `leaf1`, `leaf2`, and four hosts split across VLAN 10/VNI 10010 and VLAN 20/VNI 10020 inside VRF `TENANT_A`.

## Planned Workflow

```bash
make validate-sot
make generate
make deploy-lab
make collect-state
make validate
make report
```
