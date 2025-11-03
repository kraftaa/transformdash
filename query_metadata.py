#!/usr/bin/env python3
"""
Query metadata from TransformDash YAML files
"""
import yaml
from pathlib import Path

def load_yaml(file_path):
    """Load YAML file"""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    models_dir = Path(__file__).parent / 'models'

    # Load dashboards
    dashboards_file = models_dir / 'dashboards.yml'
    if dashboards_file.exists():
        dashboards_data = load_yaml(dashboards_file)
        print("=" * 80)
        print("DASHBOARDS")
        print("=" * 80)
        for dashboard in dashboards_data.get('dashboards', []):
            print(f"\nDashboard: {dashboard['name']} (ID: {dashboard['id']})")
            print(f"  Description: {dashboard.get('description', 'N/A')}")
            print(f"  Charts: {len(dashboard.get('charts', []))}")

            for chart in dashboard.get('charts', []):
                print(f"\n  Chart: {chart['title']} (ID: {chart['id']})")
                print(f"    Type: {chart['type']}")
                print(f"    Model: {chart['model']}")
                if chart['type'] == 'table':
                    print(f"    Columns: {', '.join(chart.get('columns', []))}")
                else:
                    print(f"    X-Axis: {chart.get('x_axis', 'N/A')}")
                    print(f"    Y-Axis: {chart.get('y_axis', 'N/A')}")
                    print(f"    Aggregation: {chart.get('aggregation', 'N/A')}")

    # Load datasets (models)
    print("\n" + "=" * 80)
    print("DATASETS (DBT MODELS)")
    print("=" * 80)

    for yml_file in models_dir.glob('*.yml'):
        if yml_file.name == 'dashboards.yml':
            continue

        data = load_yaml(yml_file)

        # Check if it's a dbt models file
        if 'models' in data:
            print(f"\nFile: {yml_file.name}")
            for model in data.get('models', []):
                print(f"\n  Model: {model['name']}")
                print(f"    Description: {model.get('description', 'N/A')}")
                print(f"    Columns: {len(model.get('columns', []))}")

                for col in model.get('columns', []):
                    print(f"      - {col['name']}: {col.get('description', 'No description')}")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
