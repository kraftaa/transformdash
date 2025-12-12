"""
TransformDash - Hybrid Data Transformation & Dashboard Platform
with dbt-like SQL models, ML integration, and interactive dashboards
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="transformdash",
    version="1.0.0",
    author="Maria Dubyaga",
    author_email="kraftaa@gmail.com",
    description="A modern, dbt-inspired data transformation platform with ML integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kraftaa/transformdash",
    project_urls={
        "Bug Tracker": "https://github.com/kraftaa/transformdash/issues",
        "Documentation": "https://github.com/kraftaa/transformdash/wiki",
        "Source Code": "https://github.com/kraftaa/transformdash",
    },
    packages=find_packages(exclude=["tests", "tests.*", "examples"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Database",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "psycopg2-binary>=2.9.6",
        "pymongo>=4.4.0",
        "redis>=4.5.1",
        "sqlalchemy>=2.0.15",
        "python-dotenv>=1.0.0",
        "fastapi>=0.95.2",
        "uvicorn>=0.23.1",
        "python-multipart>=0.0.20",
        "python-jose[cryptography]>=3.3.0",
        "bcrypt>=4.0.1",
        "jinja2>=3.1.0",
        "pyyaml>=6.0",
        "pandas>=2.0.2",
        "numpy>=1.20.0",
        "faker>=18.10.1",
        "apscheduler>=3.10.4",
        "scikit-learn>=1.3.0",
        "joblib>=1.3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "isort>=5.12.0",
        ],
        "scraping": [
            "selenium>=4.15.0",
            "webdriver-manager>=4.0.1",
            "beautifulsoup4>=4.12.0",
            "openpyxl>=3.1.2",
        ],
        "orchestration": [
            "celery>=5.3.1",
            "prefect>=2.7.9",
        ],
        "bigdata": [
            "pyspark>=3.5.1",
        ],
        "ml": [
            "scikit-learn>=1.3.0",
            "joblib>=1.3.0",
            "xgboost>=1.7.0",
            "lightgbm>=4.0.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
            "mkdocstrings[python]>=0.22.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "transformdash=ui.app_refactored:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.sql", "*.yml", "*.yaml"],
        "ui": ["templates/*.html", "static/css/*.css", "static/js/*.js", "static/assets/*"],
        "models": ["bronze/*.sql", "silver/*.sql", "gold/*.sql", "schema.yml"],
    },
    keywords=[
        "data",
        "transformation",
        "etl",
        "dbt",
        "sql",
        "analytics",
        "dashboard",
        "visualization",
        "machine-learning",
        "ml",
        "postgres",
        "fastapi",
    ],
    zip_safe=False,
)
