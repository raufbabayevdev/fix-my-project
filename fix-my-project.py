#!/usr/bin/env python3
"""
fix-my-project.py

A tiny cross-platform project doctor.
Scans a project folder for common Git, Node.js, Python, Docker, CI,
source-file, metadata, and secret-management mistakes.

Works with:
- Windows
- Linux
- macOS

Requires:
- Python 3.8+
- No external packages
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


VERSION = "0.1.1"


# -----------------------------
# Data models
# -----------------------------

@dataclass
class Finding:
    level: str          # "info", "warning", "error"
    title: str
    message: str
    recommendation: str
    file: Optional[str] = None


@dataclass
class Report:
    project_path: str
    score: int
    findings: List[Finding]


# -----------------------------
# Helpers
# -----------------------------

def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def safe_write_text(path: Path, content: str) -> bool:
    try:
        path.write_text(content, encoding="utf-8")
        return True
    except Exception:
        return False


def exists(root: Path, name: str) -> bool:
    return (root / name).exists()


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except Exception:
        return str(path)


def run_command(command: List[str], cwd: Path) -> Tuple[int, str, str]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
        return completed.returncode, completed.stdout.strip(), completed.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"Command not found: {command[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def append_to_gitignore(root: Path, patterns: List[str]) -> bool:
    gitignore = root / ".gitignore"

    existing = ""
    if gitignore.exists():
        existing = safe_read_text(gitignore)

    lines = existing.splitlines()
    existing_set = {line.strip() for line in lines}

    to_add = []
    for pattern in patterns:
        if pattern not in existing_set:
            to_add.append(pattern)

    if not to_add:
        return True

    if existing.strip():
        new_content = existing.rstrip() + "\n\n# Added by fix-my-project\n" + "\n".join(to_add) + "\n"
    else:
        new_content = "# Added by fix-my-project\n" + "\n".join(to_add) + "\n"

    return safe_write_text(gitignore, new_content)


def is_ignored_by_gitignore(root: Path, target: str) -> bool:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return False

    content = safe_read_text(gitignore)
    patterns = set()

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.add(line)

    normalized = target.replace("\\", "/").strip("/")

    possible_patterns = {
        normalized,
        f"/{normalized}",
        f"{normalized}/",
        f"/{normalized}/",
    }

    if normalized.startswith(".env"):
        possible_patterns.update({
            ".env",
            ".env.*",
            "*.env",
            ".env.local",
            ".env.development",
            ".env.production",
            ".env.test",
        })

    if normalized in {"node_modules", ".venv", "venv", "__pycache__"}:
        possible_patterns.update({
            normalized,
            f"{normalized}/",
            f"/{normalized}/",
        })

    return bool(patterns.intersection(possible_patterns))


def find_files(
    root: Path,
    max_files: int = 5000,
    skip_dirs: Optional[set] = None,
) -> List[Path]:
    if skip_dirs is None:
        skip_dirs = {
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "env",
            "__pycache__",
            ".next",
            ".nuxt",
            "dist",
            "build",
            ".cache",
            ".idea",
            ".vscode",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
        }

    result: List[Path] = []

    for current_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for filename in files:
            if len(result) >= max_files:
                return result

            path = Path(current_root) / filename
            result.append(path)

    return result


def has_any_file(root: Path, names: List[str]) -> bool:
    return any(exists(root, name) for name in names)


# -----------------------------
# Checks
# -----------------------------

def check_git_repo(root: Path) -> List[Finding]:
    findings: List[Finding] = []

    if not exists(root, ".git"):
        findings.append(Finding(
            level="info",
            title="Git repository not found",
            message="This folder does not look like a Git repository.",
            recommendation="Run 'git init' if this project should be tracked with Git.",
        ))

    return findings


def check_project_metadata(root: Path) -> List[Finding]:
    findings: List[Finding] = []

    readme_files = [
        "README.md",
        "README.txt",
        "README",
        "readme.md",
        "Readme.md",
    ]

    license_files = [
        "LICENSE",
        "LICENSE.md",
        "LICENSE.txt",
        "LICENCE",
        "LICENCE.md",
        "COPYING",
    ]

    has_readme = has_any_file(root, readme_files)
    has_license = has_any_file(root, license_files)

    if not has_readme:
        findings.append(Finding(
            level="warning",
            title="README is missing",
            message="No README file was found.",
            recommendation="Add a README.md with project description, installation steps, usage examples, and requirements.",
        ))

    if not has_license:
        findings.append(Finding(
            level="info",
            title="LICENSE is missing",
            message="No license file was found.",
            recommendation="Add a license such as MIT if this is an open-source project.",
        ))

    return findings


def check_gitignore(root: Path, fix: bool) -> List[Finding]:
    findings: List[Finding] = []

    gitignore = root / ".gitignore"

    recommended_patterns = [
        ".env",
        ".env.*",
        "node_modules/",
        "dist/",
        "build/",
        ".cache/",
        ".DS_Store",
        "Thumbs.db",
        "__pycache__/",
        "*.pyc",
        ".venv/",
        "venv/",
        "env/",
    ]

    if not gitignore.exists():
        findings.append(Finding(
            level="warning",
            title=".gitignore is missing",
            message="No .gitignore file was found.",
            recommendation="Create a .gitignore file to avoid committing secrets, dependencies, and build output.",
            file=".gitignore",
        ))

        if fix:
            created = safe_write_text(
                gitignore,
                "# Created by fix-my-project\n" + "\n".join(recommended_patterns) + "\n"
            )
            if created:
                findings.append(Finding(
                    level="info",
                    title=".gitignore created",
                    message="A basic .gitignore file was created.",
                    recommendation="Review it and adjust it for your project.",
                    file=".gitignore",
                ))

        return findings

    content = safe_read_text(gitignore)

    missing = []
    for pattern in recommended_patterns:
        if pattern not in content:
            missing.append(pattern)

    important_missing = [
        p for p in missing
        if p in [".env", ".env.*", "node_modules/", ".venv/", "venv/", "env/", "__pycache__/", "*.pyc"]
    ]

    if important_missing:
        findings.append(Finding(
            level="warning",
            title=".gitignore is missing important patterns",
            message=f"Missing patterns: {', '.join(important_missing)}",
            recommendation="Add these patterns to avoid committing secrets, dependency folders, virtual environments, and cache files.",
            file=".gitignore",
        ))

        if fix:
            ok = append_to_gitignore(root, important_missing)
            if ok:
                findings.append(Finding(
                    level="info",
                    title=".gitignore updated",
                    message="Important ignore patterns were added.",
                    recommendation="Review .gitignore before committing.",
                    file=".gitignore",
                ))

    return findings


def check_env_files(root: Path) -> List[Finding]:
    findings: List[Finding] = []

    env_files = [
        p for p in root.iterdir()
        if p.is_file() and (p.name == ".env" or p.name.startswith(".env."))
    ]

    safe_env_examples = {
        ".env.example",
        ".env.sample",
        ".env.template",
        ".env.example.local",
    }

    for env_file in env_files:
        if env_file.name in safe_env_examples:
            continue

        if not is_ignored_by_gitignore(root, env_file.name):
            findings.append(Finding(
                level="error",
                title="Environment file may be committed",
                message=f"{env_file.name} exists but does not appear to be ignored by .gitignore.",
                recommendation="Add '.env' and '.env.*' to .gitignore. Keep only .env.example in Git.",
                file=env_file.name,
            ))

    return findings


def check_node_project(root: Path) -> List[Finding]:
    findings: List[Finding] = []

    package_json = root / "package.json"
    if not package_json.exists():
        return findings

    lockfiles = []
    for name in ["package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock"]:
        if exists(root, name):
            lockfiles.append(name)

    if len(lockfiles) > 1:
        findings.append(Finding(
            level="warning",
            title="Multiple package manager lockfiles detected",
            message=f"Found: {', '.join(lockfiles)}",
            recommendation="Use only one package manager per project to avoid dependency mismatch.",
        ))

    if len(lockfiles) == 0:
        findings.append(Finding(
            level="warning",
            title="No lockfile found",
            message="package.json exists but no lockfile was found.",
            recommendation="Run your package manager install command to create a lockfile, for example: npm install, pnpm install, yarn install, or bun install.",
            file="package.json",
        ))

    node_modules = root / "node_modules"
    if node_modules.exists() and not is_ignored_by_gitignore(root, "node_modules"):
        findings.append(Finding(
            level="warning",
            title="node_modules may be committed",
            message="node_modules exists but does not appear to be ignored.",
            recommendation="Add 'node_modules/' to .gitignore.",
            file="node_modules",
        ))

    content = safe_read_text(package_json)
    try:
        data = json.loads(content)
    except Exception:
        findings.append(Finding(
            level="error",
            title="Invalid package.json",
            message="package.json could not be parsed as valid JSON.",
            recommendation="Fix the JSON syntax in package.json.",
            file="package.json",
        ))
        return findings

    scripts = data.get("scripts", {})
    if isinstance(scripts, dict):
        if not any(k in scripts for k in ["dev", "start", "build", "test"]):
            findings.append(Finding(
                level="info",
                title="No common npm scripts found",
                message="package.json does not include dev/start/build/test scripts.",
                recommendation="Add useful scripts so contributors know how to run, build, or test the project.",
                file="package.json",
            ))

    dependencies = data.get("dependencies", {})
    dev_dependencies = data.get("devDependencies", {})

    if isinstance(dependencies, dict) and isinstance(dev_dependencies, dict):
        duplicated = sorted(set(dependencies.keys()).intersection(set(dev_dependencies.keys())))
        if duplicated:
            findings.append(Finding(
                level="warning",
                title="Duplicate dependencies detected",
                message=f"These packages are in both dependencies and devDependencies: {', '.join(duplicated[:10])}",
                recommendation="Keep each package in only one dependency section.",
                file="package.json",
            ))

    return findings


def check_python_project(root: Path) -> List[Finding]:
    findings: List[Finding] = []

    has_python_config = any([
        exists(root, "requirements.txt"),
        exists(root, "pyproject.toml"),
        exists(root, "setup.py"),
        exists(root, "Pipfile"),
        exists(root, "poetry.lock"),
    ])

    if not has_python_config:
        return findings

    if exists(root, "requirements.txt") and exists(root, "pyproject.toml"):
        findings.append(Finding(
            level="info",
            title="Multiple Python dependency formats detected",
            message="Both requirements.txt and pyproject.toml exist.",
            recommendation="This can be okay, but make sure they do not define conflicting dependency sources.",
        ))

    for venv_name in [".venv", "venv", "env"]:
        venv_path = root / venv_name
        if venv_path.exists() and not is_ignored_by_gitignore(root, venv_name):
            findings.append(Finding(
                level="warning",
                title="Python virtual environment may be committed",
                message=f"{venv_name} exists but does not appear to be ignored.",
                recommendation=f"Add '{venv_name}/' to .gitignore.",
                file=venv_name,
            ))

    pycache_dirs = list(root.glob("**/__pycache__"))
    if pycache_dirs and not is_ignored_by_gitignore(root, "__pycache__"):
        findings.append(Finding(
            level="warning",
            title="Python cache folders may be committed",
            message="__pycache__ folders exist but do not appear to be ignored.",
            recommendation="Add '__pycache__/' and '*.pyc' to .gitignore.",
        ))

    return findings


def check_source_files(root: Path) -> List[Finding]:
    findings: List[Finding] = []

    files = find_files(root, max_files=5000)

    python_files = [p for p in files if p.suffix.lower() == ".py"]

    js_files = [
        p for p in files
        if p.suffix.lower() in [".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"]
    ]

    shell_files = [
        p for p in files
        if p.suffix.lower() in [".sh", ".bash", ".zsh"]
    ]

    if python_files:
        has_python_config = any([
            exists(root, "requirements.txt"),
            exists(root, "pyproject.toml"),
            exists(root, "setup.py"),
            exists(root, "Pipfile"),
            exists(root, "poetry.lock"),
        ])

        if not has_python_config:
            findings.append(Finding(
                level="info",
                title="Python files found without dependency file",
                message=f"Found {len(python_files)} Python file(s), but no requirements.txt, pyproject.toml, setup.py, Pipfile, or poetry.lock.",
                recommendation="This is only a problem if the project uses external Python packages. If it only uses the standard library, you can ignore this.",
            ))

    if js_files:
        if not exists(root, "package.json"):
            findings.append(Finding(
                level="info",
                title="JavaScript/TypeScript files found without package.json",
                message=f"Found {len(js_files)} JavaScript/TypeScript file(s), but no package.json.",
                recommendation="This is only a problem if the project uses Node.js dependencies, npm scripts, or a build tool.",
            ))

    if shell_files:
        for script in shell_files[:10]:
            content = safe_read_text(script)
            lines = content.splitlines()
            first_line = lines[0] if lines else ""

            if not first_line.startswith("#!"):
                findings.append(Finding(
                    level="info",
                    title="Shell script may be missing shebang",
                    message=f"{rel(root, script)} does not start with a shebang line.",
                    recommendation="Add a shebang such as '#!/usr/bin/env bash' if this file is meant to be executable.",
                    file=rel(root, script),
                ))

    return findings


def check_docker(root: Path) -> List[Finding]:
    findings: List[Finding] = []

    dockerfile_exists = exists(root, "Dockerfile") or exists(root, "dockerfile")
    compose_exists = exists(root, "docker-compose.yml") or exists(root, "docker-compose.yaml") or exists(root, "compose.yml")

    if dockerfile_exists and not exists(root, ".dockerignore"):
        findings.append(Finding(
            level="warning",
            title=".dockerignore is missing",
            message="Dockerfile exists but .dockerignore was not found.",
            recommendation="Create .dockerignore to avoid copying node_modules, .git, build output, and secrets into Docker images.",
            file=".dockerignore",
        ))

    dockerfile = root / "Dockerfile"
    if dockerfile.exists():
        content = safe_read_text(dockerfile)

        if "COPY . ." in content and not exists(root, ".dockerignore"):
            findings.append(Finding(
                level="warning",
                title="Docker build context may be too large",
                message="Dockerfile uses 'COPY . .' but .dockerignore is missing.",
                recommendation="Add a .dockerignore file to reduce image build time and avoid copying secrets.",
                file="Dockerfile",
            ))

        if re.search(r"(?i)apt-get install", content) and "-y" not in content:
            findings.append(Finding(
                level="info",
                title="Possible interactive apt install",
                message="Dockerfile uses apt-get install without '-y'.",
                recommendation="Use 'apt-get install -y ...' in Docker builds.",
                file="Dockerfile",
            ))

    if compose_exists:
        compose_files = ["docker-compose.yml", "docker-compose.yaml", "compose.yml"]
        for name in compose_files:
            p = root / name
            if p.exists():
                content = safe_read_text(p)
                if re.search(r":latest\b", content):
                    findings.append(Finding(
                        level="info",
                        title="Docker image uses latest tag",
                        message=f"{name} appears to use the 'latest' image tag.",
                        recommendation="Pin image versions for more predictable builds.",
                        file=name,
                    ))

    return findings


def check_github_actions(root: Path) -> List[Finding]:
    findings: List[Finding] = []

    workflows = root / ".github" / "workflows"
    if not workflows.exists():
        return findings

    workflow_files = list(workflows.glob("*.yml")) + list(workflows.glob("*.yaml"))

    for wf in workflow_files:
        content = safe_read_text(wf)
        relative_file = rel(root, wf)

        if "actions/checkout@" in content and "actions/checkout@v4" not in content:
            findings.append(Finding(
                level="info",
                title="GitHub Actions checkout may be outdated",
                message="Workflow uses actions/checkout but not v4.",
                recommendation="Consider using actions/checkout@v4.",
                file=relative_file,
            ))

        if "node-version" in content and "cache:" not in content:
            findings.append(Finding(
                level="info",
                title="GitHub Actions dependency cache missing",
                message="Node setup was detected but no cache setting was found.",
                recommendation="Use cache: 'npm', 'pnpm', or 'yarn' with actions/setup-node.",
                file=relative_file,
            ))

        if "pip install" in content and "cache:" not in content and "actions/cache" not in content:
            findings.append(Finding(
                level="info",
                title="Python dependency cache may be missing",
                message="pip install was detected but no cache setup was found.",
                recommendation="Consider using actions/setup-python with pip cache.",
                file=relative_file,
            ))

    return findings


def check_large_files(root: Path) -> List[Finding]:
    findings: List[Finding] = []

    files = find_files(root, max_files=5000)
    large_files = []

    for p in files:
        try:
            size_mb = p.stat().st_size / (1024 * 1024)
        except Exception:
            continue

        if size_mb >= 20:
            large_files.append((p, size_mb))

    if large_files:
        large_files = sorted(large_files, key=lambda x: x[1], reverse=True)
        top = large_files[:5]
        message = ", ".join([f"{rel(root, p)} ({size:.1f} MB)" for p, size in top])

        findings.append(Finding(
            level="warning",
            title="Large files detected",
            message=f"Large files found: {message}",
            recommendation="Avoid committing large binaries. Use Git LFS, release assets, or external storage if needed.",
        ))

    return findings


def check_secrets(root: Path) -> List[Finding]:
    findings: List[Finding] = []

    secret_patterns: Dict[str, re.Pattern] = {
        "Possible AWS Access Key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "Possible GitHub token": re.compile(r"\bghp_[A-Za-z0-9_]{30,}\b"),
        "Possible GitHub fine-grained token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
        "Possible private key": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
        "Possible generic API key": re.compile(
            r"(?i)\b(api_key|apikey|secret|token|password)\b\s*[:=]\s*['\"][^'\"]{12,}['\"]"
        ),
    }

    allowed_extensions = {
        ".js", ".ts", ".jsx", ".tsx",
        ".py", ".env", ".json", ".yml", ".yaml",
        ".toml", ".ini", ".cfg", ".txt", ".md",
        ".sh", ".bash", ".zsh",
    }

    files = find_files(root, max_files=5000)

    for p in files:
        if p.suffix.lower() not in allowed_extensions and p.name != ".env":
            continue

        # Skip lockfiles because false positives are common.
        if p.name in ["package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock"]:
            continue

        content = safe_read_text(p)
        if not content:
            continue

        for secret_name, pattern in secret_patterns.items():
            if pattern.search(content):
                findings.append(Finding(
                    level="error",
                    title=secret_name,
                    message=f"A possible secret was found in {rel(root, p)}.",
                    recommendation="Remove the secret, rotate it if it was real, and use environment variables instead.",
                    file=rel(root, p),
                ))
                break

    return findings


def check_git_tracked_bad_files(root: Path) -> List[Finding]:
    findings: List[Finding] = []

    if not exists(root, ".git"):
        return findings

    code, stdout, _stderr = run_command(["git", "ls-files"], cwd=root)
    if code != 0:
        return findings

    tracked = stdout.splitlines()

    bad_patterns = [
        "node_modules/",
        ".env",
        ".venv/",
        "venv/",
        "env/",
        "__pycache__/",
        ".DS_Store",
        "Thumbs.db",
    ]

    bad_tracked = []

    for item in tracked:
        normalized = item.replace("\\", "/")

        for bad in bad_patterns:
            if normalized == bad or normalized.startswith(bad):
                bad_tracked.append(item)
                break

    if bad_tracked:
        examples = ", ".join(bad_tracked[:10])
        findings.append(Finding(
            level="error",
            title="Unwanted files are tracked by Git",
            message=f"These files/folders should usually not be tracked: {examples}",
            recommendation="Remove them from Git tracking with: git rm -r --cached <path>",
        ))

    return findings


# -----------------------------
# Scoring and output
# -----------------------------

def calculate_score(findings: List[Finding]) -> int:
    score = 100

    for finding in findings:
        if finding.level == "error":
            score -= 15
        elif finding.level == "warning":
            score -= 8
        elif finding.level == "info":
            score -= 2

    return max(0, min(100, score))


def print_report(report: Report) -> None:
    print()
    print("🩺 fix-my-project")
    print(f"Version: {VERSION}")
    print(f"Project: {report.project_path}")
    print()

    if report.score >= 85:
        emoji = "✅"
    elif report.score >= 60:
        emoji = "⚠️"
    else:
        emoji = "❌"

    print(f"{emoji} Project score: {report.score}/100")
    print()

    if not report.findings:
        print("✅ No common problems found.")
        print()
        return

    for index, finding in enumerate(report.findings, start=1):
        if finding.level == "error":
            icon = "❌"
        elif finding.level == "warning":
            icon = "⚠️"
        else:
            icon = "ℹ️"

        print(f"{index}. {icon} {finding.title}")

        if finding.file:
            print(f"   File: {finding.file}")

        print(f"   Problem: {finding.message}")
        print(f"   Fix: {finding.recommendation}")
        print()

    print("Done.")


def build_json_report(report: Report) -> str:
    return json.dumps(asdict(report), indent=2, ensure_ascii=False)


# -----------------------------
# Main
# -----------------------------

def scan_project(root: Path, fix: bool = False) -> Report:
    findings: List[Finding] = []

    checks = [
        check_git_repo,
        lambda r: check_gitignore(r, fix=fix),
        check_project_metadata,
        check_env_files,
        check_node_project,
        check_python_project,
        check_source_files,
        check_docker,
        check_github_actions,
        check_large_files,
        check_secrets,
        check_git_tracked_bad_files,
    ]

    for check in checks:
        try:
            findings.extend(check(root))
        except Exception as e:
            findings.append(Finding(
                level="warning",
                title="A check failed",
                message=f"{getattr(check, '__name__', 'unknown_check')} failed: {e}",
                recommendation="Report this issue or run the tool again with a smaller project.",
            ))

    score = calculate_score(findings)

    return Report(
        project_path=str(root),
        score=score,
        findings=findings,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="fix-my-project",
        description="Scan a project for common setup, Git, dependency, Docker, CI, source-file, metadata, and secret mistakes.",
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project folder to scan. Default: current folder.",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Print report as JSON.",
    )

    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply safe fixes, such as creating or updating .gitignore.",
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.version:
        print(VERSION)
        return 0

    root = Path(args.path).expanduser().resolve()

    if not root.exists():
        print(f"Error: path does not exist: {root}", file=sys.stderr)
        return 1

    if not root.is_dir():
        print(f"Error: path is not a folder: {root}", file=sys.stderr)
        return 1

    report = scan_project(root, fix=args.fix)

    if args.json:
        print(build_json_report(report))
    else:
        print_report(report)

    # Exit code:
    # 0 = healthy enough
    # 1 = errors found
    has_error = any(f.level == "error" for f in report.findings)
    return 1 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
    
