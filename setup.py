"""
TransformDash - Hybrid Data Transformation & Dashboard Platform
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="transformdash",
    version="1.0.0",
    author="Maria Kraft",
    author_email="your.email@example.com",  # Update with your email
    description="A modern, dbt-inspired data transformation platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kraftaa/transformdash",
    project_urls={
        "Bug Tracker": "https://github.com/kraftaa/transformdash/issues",
        "Documentation": "https://github.com/kraftaa/transformdash/wiki",
        "Source Code": "https://github.com/kraftaa/transformdash",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.11",
    install_requires=[
        "psycopg2-binary>=2.9.6",
        "pymongo>=4.4.0",
        "redis>=4.5.1",
        "sqlalchemy>=2.0.15",
        "python-dotenv>=1.0.0",
        "fastapi>=0.95.2",
        "uvicorn>=0.23.1",
        "jinja2>=3.1.0",
        "pyyaml>=6.0",
        "pandas>=2.0.2",
        "numpy>=1.20.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "orchestration": [
            "celery>=5.3.1",
            "prefect>=2.7.9",
        ],
        "bigdata": [
            "pyspark>=3.5.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "transformdash=ui.app:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.sql", "*.yml", "*.yaml"],
    },
)
