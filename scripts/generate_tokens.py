"""Generate the explicitly supported DESIGN.md token schema without dependencies."""

import argparse
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def generate():
    frontmatter = (ROOT / "DESIGN.md").read_text().split("---", 2)[1]
    sections = {"colors": "color", "rounded": "radius", "spacing": "space"}
    section = role = None
    tokens = []
    for line in frontmatter.splitlines():
        if line and not line.startswith(" "):
            section = line.split(":", 1)[0]
        match = re.fullmatch(r"  ([\w-]+): [\"'](.*)[\"']", line)
        if section in sections and match:
            tokens.append(f"  --{sections[section]}-{match[1]}: {match[2]};")
        if section == "typography":
            role_match = re.fullmatch(r"  ([\w-]+):", line)
            if role_match:
                role = role_match[1]
            family = re.fullmatch(r"    fontFamily: '(.*)'", line)
            if family:
                tokens.append(f"  --font-{role}: {family[1]};")
    if len(tokens) != 19:
        raise ValueError("DESIGN.md schema changed: update token mapping explicitly.")
    return "/* Generated from DESIGN.md. Run npm run tokens; do not edit. */\n:root {\n" + "\n".join(tokens) + "\n}\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    destination = ROOT / "web/src/tokens.css"
    content = generate()
    if arguments.check:
        if not destination.exists() or destination.read_text() != content:
            raise SystemExit("Design tokens drifted. Run npm --prefix web run tokens.")
        print("Design tokens match DESIGN.md.")
    else:
        destination.write_text(content)
