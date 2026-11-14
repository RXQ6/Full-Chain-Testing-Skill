"""Dependency-free structural checks for this skill; not a model behavior test."""
import argparse
import ast
import json
import re
import sys
import shlex
from urllib.parse import unquote
from pathlib import Path

def check(root):
    root = Path(root).resolve()
    errors = []
    name = None
    skill = root / "SKILL.md"
    try:
        content = skill.read_text(encoding="utf-8")
    except OSError:
        return ["SKILL.md missing"]
    fm = re.match(r"\A---\n(.*?)\n---\n", content, re.S)
    if not fm:
        errors.append("SKILL.md frontmatter missing")
    else:
        name = re.search(r"(?m)^name:\s*([a-z0-9-]+)\s*$", fm[1])
        desc = re.search(r"(?m)^description:\s*(.+)$", fm[1])
        if not name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name[1]) or len(name[1]) > 64:
            errors.append("skill name invalid")
        if not desc or not 1 <= len(desc[1]) <= 1024 or any(x in desc[1] for x in "<>"):
            errors.append("description invalid")
    for file in root.rglob("*.md"):
        body = file.read_text(encoding="utf-8")
        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body):
            if "://" in link or link.startswith("#"):
                continue
            try:
                relative = unquote(shlex.split(link)[0].split("#", 1)[0])
            except (ValueError, IndexError):
                errors.append(str(file.relative_to(root)) + ': malformed Markdown link')
                continue
            target = (file.parent / relative).resolve()
            if not target.is_relative_to(root) or not target.exists():
                errors.append(str(file.relative_to(root)) + ": broken or escaping local link")
    for file in root.rglob("*.py"):
        try:
            ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        except (SyntaxError, UnicodeError):
            errors.append(str(file.relative_to(root)) + ": invalid Python syntax")
    for file in (root / "assets").glob("*.json"):
        try:
            json.loads(file.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            errors.append(str(file.relative_to(root)) + ": invalid JSON template")
    try:
        metadata = (root / "agents/openai.yaml").read_text(encoding="utf-8")
        if not name or ("$" + name[1]) not in metadata:
            errors.append("UI metadata invocation policy/default prompt mismatch")
        description = re.search(r'(?m)^\s+short_description:\s*"([^"]+)"\s*$', metadata)
        if not description or not description[1].strip():
            errors.append("UI short description must be nonempty; host length guidelines are advisory")
    except OSError:
        errors.append("agents/openai.yaml missing")
    return errors

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir")
    args = parser.parse_args()
    errors = check(args.skill_dir)
    print(json.dumps({"valid": not errors, "errors": errors,
                      "limitation": "Checks this package's simple metadata format, links and syntax; not a general YAML parser or behavioral certification."},
                     ensure_ascii=False, indent=2))
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
