# Quick Guide: Publishing TransformDash to PyPI

This is a condensed guide for publishing TransformDash as a pip package. For complete details, see [PUBLISHING.md](PUBLISHING.md).

---

## Prerequisites

1. **Create PyPI Accounts:**
   - TestPyPI: https://test.pypi.org/account/register/
   - PyPI: https://pypi.org/account/register/

2. **Install Build Tools:**
   ```bash
   pip install build twine
   ```

---

## Publishing Steps

### Step 1: Clean and Build

```bash
# Clean old builds
rm -rf build/ dist/ *.egg-info/

# Build the package
python -m build
```

This creates:
- `dist/transformdash-1.0.0-py3-none-any.whl` (wheel)
- `dist/transformdash-1.0.0.tar.gz` (source)

### Step 2: Check Quality

```bash
twine check dist/*
```

Should show:
```
Checking dist/transformdash-1.0.0-py3-none-any.whl: PASSED
Checking dist/transformdash-1.0.0.tar.gz: PASSED
```

### Step 3: Test on TestPyPI (Recommended)

```bash
# Upload to test.pypi.org
twine upload --repository testpypi dist/*
```

You'll be prompted for:
- Username: `__token__`
- Password: Your TestPyPI API token

**Test the installation:**
```bash
# Create test environment
python -m venv test_env
source test_env/bin/activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  transformdash

# Test it works
python -c "import ui.app; print('Success!')"

# Cleanup
deactivate
rm -rf test_env
```

### Step 4: Publish to PyPI

```bash
# Upload to production PyPI
twine upload dist/*
```

You'll be prompted for:
- Username: `__token__`
- Password: Your PyPI API token

### Step 5: Verify

Visit your package page:
```
https://pypi.org/project/transformdash/
```

Users can now install with:
```bash
pip install transformdash
```

---

## Using API Tokens

### Get API Tokens

1. **TestPyPI**: https://test.pypi.org/manage/account/token/
2. **PyPI**: https://pypi.org/manage/account/token/

### Save Tokens (Optional)

Create `~/.pypirc`:
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

**Secure it:**
```bash
chmod 600 ~/.pypirc
```

Then uploading is simpler:
```bash
twine upload --repository testpypi dist/*  # TestPyPI
twine upload dist/*                         # PyPI
```

---

## Updating the Package

When releasing a new version:

### 1. Update Version

Edit both files:
- `setup.py`: Change `version="1.0.0"` to `version="1.0.1"`
- `pyproject.toml`: Change `version = "1.0.0"` to `version = "1.0.1"`

### 2. Rebuild and Publish

```bash
# Clean and rebuild
rm -rf build/ dist/ *.egg-info/
python -m build

# Check
twine check dist/*

# Test on TestPyPI first
twine upload --repository testpypi dist/*

# Then publish to PyPI
twine upload dist/*
```

### 3. Tag Release

```bash
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1
```

---

## Troubleshooting

### Error: "File already exists"

PyPI doesn't allow overwriting. You must increment the version number.

### Error: "Invalid distribution"

Check that required files exist:
```bash
ls README.md LICENSE requirements.txt
```

### Missing Dependencies

Ensure all dependencies are in:
- `setup.py` → `install_requires`
- `pyproject.toml` → `dependencies`

---

## Version Numbering

Use [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

- **MAJOR** (1.0.0 → 2.0.0): Breaking changes
- **MINOR** (1.0.0 → 1.1.0): New features, backward compatible
- **PATCH** (1.0.0 → 1.0.1): Bug fixes

---

## Quick Reference

```bash
# Full publishing workflow
rm -rf build/ dist/ *.egg-info/
python -m build
twine check dist/*
twine upload --repository testpypi dist/*  # Test first
twine upload dist/*                         # Then production

# Users install with
pip install transformdash
```

---

## Resources

- **Complete Guide**: [PUBLISHING.md](PUBLISHING.md)
- **PyPI**: https://pypi.org
- **TestPyPI**: https://test.pypi.org
- **Twine Docs**: https://twine.readthedocs.io/
