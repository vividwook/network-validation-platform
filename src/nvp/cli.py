"""Command-line entry points for the Network Validation Platform."""

from __future__ import annotations

import argparse
import sys

from nvp.collectors import collect_state
from nvp.generate_configs import generate_configs
from nvp.load_sot import load_fabric_intent, summarize_intent
from nvp.validators import format_validation_results, validate_state


COMMANDS = (
    "validate-sot",
    "generate",
    "collect-state",
    "validate",
    "report",
)


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""
    parser = argparse.ArgumentParser(
        prog="nvp",
        description="Validate EVPN/VXLAN fabric intent and state.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in COMMANDS:
        command_parser = subparsers.add_parser(command)
        if command in {"validate-sot", "generate", "collect-state", "validate"}:
            command_parser.add_argument(
                "--sot-dir",
                default="sot",
                help="Directory containing Source of Truth YAML files.",
            )
        if command == "generate":
            command_parser.add_argument(
                "--output-dir",
                default="generated-configs",
                help="Directory to write generated startup configs.",
            )
            command_parser.add_argument(
                "--template-dir",
                default="templates",
                help="Directory containing Jinja2 templates.",
            )
        if command == "collect-state":
            command_parser.add_argument(
                "--output-dir",
                default="artifacts/state",
                help="Directory to write collected state artifacts.",
            )
            command_parser.add_argument(
                "--lab-name",
                default=None,
                help="Containerlab lab name. Defaults to fabric.name from SoT.",
            )
        if command == "validate":
            command_parser.add_argument(
                "--state-dir",
                default="artifacts/state",
                help="Directory containing collected state artifacts.",
            )

    return parser


def main() -> None:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "validate-sot":
        intent = load_fabric_intent(args.sot_dir)
        print("SoT validation passed.")
        print(summarize_intent(intent))
        return

    if args.command == "generate":
        written_files = generate_configs(
            sot_dir=args.sot_dir,
            output_dir=args.output_dir,
            template_dir=args.template_dir,
        )
        print("Generated startup configs:")
        for path in written_files:
            print(f"- {path}")
        return

    if args.command == "collect-state":
        artifacts = collect_state(
            sot_dir=args.sot_dir,
            output_dir=args.output_dir,
            lab_name=args.lab_name,
        )
        print("Collected state artifacts:")
        for artifact in artifacts:
            print(f"- {artifact.path}")
        return

    if args.command == "validate":
        results = validate_state(sot_dir=args.sot_dir, state_dir=args.state_dir)
        print(format_validation_results(results))
        if not all(item.passed for item in results):
            sys.exit(1)
        return

    print(f"{args.command} is not implemented yet.")


if __name__ == "__main__":
    main()
