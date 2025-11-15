# Publishing TransformDash to PyPI

This guide explains how to publish TransformDash as a pip package so users can install it with `pip install transformdash`.

## Table of Contents

1. [Understanding pip install -e](#understanding-pip-install--e)
2. [Prerequisites](#prerequisites)
3. [Preparing for Publication](#preparing-for-publication)
4. [Publishing to TestPyPI (Recommended First)](#publishing-to-testpypi)
5. [Publishing to PyPI (Production)](#publishing-to-pypi)
6. [After Publishing](#after-publishing)
7. [Version Management](#version-management)

---

## Understanding `pip install -e`

### What does `pip install -e ".[ml]"` mean?

This command installs your package in **editable mode** (also called **development mode**):

```bash
pip install -e ".[ml]"
```

Breaking it down:
- **`pip install`** - Install a package
- **`-e`** - Editable/development mode
- **`.`** - Current directory (install from here)
- **`[ml]`** - Include optional dependencies from the `ml` group

**Key point:** This works **locally WITHOUT publishing to PyPI** because it installs directly from your source code.

### Editable vs Normal Installation

**Editable Mode (`pip install -e .`):**
- Creates a link to your source code
- Changes to code are immediately reflected
- Great for development
- No need to reinstall after code changes

**Normal Mode (`pip install .`):**
- Copies files to site-packages
- Changes require reinstalling
- Used for testing production behavior
- Files are installed like a real package

### Optional Dependencies

In `setup.py` and `pyproject.toml`, we defined several optional dependency groups:

```python
extras_require={
    "dev": ["pytest", "black", "flake8", ...],
    "ml": ["xgboost", "lightgbm", ...],
    "scraping": ["selenium", "beautifulsoup4", ...],
    "orchestration": ["celery", "prefect", ...],
    "bigdata": ["pyspark", ...],
}
```

Users can install specific combinations:
```bash
# Just core dependencies
pip install transformdash

# With ML support
pip install transformdash[ml]

# With multiple extras
pip install transformdash[ml,scraping]

# With everything
pip install transformdash[ml,scraping,orchestration,bigdata]
```

---

## Prerequisites

### 1. Create PyPI Account

Create accounts on both:
- **TestPyPI** (for testing): https://test.pypi.org/account/register/
- **PyPI** (production): https://pypi.org/account/register/

### 2. Set Up API Tokens

**TestPyPI:**
1. Go to https://test.pypi.org/manage/account/token/
2. Create a new API token with scope "Entire account"
3. Save the token (starts with `pypi-`)

**PyPI:**
1. Go to https://pypi.org/manage/account/token/
2. Create a new API token
3. Save the token

### 3. Install Build Tools

```bash
pip install --upgrade build twine
```

---

## Preparing for Publication

### 1. Verify Package Metadata

Check `setup.py` and `pyproject.toml` have:
- ✅ Correct version number
- ✅ Valid author info and email
- ✅ Correct GitHub URL
- ✅ All required dependencies
- ✅ Proper classifiers

### 2. Update Version

Edit version in **both** files:

**`setup.py`:**
```python
setup(
    name="transformdash",
    version="1.0.0",  # Update this
    ...
)
```

**`pyproject.toml`:**
```toml
[project]
name = "transformdash"
version = "1.0.0"  # Update this
```

### 3. Ensure All Files Are Included

Check `MANIFEST.in` includes everything needed:
```bash
# Test what will be included
python setup.py sdist
tar -tzf dist/transformdash-1.0.0.tar.gz | less
```

### 4. Clean Previous Builds

```bash
# Remove old build artifacts
rm -rf build/ dist/ *.egg-info/
```

### 5. Run Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Check code quality
black --check .
flake8 .
```

---

## Publishing to TestPyPI

**Always test on TestPyPI first** before publishing to production PyPI!

### Step 1: Build the Package

```bash
# Build both wheel and source distribution
python -m build
```

This creates:
- `dist/transformdash-1.0.0-py3-none-any.whl` (wheel)
- `dist/transformdash-1.0.0.tar.gz` (source)

### Step 2: Check the Distribution

```bash
# Verify package quality
twine check dist/*
```

Should show:
```
Checking dist/transformdash-1.0.0-py3-none-any.whl: PASSED
Checking dist/transformdash-1.0.0.tar.gz: PASSED
```

### Step 3: Upload to TestPyPI

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*
```

Or with token directly:
```bash
twine upload --repository testpypi \
  --username __token__ \
  --password pypi-YOUR_TESTPYPI_TOKEN \
  dist/*
```

### Step 4: Test Installation from TestPyPI

```bash
# Create a fresh virtual environment
python -m venv test_env
source test_env/bin/activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  transformdash[ml]

# Test it works
transformdash --help
python -c "from ml.registry.model_registry import model_registry; print('Success!')"

# Deactivate and remove test environment
deactivate
rm -rf test_env
```

**Note:** `--extra-index-url https://pypi.org/simple/` is needed because TestPyPI doesn't have all dependencies.

---

## Publishing to PyPI

### Step 1: Verify TestPyPI Success

Make sure everything works on TestPyPI before proceeding!

### Step 2: Clean and Rebuild

```bash
# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Rebuild with latest changes
python -m build

# Verify
twine check dist/*
```

### Step 3: Upload to PyPI

```bash
# Upload to production PyPI
twine upload dist/*
```

Or with token:
```bash
twine upload \
  --username __token__ \
  --password pypi-YOUR_PYPI_TOKEN \
  dist/*
```

### Step 4: Verify Publication

Visit your package page:
```
https://pypi.org/project/transformdash/
```

### Step 5: Test Installation

```bash
# Create fresh environment
python -m venv test_prod
source test_prod/bin/activate

# Install from PyPI
pip install transformdash[ml]

# Test
transformdash --help

# Cleanup
deactivate
rm -rf test_prod
```

---

## After Publishing

### 1. Update Documentation

Add installation instructions to README:
```markdown
## Installation

```bash
pip install transformdash

# With ML support
pip install transformdash[ml]

# With all extras
pip install transformdash[ml,scraping,orchestration]
```
```

### 2. Create GitHub Release

```bash
# Tag the version
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# Create release on GitHub
# Go to https://github.com/kraftaa/transformdash/releases/new
# - Select the tag v1.0.0
# - Add release notes
# - Attach dist files (optional)
```

### 3. Announce Release

- Update project documentation
- Notify users via email/Slack/etc.
- Post on social media
- Update project homepage

---

## Version Management

### Semantic Versioning

Use [semantic versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

- **MAJOR** (1.0.0 → 2.0.0): Breaking changes
- **MINOR** (1.0.0 → 1.1.0): New features, backward compatible
- **PATCH** (1.0.0 → 1.0.1): Bug fixes

### Publishing Updates

```bash
# 1. Update version in setup.py and pyproject.toml
# 2. Update CHANGELOG.md
# 3. Commit changes
git add setup.py pyproject.toml CHANGELOG.md
git commit -m "Bump version to 1.1.0"

# 4. Clean and rebuild
rm -rf build/ dist/ *.egg-info/
python -m build

# 5. Test on TestPyPI first
twine upload --repository testpypi dist/*

# 6. If all good, upload to PyPI
twine upload dist/*

# 7. Tag and push
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin main
git push origin v1.1.0
```

---

## Configuration with `.pypirc`

To avoid entering credentials each time, create `~/.pypirc`:

```ini
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
```

Then uploading is simpler:
```bash
# TestPyPI
twine upload --repository testpypi dist/*

# PyPI
twine upload dist/*
```

**Security:** Make sure `.pypirc` has restricted permissions:
```bash
chmod 600 ~/.pypirc
```

---

## Troubleshooting

### Error: "File already exists"

PyPI doesn't allow overwriting versions. You must:
1. Increment the version number
2. Rebuild and upload

```bash
# Update version in setup.py and pyproject.toml
# Then:
rm -rf dist/ build/ *.egg-info/
python -m build
twine upload dist/*
```

### Error: "Invalid distribution"

Check that required files exist:
```bash
# Verify these exist
ls README.md
ls LICENSE
ls requirements.txt

# Verify MANIFEST.in includes them
cat MANIFEST.in
```

### Error: "Invalid classifier"

Use only [valid classifiers](https://pypi.org/classifiers/):
```python
classifiers=[
    "Development Status :: 4 - Beta",  # Valid
    "Intended Audience :: Developers",  # Valid
    "Invalid :: Classifier",  # INVALID - will fail
]
```

### Missing Dependencies After Install

If users report missing dependencies:
1. Check `install_requires` in `setup.py`
2. Check `dependencies` in `pyproject.toml`
3. Ensure version is incremented
4. Republish

---

## Best Practices

1. **Always test on TestPyPI first**
2. **Use semantic versioning**
3. **Keep CHANGELOG.md updated**
4. **Tag releases in git**
5. **Test installation before announcing**
6. **Never delete published versions** (breaks users' installs)
7. **Use API tokens, not passwords**
8. **Keep tokens secure** (never commit them)

---

## Summary Commands

```bash
# Local development install
pip install -e ".[dev,ml]"

# Build package
python -m build

# Check distribution
twine check dist/*

# Test on TestPyPI
twine upload --repository testpypi dist/*

# Publish to PyPI
twine upload dist/*

# Users install with
pip install transformdash
pip install transformdash[ml]
pip install transformdash[ml,scraping,orchestration]
```

---

## Resources

- PyPI: https://pypi.org
- TestPyPI: https://test.pypi.org
- Packaging Guide: https://packaging.python.org/
- Twine Docs: https://twine.readthedocs.io/
- Semantic Versioning: https://semver.org/
