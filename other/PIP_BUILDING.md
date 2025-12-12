# Building TransformDash Pip Package - Step by Step Guide

This document records the exact steps we took to build and test the TransformDash pip package, including all issues we encountered and how we fixed them.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Issues We Found & Fixed](#issues-we-found--fixed)
4. [Building the Package](#building-the-package)
5. [Testing the Package](#testing-the-package)
6. [Publishing to TestPyPI](#publishing-to-testpypi)
7. [Publishing to PyPI](#publishing-to-pypi)
8. [Quick Reference Commands](#quick-reference-commands)

---

## Prerequisites

### Software Requirements

- Python 3.9+
- pip (latest version recommended)
- Virtual environment support

### Install Build Tools

```bash
# Activate your main venv
source venv/bin/activate

# Install build and twine
pip install build twine
```

---

## Initial Setup

### 1. Project Structure

Your project has a flat structure (not a single package):
```
transformdash/
├── ui/              # Web interface
├── ml/              # Machine learning module
├── models/          # SQL transformation models
├── transformations/ # Core transformation engine
├── orchestration/   # DAG orchestrator
├── connectors/      # Database connectors
├── setup.py         # Package configuration
├── pyproject.toml   # Modern package configuration
└── requirements.txt # Dependencies
```

### 2. Configuration Files

We use **both** `setup.py` and `pyproject.toml` for backwards compatibility.

---

## Issues We Found & Fixed

### Issue 1: Package Directory Doesn't Exist

**Error:**
```
error: package directory 'transformdash' does not exist
```

**Problem:**
`pyproject.toml` listed `"transformdash"` as a package, but we don't have a `transformdash/` directory.

**Fix:**
Updated `pyproject.toml` line 111:
```toml
# Before:
packages = ["transformdash", "ui", "ml", "models", "postgres"]

# After:
packages = ["ui", "ml", "models", "transformations", "orchestration", "connectors"]
```

### Issue 2: Missing Dependencies

**Error:**
```
ModuleNotFoundError: No module named 'jose'
```

**Problem:**
`python-jose[cryptography]` and `bcrypt` were in `requirements.txt` but missing from `setup.py` and `pyproject.toml`.

**Fix:**

**setup.py** - Added to `install_requires`:
```python
install_requires=[
    # ... existing packages ...
    "python-jose[cryptography]>=3.3.0",
    "bcrypt>=4.0.1",
    # ... rest of packages ...
]
```

**pyproject.toml** - Added to `dependencies`:
```toml
dependencies = [
    # ... existing packages ...
    "python-jose[cryptography]>=3.3.0",
    "bcrypt>=4.0.1",
    # ... rest of packages ...
]
```

---

## Building the Package

### Step 1: Clean Previous Builds

```bash
# Remove any old build artifacts
rm -rf build/ dist/ *.egg-info/
```

### Step 2: Build the Package

```bash
# Activate venv
source venv/bin/activate

# Build both wheel and source distribution
python -m build
```

**Output:**
```
Successfully built transformdash-1.0.0.tar.gz and transformdash-1.0.0-py3-none-any.whl
```

**Files Created:**
- `dist/transformdash-1.0.0-py3-none-any.whl` (220KB) - Wheel distribution
- `dist/transformdash-1.0.0.tar.gz` (216KB) - Source distribution

### Step 3: Verify Build Quality

```bash
twine check dist/*
```

**Expected Output:**
```
Checking dist/transformdash-1.0.0-py3-none-any.whl: PASSED
Checking dist/transformdash-1.0.0.tar.gz: PASSED
```

---

## Testing the Package

### Why Test Locally?

Testing locally before publishing helps catch:
- Missing dependencies
- Import errors
- File path issues
- Configuration problems

### Test Process

#### 1. Create Test Environment

```bash
# Create isolated test environment
python3 -m venv test_env

# Activate it
source test_env/bin/activate
```

#### 2. Install from Local Build

```bash
# Install the wheel file
pip install dist/transformdash-1.0.0-py3-none-any.whl
```

This installs all dependencies and the package itself.

#### 3. Test Imports

```bash
# Test that all modules can be imported
python -c "import ui.app; import ml; import transformations; print('✅ SUCCESS!')"
```

**Expected Output:**
```
✅ SUCCESS!
```

#### 4. Cleanup

```bash
# Deactivate test environment
deactivate

# Remove test environment
rm -rf test_env
```

### What We Tested

✅ **Package Installation** - Package installs without errors
✅ **Dependency Resolution** - All dependencies are installed correctly
✅ **Module Imports** - All main modules can be imported:
   - `ui.app` - Web application
   - `ml` - Machine learning module
   - `transformations` - Transformation engine
   - `orchestration` - DAG orchestrator
   - `connectors` - Database connectors

---

## Publishing to TestPyPI

**IMPORTANT:** Always test on TestPyPI before publishing to production PyPI!

### Why TestPyPI?

- Safe environment to test the publishing process
- Verify package installation works for end users
- Check package metadata displays correctly
- No risk to your production package

### Step 1: Create TestPyPI Account

1. Go to https://test.pypi.org/account/register/
2. Fill in your details (email, username, password)
3. Verify your email address

### Step 2: Create API Token

1. Go to https://test.pypi.org/manage/account/token/
2. Click "Add API token"
3. Token name: `transformdash-upload`
4. Scope: Select "Entire account" (or specific project after first upload)
5. Click "Add token"
6. **IMPORTANT:** Copy the token immediately (starts with `pypi-`)
7. Save it securely - you won't see it again!

### Step 3: Upload to TestPyPI

```bash
# Make sure you're in your main venv
source venv/bin/activate

# Upload to TestPyPI
twine upload --repository testpypi dist/*
```

**Prompts:**
```
Enter your username: __token__
Enter your password: [paste your TestPyPI token here]
```

**Expected Output:**
```
Uploading distributions to https://test.pypi.org/legacy/
Uploading transformdash-1.0.0-py3-none-any.whl
Uploading transformdash-1.0.0.tar.gz
View at: https://test.pypi.org/project/transformdash/1.0.0/
```

### Step 4: Test Install from TestPyPI

```bash
# Create fresh test environment
python3 -m venv testpypi_test
source testpypi_test/bin/activate

# Install from TestPyPI
# Note: --extra-index-url needed because TestPyPI doesn't have all dependencies
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  transformdash

# Test it works
python -c "import ui.app; print('✅ TestPyPI installation works!')"

# Cleanup
deactivate
rm -rf testpypi_test
```

### Step 5: Verify on Web

Visit your package page:
```
https://test.pypi.org/project/transformdash/
```

Check:
- ✅ Package description displays correctly
- ✅ README renders properly
- ✅ Version number is correct
- ✅ Dependencies are listed
- ✅ Project URLs work

---

## Publishing to PyPI

**Only do this after TestPyPI works perfectly!**

### Step 1: Create PyPI Account

1. Go to https://pypi.org/account/register/
2. Fill in your details (use same email as TestPyPI if you want)
3. Verify your email address

### Step 2: Create API Token

1. Go to https://pypi.org/manage/account/token/
2. Click "Add API token"
3. Token name: `transformdash-upload`
4. Scope: "Entire account" (for now)
5. Copy and save the token securely

### Step 3: Upload to PyPI

```bash
# Make sure you're in venv
source venv/bin/activate

# Upload to production PyPI
twine upload dist/*
```

**Prompts:**
```
Enter your username: __token__
Enter your password: [paste your PyPI token here]
```

**Expected Output:**
```
Uploading distributions to https://upload.pypi.org/legacy/
Uploading transformdash-1.0.0-py3-none-any.whl
Uploading transformdash-1.0.0.tar.gz
View at: https://pypi.org/project/transformdash/1.0.0/
```

### Step 4: Verify Installation

```bash
# Create test environment
python3 -m venv pypi_test
source pypi_test/bin/activate

# Install from PyPI (just like users will)
pip install transformdash

# Test
python -c "import transformdash; print('✅ PyPI installation works!')"

# Cleanup
deactivate
rm -rf pypi_test
```

### Step 5: Announce

Your package is now public! Users can install with:
```bash
pip install transformdash
```

Visit: https://pypi.org/project/transformdash/

---

## Quick Reference Commands

### Build Process

```bash
# Complete build workflow
rm -rf build/ dist/ *.egg-info/
source venv/bin/activate
python -m build
twine check dist/*
```

### Local Testing

```bash
# Quick local test
python3 -m venv test_env
source test_env/bin/activate
pip install dist/transformdash-1.0.0-py3-none-any.whl
python -c "import ui.app; import ml; print('✅ Works!')"
deactivate
rm -rf test_env
```

### Publishing

```bash
# TestPyPI
twine upload --repository testpypi dist/*

# Production PyPI
twine upload dist/*
```

### Installing (End Users)

```bash
# From PyPI
pip install transformdash

# From TestPyPI (for testing)
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  transformdash
```

---

## Version Updates

When releasing a new version:

### 1. Update Version Numbers

Edit **both** files:

**setup.py:**
```python
setup(
    name="transformdash",
    version="1.0.1",  # Update here
    ...
)
```

**pyproject.toml:**
```toml
[project]
name = "transformdash"
version = "1.0.1"  # Update here
```

### 2. Rebuild and Publish

```bash
# Clean and rebuild
rm -rf build/ dist/ *.egg-info/
python -m build
twine check dist/*

# Test on TestPyPI first
twine upload --repository testpypi dist/*

# Then publish to PyPI
twine upload dist/*
```

### 3. Tag Release in Git

```bash
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1
```

---

## Troubleshooting

### Error: "File already exists"

**Problem:** PyPI doesn't allow overwriting versions.

**Solution:** Increment version number in both `setup.py` and `pyproject.toml`, rebuild, and upload.

### Error: "Invalid distribution"

**Problem:** Missing required files (README.md, LICENSE, etc.)

**Solution:**
```bash
# Verify files exist
ls README.md LICENSE requirements.txt

# Check MANIFEST.in includes them
cat MANIFEST.in
```

### Error: "ModuleNotFoundError" after install

**Problem:** Missing dependencies in `setup.py` or `pyproject.toml`.

**Solution:**
1. Check `requirements.txt` for the missing package
2. Add it to both `setup.py` (`install_requires`) and `pyproject.toml` (`dependencies`)
3. Rebuild the package
4. Test locally again

### Warning: License deprecated

**Problem:** Using `license = { text = "MIT" }` format.

**Solution:** This is a warning, not an error. Package will still build. To fix in the future, update to SPDX format.

---

## Files Changed During This Process

### Modified:
- `pyproject.toml` - Fixed packages list, added missing dependencies
- `setup.py` - Added missing dependencies
- `MANIFEST.in` - Added `prune other` to exclude dev files

### Created:
- `dist/transformdash-1.0.0-py3-none-any.whl` - Wheel distribution
- `dist/transformdash-1.0.0.tar.gz` - Source distribution
- `other/PIP_BUILDING.md` - This document
- `other/PUBLISHING_QUICK.md` - Quick reference guide

---

## What's Included in the Package

When users install via `pip install transformdash`, they get:

### Python Modules:
- `ui/` - Web application
- `ml/` - Machine learning module
- `models/` - SQL transformation models (bronze, silver, gold)
- `transformations/` - Core transformation engine
- `orchestration/` - DAG orchestrator
- `connectors/` - Database connectors

### Static Assets:
- `ui/templates/` - HTML templates
- `ui/static/css/` - Stylesheets
- `ui/static/js/` - JavaScript files
- `models/**/*.sql` - SQL transformation files
- `models/**/*.yml` - YAML configuration files

### Configuration:
- `README.md` - Project documentation
- `LICENSE` - MIT License
- `.env.example` - Example environment file
- `requirements.txt` - Dependency list
- `docker-compose.yml` - Docker configuration
- `Dockerfile` - Container image
- `k8s/` - Kubernetes configurations

### ML Assets:
- `ml/models/registry.json` - Model registry metadata
- Training scripts and examples

---

## What's Excluded from the Package

Thanks to `MANIFEST.in`, these are NOT included:

- `tests/` - Test files
- `venv/` - Virtual environment
- `.git/` - Git history
- `.github/` - GitHub Actions
- `.idea/` - IDE settings
- `.vscode/` - VS Code settings
- `other/` - Development documentation
- `data/` - Data files
- `logs/` - Log files
- `__pycache__/` - Python cache
- `*.pyc`, `*.log` - Build artifacts

---

## Security Notes

### API Tokens

**NEVER** commit API tokens to git!

Store them securely:
1. Password manager
2. Environment variables
3. `.pypirc` file (with `chmod 600`)

### `.pypirc` Setup (Optional)

To avoid entering credentials each time:

```bash
# Create ~/.pypirc
cat > ~/.pypirc << 'EOF'
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_PYPI_TOKEN

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TESTPYPI_TOKEN
EOF

# Secure it
chmod 600 ~/.pypirc
```

Then uploading is simpler:
```bash
twine upload --repository testpypi dist/*  # TestPyPI
twine upload dist/*                         # PyPI
```

---

## Resources

- **TestPyPI**: https://test.pypi.org
- **PyPI**: https://pypi.org
- **Twine Docs**: https://twine.readthedocs.io/
- **Packaging Guide**: https://packaging.python.org/
- **Semantic Versioning**: https://semver.org/

---

## Changelog

### 2024-12-05
- Initial package build
- Fixed package configuration (removed non-existent "transformdash" package)
- Added missing dependencies (`python-jose[cryptography]`, `bcrypt`)
- Successfully tested locally
- Created publishing documentation

---

**Ready to publish!** Follow the TestPyPI steps above to test, then publish to PyPI when ready.
