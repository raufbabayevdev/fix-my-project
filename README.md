# fix-my-project

**One command to diagnose why your project is broken.**

`fix-my-project` is a tiny cross-platform CLI tool that scans your project folder for common Git, Node.js, Python, Docker, GitHub Actions, dependency, and secret-management mistakes.

It is designed to be simple, fast, beginner-friendly, and useful for real projects.

---

## Features

### Git checks

- Detects whether the folder is a Git repository.
- Detects unwanted files already tracked by Git.
- Warns about files that usually should not be committed.

Examples:

- `.env`
- `node_modules/`
- `.venv/`
- `venv/`
- `__pycache__/`
- `.DS_Store`
- `Thumbs.db`

---

### `.gitignore` checks

- Detects missing `.gitignore`.
- Detects missing important ignore patterns.
- Can create or update `.gitignore` with `--fix`.

Recommended ignore patterns include:

```gitignore
.env
.env.*
node_modules/
dist/
build/
.cache/
.DS_Store
Thumbs.db
__pycache__/
*.pyc
.venv/
venv/
````

---

### Environment file checks

Detects risky environment files such as:

```txt
.env
.env.local
.env.production
.env.development
```

If these files exist but are not ignored by `.gitignore`, the tool warns you.

This helps prevent accidentally committing secrets, API keys, tokens, and database URLs.

---

### Node.js project checks

If a `package.json` file exists, the tool detects the project as a Node.js project.

It checks for:

* Multiple package manager lockfiles.
* Missing lockfile.
* `node_modules/` not ignored.
* Invalid `package.json`.
* Missing common scripts.
* Duplicate packages in `dependencies` and `devDependencies`.

Supported lockfiles:

```txt
package-lock.json
pnpm-lock.yaml
yarn.lock
bun.lock
bun.lockb
```

---

### Python project checks

The tool detects Python projects by looking for files such as:

```txt
requirements.txt
pyproject.toml
setup.py
Pipfile
poetry.lock
```

It checks for:

* Virtual environments not ignored.
* Python cache folders not ignored.
* Multiple dependency formats.

Examples:

```txt
.venv/
venv/
__pycache__/
*.pyc
```

---

### Docker checks

The tool detects Docker usage by looking for:

```txt
Dockerfile
dockerfile
docker-compose.yml
docker-compose.yaml
compose.yml
```

It checks for:

* Missing `.dockerignore`.
* Risky `COPY . .` usage without `.dockerignore`.
* Usage of `latest` image tags in compose files.

---

### GitHub Actions checks

The tool scans workflow files in:

```txt
.github/workflows/
```

It checks for:

* Older `actions/checkout` versions.
* Missing dependency cache for Node.js workflows.
* Missing dependency cache for Python workflows.

---

### Large file checks

The tool detects files larger than 20 MB.

Large files can make your Git repository slow and heavy.

For large files, consider using:

* Git LFS
* GitHub Releases
* External storage

---

### Secret checks

The tool scans common text-based files for possible secrets.

It can detect patterns such as:

* Possible AWS Access Keys
* Possible GitHub tokens
* Possible private keys
* Possible generic API keys
* Possible passwords, secrets, and tokens

> This check is helpful, but it is not perfect. It may produce false positives or miss some secrets.

---

### JSON output

You can print the report as JSON:

```bash
python3 fix-my-project.py --json
```

This is useful for automation, GitHub Actions, dashboards, and integrations.

---

### Safe fix mode

You can apply safe fixes:

```bash
python3 fix-my-project.py --fix
```

Currently, safe fix mode can:

* Create a basic `.gitignore` if missing.
* Add important missing patterns to `.gitignore`.

It does **not** delete files or run dangerous commands.

---

## Installation

For now, clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/fix-my-project.git
cd fix-my-project
```

Run the tool:

```bash
python3 fix-my-project.py
```

---

## Usage

Scan the current folder:

```bash
python3 fix-my-project.py
```

Scan another project folder:

```bash
python3 fix-my-project.py /path/to/project
```

Example on Linux:

```bash
python3 ~/Desktop/fix-my-project.py ~/my-project
```

Example on Windows:

```powershell
python fix-my-project.py C:\Users\YourName\Desktop\my-project
```

Print JSON output:

```bash
python3 fix-my-project.py --json
```

Apply safe fixes:

```bash
python3 fix-my-project.py --fix
```

Show version:

```bash
python3 fix-my-project.py --version
```

---

## Example output

```txt
🩺 fix-my-project
Version: 0.1.0
Project: /home/user/my-project

⚠️ Project score: 72/100

1. ⚠️ Multiple package manager lockfiles detected
   Problem: Found: package-lock.json, pnpm-lock.yaml
   Fix: Use only one package manager per project to avoid dependency mismatch.

2. ❌ Environment file may be committed
   File: .env
   Problem: .env exists but does not appear to be ignored by .gitignore.
   Fix: Add '.env' and '.env.*' to .gitignore. Keep only .env.example in Git.

3. ⚠️ .dockerignore is missing
   File: .dockerignore
   Problem: Dockerfile exists but .dockerignore was not found.
   Fix: Create .dockerignore to avoid copying node_modules, .git, build output, and secrets into Docker images.

Done.
```

---

## Project score

The tool gives your project a health score from 0 to 100.

Basic scoring:

```txt
error   -15
warning -8
info    -2
```

Example:

```txt
Project score: 85/100
```

---

## Why this exists

Many projects fail to run because of small setup mistakes:

* Wrong package manager.
* Missing lockfile.
* Broken `.gitignore`.
* `.env` files not ignored.
* Docker context too large.
* Missing CI cache.
* Secrets accidentally committed.
* Large files inside the repository.

`fix-my-project` helps you find these problems quickly.

---

## Roadmap

Planned features:

* `--doctor node`
* `--doctor python`
* `--doctor docker`
* `--doctor github-actions`
* `--html-report`
* `--sarif`
* GitHub Actions integration
* Better secret detection
* Config file support
* Auto-fix confirmation mode
* Package release with `pipx`

---

## Safety

`fix-my-project` is designed to be safe.

By default, it only scans and reports problems.

With `--fix`, it only applies simple safe fixes such as creating or updating `.gitignore`.

It does not delete project files.

---

## Requirements

* Python 3.8+
* No external Python packages required

---

## License

MIT License

````

---
