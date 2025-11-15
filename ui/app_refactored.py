"""
TransformDash Web UI - FastAPI Application (Refactored)
Interactive lineage graphs and dashboard with separated concerns
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pathlib import Path
import sys
import pandas as pd
import logging
import uuid
import os
import json
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from transformations.dbt_loader import DBTModelLoader
from transformations import DAG
from orchestration.history import RunHistory
import datasets_api

app = FastAPI(title="TransformDash", description="Hybrid Data Transformation Platform")

# Mount static files
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Global state
models_dir = Path(__file__).parent.parent / "models"
loader = DBTModelLoader(models_dir=str(models_dir))
run_history = RunHistory()


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main dashboard HTML"""
    import yaml
    import time
    from fastapi.responses import Response

    # Load dashboards for the dropdown
    dashboards = []
    dashboards_file = models_dir / "dashboards.yml"
    if dashboards_file.exists():
        try:
            with open(dashboards_file, 'r') as f:
                data = yaml.safe_load(f)
                dashboards = data.get('dashboards', [])
        except Exception:
            pass

    response = templates.TemplateResponse("index.html", {
        "request": request,
        "dashboards": dashboards,
        "cache_bust": int(time.time() * 1000)
    })

    # Add cache control headers to prevent caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@app.get("/dashboard/{dashboard_id}", response_class=HTMLResponse)
async def dashboard_view(request: Request, dashboard_id: str):
    """Serve an individual dashboard in full-page view"""
    return templates.TemplateResponse("dashboard_view.html", {
        "request": request,
        "dashboard_id": dashboard_id
    })


@app.get("/api/models")
async def get_models():
    """Get all models with their dependencies"""
    try:
        models = loader.load_all_models()

        return [{
            "name": model.name,
            "type": model.model_type.value,
            "depends_on": model.depends_on,
            "config": getattr(model, 'config', {}),
            "file_path": getattr(model, 'file_path', '')
        } for model in models]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lineage")
async def get_lineage():
    """Get DAG lineage information"""
    try:
        models = loader.load_all_models()
        dag = DAG(models)

        return {
            "execution_order": dag.get_execution_order(),
            "graph": dag.graph,
            "visualization": dag.visualize()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/{model_name}/code")
async def get_model_code(model_name: str):
    """Get the code for a specific model (SQL or Python)"""
    try:
        models = loader.load_all_models()
        model = next((m for m in models if m.name == model_name), None)

        if not model:
            raise HTTPException(status_code=404, detail=f"Model {model_name} not found")

        # Get code - for SQL models use sql_query, for Python models read file
        code = model.sql_query
        if code is None and hasattr(model, 'file_path') and model.file_path:
            # Python model - read the file
            try:
                with open(model.file_path, 'r') as f:
                    code = f.read()
            except Exception as e:
                code = f"# Error reading file: {e}"

        return {
            "name": model.name,
            "code": code,
            "type": model.model_type.value,
            "config": getattr(model, 'config', {}),
            "depends_on": model.depends_on,
            "file_path": getattr(model, 'file_path', '')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/execute")
async def execute_transformations():
    """Execute all transformations in DAG order"""
    try:
        from orchestration import TransformationEngine
        from datetime import datetime

        # Generate run ID
        run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")

        models = loader.load_all_models()
        engine = TransformationEngine(models)
        context = engine.run(verbose=False)

        summary = context.get_summary()

        # Save run history
        run_history.save_run(run_id, summary, context.logs)

        # Build model results array with error messages
        model_results = []
        for name, meta in summary["models"].items():
            model_results.append({
                "name": name,
                "status": meta["status"],
                "execution_time": meta["execution_time"],
                "error": meta.get("error", None)
            })

        # Add model_results to summary for frontend
        summary["model_results"] = model_results

        return {
            "status": "completed",
            "run_id": run_id,
            "summary": summary,
            "results": {
                name: {
                    "status": meta["status"],
                    "execution_time": meta["execution_time"]
                }
                for name, meta in summary["models"].items()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/execute/{model_name}")
async def execute_single_model(model_name: str):
    """Execute a single transformation model (and its dependencies)"""
    try:
        from orchestration import TransformationEngine

        # Load all models (need dependencies)
        all_models = loader.load_all_models()

        # Find the target model
        target_model = next((m for m in all_models if m.name == model_name), None)
        if not target_model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # Get all dependencies (recursively)
        def get_dependencies(model_name, all_models):
            model = next((m for m in all_models if m.name == model_name), None)
            if not model:
                return []

            deps = []
            for dep_name in model.depends_on:
                deps.extend(get_dependencies(dep_name, all_models))
                dep_model = next((m for m in all_models if m.name == dep_name), None)
                if dep_model and dep_model not in deps:
                    deps.append(dep_model)

            return deps

        # Get all models needed (dependencies + target)
        dependency_models = get_dependencies(model_name, all_models)
        models_to_run = dependency_models + [target_model]

        # Run models
        engine = TransformationEngine(models_to_run)
        context = engine.run(verbose=False)

        # Get summary
        summary = context.get_summary()

        # Save to run history
        import uuid
        from datetime import datetime
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Add run metadata to summary
        summary['run_type'] = 'single_model'
        summary['target_model'] = model_name
        summary['timestamp'] = datetime.now().isoformat()

        run_history.save_run(run_id, summary, context.logs)

        # Check if target model succeeded
        if target_model.status != "completed":
            return {
                "status": "failed",
                "model": {
                    'name': target_model.name,
                    'type': target_model.model_type.value,
                    'status': target_model.status,
                    'error': target_model.error
                },
                "message": f"Model '{model_name}' failed to execute",
                "dependencies_run": len(dependency_models),
                "summary": summary,
                "run_id": run_id
            }

        return {
            "status": "completed",
            "model": {
                'name': target_model.name,
                'type': target_model.model_type.value,
                'status': target_model.status
            },
            "message": f"Model '{model_name}' executed successfully",
            "dependencies_run": len(dependency_models),
            "summary": summary,
            "run_id": run_id
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error running model {model_name}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/runs")
async def get_runs(limit: int = 50):
    """Get execution history"""
    try:
        runs = run_history.get_all_runs(limit=limit)
        return {"runs": runs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/runs/{run_id}")
async def get_run_details(run_id: str):
    """Get detailed information about a specific run"""
    try:
        run_data = run_history.get_run(run_id)
        return run_data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/{model_name}/runs")
async def get_model_runs(model_name: str, limit: int = 10):
    """Get execution history for a specific model"""
    try:
        all_runs = run_history.get_all_runs(limit=100)  # Get more runs to filter from
        model_runs = []

        for run in all_runs:
            # Check if this model was in this run
            if 'summary' in run and 'models' in run['summary']:
                if model_name in run['summary']['models']:
                    model_info = run['summary']['models'][model_name]
                    model_runs.append({
                        'run_id': run['run_id'],
                        'timestamp': run['timestamp'],
                        'status': model_info['status'],
                        'execution_time': model_info['execution_time'],
                        'error': model_info.get('error', None)
                    })

                    if len(model_runs) >= limit:
                        break

        return {"runs": model_runs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ML MODEL ENDPOINTS
# =============================================================================

@app.get("/api/ml/models")
async def get_ml_models():
    """Get all registered ML models"""
    try:
        from ml.registry.model_registry import model_registry
        models = model_registry.list_models()
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ml/models/{model_name}")
async def get_ml_model_info(model_name: str, version: str = None):
    """Get detailed information about a specific ML model"""
    try:
        from ml.registry.model_registry import model_registry
        info = model_registry.get_model_info(model_name, version)
        return info
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ml/models/{model_name}/versions")
async def get_ml_model_versions(model_name: str):
    """Get all versions of a specific ML model"""
    try:
        from ml.registry.model_registry import model_registry
        versions = model_registry.list_model_versions(model_name)
        return {"model_name": model_name, "versions": versions}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ml/predict")
async def ml_predict(request: Request):
    """Make predictions using a registered ML model"""
    try:
        from ml.inference.predictor import ml_predictor
        body = await request.json()

        model_name = body.get('model_name')
        features = body.get('features')
        version = body.get('version')
        return_proba = body.get('return_proba', False)

        if not model_name or not features:
            raise HTTPException(status_code=400, detail="model_name and features are required")

        prediction = ml_predictor.predict(
            model_name=model_name,
            features=features,
            version=version,
            return_proba=return_proba
        )

        return {
            "model_name": model_name,
            "prediction": prediction
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/exposures")
async def get_exposures():
    """Get dashboards/exposures that depend on models"""
    try:
        import yaml
        exposures_file = models_dir / "exposures.yml"

        if not exposures_file.exists():
            return {"exposures": []}

        with open(exposures_file, 'r') as f:
            data = yaml.safe_load(f)

        return {"exposures": data.get('exposures', [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboards")
async def get_dashboards():
    """Get dashboard configurations from database"""
    try:
        from connection_manager import connection_manager

        with connection_manager.get_connection() as pg:
            # Get all dashboards
            dashboards_query = """
                SELECT id, name, description, created_at, updated_at
                FROM dashboards
                ORDER BY name
            """
            dashboards = pg.execute(dashboards_query, fetch=True)

            result = []
            for dashboard in dashboards:
                dashboard_id = dashboard['id']

                # Get tabs for this dashboard
                tabs_query = """
                    SELECT id, name, position
                    FROM dashboard_tabs
                    WHERE dashboard_id = %s
                    ORDER BY position
                """
                tabs = pg.execute(tabs_query, (dashboard_id,), fetch=True)

                # Get filters for this dashboard
                filters_query = """
                    SELECT field, label, model, expression, apply_to_tabs
                    FROM dashboard_filters
                    WHERE dashboard_id = %s
                    ORDER BY position
                """
                filters = pg.execute(filters_query, (dashboard_id,), fetch=True)

                # Get charts for this dashboard
                charts_query = """
                    SELECT
                        c.id,
                        c.chart_number,
                        c.title,
                        c.type,
                        c.model,
                        c.connection_id,
                        c.x_axis,
                        c.y_axis,
                        c.aggregation,
                        c.columns,
                        c.category,
                        c.config,
                        dc.tab_id,
                        dc.position
                    FROM charts c
                    INNER JOIN dashboard_charts dc ON c.id = dc.chart_id
                    WHERE dc.dashboard_id = %s
                    ORDER BY dc.position
                """
                charts = pg.execute(charts_query, (dashboard_id,), fetch=True)

                result.append({
                    'id': dashboard['id'],
                    'name': dashboard['name'],
                    'description': dashboard['description'],
                    'tabs': [{'id': t['id'], 'name': t['name']} for t in tabs],
                    'filters': [dict(f) for f in filters],
                    'charts': [dict(chart) for chart in charts]
                })

            return {"dashboards": result}
    except Exception as e:
        import traceback
        import logging
        logging.error(f"Error getting dashboards: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dashboards")
async def create_dashboard(request: Request):
    """Create a new dashboard"""
    try:
        import yaml
        import logging
        import re

        body = await request.json()
        dashboard_name = body.get("name", "").strip()
        dashboard_description = body.get("description", "").strip()

        if not dashboard_name:
            raise HTTPException(status_code=400, detail="Dashboard name is required")

        # Generate dashboard ID from name (lowercase, replace spaces with hyphens)
        dashboard_id = re.sub(r'[^a-z0-9]+', '-', dashboard_name.lower()).strip('-')

        dashboards_file = models_dir / "dashboards.yml"

        # Load existing dashboards or create new structure
        if dashboards_file.exists():
            with open(dashboards_file, 'r') as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}

        if 'dashboards' not in data:
            data['dashboards'] = []

        # Check if dashboard with this name or ID already exists
        existing_names = [d.get('name', '').lower() for d in data['dashboards']]
        existing_ids = [d.get('id') for d in data['dashboards']]

        if dashboard_name.lower() in existing_names:
            raise HTTPException(
                status_code=400,
                detail=f"Dashboard with name '{dashboard_name}' already exists. Please choose a different name."
            )

        if dashboard_id in existing_ids:
            # This shouldn't happen if name is unique, but just in case
            raise HTTPException(
                status_code=400,
                detail=f"Dashboard ID conflict. Please choose a different name."
            )

        # Create new dashboard
        new_dashboard = {
            "id": dashboard_id,
            "name": dashboard_name,
            "description": dashboard_description or f"Custom dashboard: {dashboard_name}",
            "charts": []
        }

        data['dashboards'].append(new_dashboard)

        # Save to file
        with open(dashboards_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        logging.info(f"Created new dashboard: {dashboard_id}")

        return {
            "success": True,
            "message": f"Dashboard '{dashboard_name}' created successfully!",
            "dashboard": new_dashboard
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error creating dashboard: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/charts")
async def get_all_charts():
    """Get all charts from the database"""
    try:
        import logging
        import json
        from connection_manager import connection_manager

        logging.info("Fetching all charts from database")

        with connection_manager.get_connection() as pg:
            # Query all charts from the charts table, including their dashboard assignments
            charts_data = pg.execute("""
                SELECT
                    c.id,
                    c.chart_number,
                    c.title,
                    c.description,
                    c.type,
                    c.model,
                    c.connection_id,
                    c.x_axis,
                    c.y_axis,
                    c.aggregation,
                    c.columns,
                    c.category,
                    c.config,
                    c.created_at,
                    c.updated_at,
                    dc.dashboard_id,
                    dc.tab_id
                FROM charts c
                LEFT JOIN dashboard_charts dc ON c.id = dc.chart_id
                ORDER BY c.chart_number ASC
            """, fetch=True)

            all_charts = []
            # Handle case where charts_data might be None or empty list
            if charts_data:
                for chart in charts_data:
                    chart_dict = {
                        'id': chart['id'],
                        'chart_number': chart['chart_number'],
                        'title': chart['title'],
                        'description': chart.get('description', ''),
                        'type': chart['type'],
                        'model': chart['model'],
                        'connection_id': chart['connection_id'],
                        'x_axis': chart['x_axis'],
                        'y_axis': chart['y_axis'],
                        'aggregation': chart['aggregation'],
                        'columns': chart['columns'] if chart['columns'] else [],
                        'category': chart['category'],
                        'config': chart['config'] if chart['config'] else {},
                        'created_at': str(chart['created_at']) if chart['created_at'] else None,
                        'updated_at': str(chart['updated_at']) if chart['updated_at'] else None,
                        'dashboard_id': chart['dashboard_id'],  # Include current dashboard assignment
                        'tab_id': chart['tab_id']  # Include current tab assignment
                    }
                    all_charts.append(chart_dict)

            logging.info(f"Fetched {len(all_charts)} charts from database")
            return {"charts": all_charts}

    except Exception as e:
        import logging
        import traceback
        logging.error(f"Error fetching charts: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/charts/save")
async def save_chart(request: Request):
    """Save a chart configuration to database"""
    try:
        import logging
        import json
        from connection_manager import connection_manager

        # Parse request body
        body = await request.json()
        logging.info(f"Received chart save request: {body}")

        # Get chart config from request
        chart_id = body.get("id")
        chart_title = body.get("title")
        chart_description = body.get("description", "")
        chart_type = body.get("type")
        chart_model = body.get("model")
        x_axis = body.get("x_axis", "")
        y_axis = body.get("y_axis", "")
        aggregation = body.get("aggregation", "sum")
        columns = body.get("columns", None)  # For table charts
        category = body.get("category", None)  # For stacked charts
        config = body.get("config", None)  # Additional config

        # Get the target dashboard ID from the request (None means standalone chart)
        target_dashboard_id = body.get('dashboard_id', None)
        tab_id = body.get('tab_id', None)  # NULL means unassigned
        logging.info(f"Target dashboard ID: {target_dashboard_id}, tab: {tab_id}")

        with connection_manager.get_connection() as pg:
            # Handle creating a new dashboard if requested
            if target_dashboard_id == '__new__':
                new_dashboard_name = body.get('dashboard_name', 'New Dashboard')
                new_dashboard_description = body.get('dashboard_description', '')
                target_dashboard_id = new_dashboard_name.lower().replace(' ', '_').replace('-', '_')

                # Check if dashboard exists
                existing_dashboard = pg.execute(
                    "SELECT id FROM dashboards WHERE id = %s",
                    (target_dashboard_id,),
                    fetch=True
                )

                if not existing_dashboard:
                    # Create new dashboard
                    pg.execute("""
                        INSERT INTO dashboards (id, name, description)
                        VALUES (%s, %s, %s)
                    """, (target_dashboard_id, new_dashboard_name, new_dashboard_description))

                    # Create default tab
                    pg.execute("""
                        INSERT INTO dashboard_tabs (id, dashboard_id, name, position)
                        VALUES (%s, %s, %s, %s)
                    """, (f"{target_dashboard_id}_tab_default", target_dashboard_id, 'All Charts', 0))

                    tab_id = f"{target_dashboard_id}_tab_default"
                    logging.info(f"Created new dashboard: {target_dashboard_id}")

            # Check if dashboard exists (only if dashboard_id provided)
            if target_dashboard_id:
                dashboard_check = pg.execute(
                    "SELECT id FROM dashboards WHERE id = %s",
                    (target_dashboard_id,),
                    fetch=True
                )

                if not dashboard_check:
                    raise HTTPException(status_code=404, detail=f"Dashboard {target_dashboard_id} not found")

            # Insert or update chart in charts table
            pg.execute("""
                INSERT INTO charts (id, title, description, type, model, x_axis, y_axis, aggregation, columns, category, config)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    type = EXCLUDED.type,
                    model = EXCLUDED.model,
                    x_axis = EXCLUDED.x_axis,
                    y_axis = EXCLUDED.y_axis,
                    aggregation = EXCLUDED.aggregation,
                    columns = EXCLUDED.columns,
                    category = EXCLUDED.category,
                    config = EXCLUDED.config,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                chart_id, chart_title, chart_description, chart_type, chart_model,
                x_axis, y_axis, aggregation,
                json.dumps(columns) if columns else None,
                category,
                json.dumps(config) if config else None
            ))

            # Insert or update dashboard_charts junction (only if dashboard_id provided)
            if target_dashboard_id:
                # If tab_id is not set, use the default tab for this dashboard
                if not tab_id:
                    tab_id = f"{target_dashboard_id}_tab_default"

                pg.execute("""
                    INSERT INTO dashboard_charts (dashboard_id, chart_id, tab_id, position)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (dashboard_id, chart_id, tab_id) DO UPDATE SET
                        position = EXCLUDED.position
                """, (target_dashboard_id, chart_id, tab_id, 0))
                logging.info(f"Successfully saved chart {chart_id} to dashboard {target_dashboard_id}")
            else:
                # Remove chart from all dashboards when saving as standalone
                pg.execute("DELETE FROM dashboard_charts WHERE chart_id = %s", (chart_id,))
                logging.info(f"Successfully saved standalone chart {chart_id} (removed from all dashboards)")

        return {
            "success": True,
            "message": "Chart saved successfully!",
            "dashboard_id": target_dashboard_id,
            "chart_id": chart_id
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        logging.error(f"Error saving chart: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/charts/{chart_id}")
async def delete_chart(chart_id: str):
    """Delete a chart from the database"""
    try:
        import logging
        from connection_manager import connection_manager

        logging.info(f"Deleting chart: {chart_id}")

        with connection_manager.get_connection() as pg:
            # Check if chart exists
            chart_check = pg.execute(
                "SELECT id FROM charts WHERE id = %s",
                (chart_id,),
                fetch=True
            )

            if not chart_check:
                raise HTTPException(status_code=404, detail=f"Chart {chart_id} not found")

            # Delete from dashboard_charts junction table first (foreign key constraint)
            pg.execute("DELETE FROM dashboard_charts WHERE chart_id = %s", (chart_id,))
            logging.info(f"Removed chart {chart_id} from all dashboards")

            # Delete the chart itself
            pg.execute("DELETE FROM charts WHERE id = %s", (chart_id,))
            logging.info(f"Successfully deleted chart {chart_id}")

            return {
                "success": True,
                "message": f"Chart deleted successfully",
                "chart_id": chart_id
            }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        logging.error(f"Error deleting chart: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dashboards/{dashboard_id}/charts/add")
async def add_chart_to_dashboard(dashboard_id: str, request: Request):
    """Add an existing chart to a specific dashboard"""
    try:
        import yaml
        import logging

        body = await request.json()
        chart_id = body.get("chart_id")

        if not chart_id:
            raise HTTPException(status_code=400, detail="chart_id is required")

        dashboards_file = models_dir / "dashboards.yml"

        if not dashboards_file.exists():
            raise HTTPException(status_code=404, detail="Dashboards file not found")

        # Load dashboards
        with open(dashboards_file, 'r') as f:
            data = yaml.safe_load(f) or {}

        # Find the chart from all dashboards
        chart_to_add = None
        for dashboard in data.get('dashboards', []):
            for chart in dashboard.get('charts', []):
                if chart.get('id') == chart_id:
                    chart_to_add = chart.copy()
                    break
            if chart_to_add:
                break

        if not chart_to_add:
            raise HTTPException(status_code=404, detail=f"Chart {chart_id} not found")

        # Find target dashboard
        target_dashboard = None
        for dashboard in data.get('dashboards', []):
            if dashboard.get('id') == dashboard_id:
                target_dashboard = dashboard
                break

        if not target_dashboard:
            raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")

        # Add chart to target dashboard if it doesn't already exist
        if 'charts' not in target_dashboard:
            target_dashboard['charts'] = []

        # Check if chart already exists in this dashboard
        chart_exists = any(c.get('id') == chart_id for c in target_dashboard['charts'])

        if chart_exists:
            return {
                "success": False,
                "message": "Chart already exists in this dashboard"
            }

        target_dashboard['charts'].append(chart_to_add)

        # Save back to file
        with open(dashboards_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        return {
            "success": True,
            "message": f"Chart added to dashboard '{target_dashboard.get('name', dashboard_id)}' successfully!"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error adding chart to dashboard: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboards/{dashboard_id}")
async def get_dashboard(dashboard_id: str):
    """Get a specific dashboard by ID from database"""
    try:
        from connection_manager import connection_manager

        with connection_manager.get_connection() as pg:
            # Get dashboard details
            dashboard_query = """
                SELECT id, name, description, created_at, updated_at
                FROM dashboards
                WHERE id = %s
            """
            dashboard_result = pg.execute(dashboard_query, (dashboard_id,), fetch=True)

            if not dashboard_result:
                raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")

            dashboard = dashboard_result[0]

            # Get tabs for this dashboard
            tabs_query = """
                SELECT id, name, position
                FROM dashboard_tabs
                WHERE dashboard_id = %s
                ORDER BY position
            """
            tabs = pg.execute(tabs_query, (dashboard_id,), fetch=True)

            # Get all charts assigned to this dashboard with their tab assignments
            assigned_charts_query = """
                SELECT
                    c.id, c.title, c.type, c.model, c.x_axis, c.y_axis,
                    c.aggregation, c.columns, c.category, c.config,
                    dc.tab_id, dc.position, dc.size
                FROM charts c
                JOIN dashboard_charts dc ON c.id = dc.chart_id
                WHERE dc.dashboard_id = %s
                ORDER BY dc.position
            """
            assigned_charts = pg.execute(assigned_charts_query, (dashboard_id,), fetch=True)

            # Organize charts by tab
            tabs_with_charts = []
            unassigned_charts = []

            for tab in tabs:
                tab_charts = [
                    {
                        'id': chart['id'],
                        'title': chart['title'],
                        'type': chart['type'],
                        'model': chart['model'],
                        'x_axis': chart['x_axis'],
                        'y_axis': chart['y_axis'],
                        'aggregation': chart['aggregation'],
                        'columns': chart['columns'],
                        'category': chart['category'],
                        'config': chart['config'],
                        'size': chart.get('size', 'medium')
                    }
                    for chart in assigned_charts
                    if chart['tab_id'] == tab['id']
                ]

                tabs_with_charts.append({
                    'id': tab['id'],
                    'name': tab['name'],
                    'position': tab['position'],
                    'charts': tab_charts
                })

            # Get unassigned charts (tab_id is NULL)
            unassigned_charts = [
                {
                    'id': chart['id'],
                    'title': chart['title'],
                    'type': chart['type'],
                    'model': chart['model'],
                    'x_axis': chart['x_axis'],
                    'y_axis': chart['y_axis'],
                    'aggregation': chart['aggregation'],
                    'columns': chart['columns'],
                    'category': chart['category'],
                    'config': chart['config'],
                    'size': chart.get('size', 'medium')
                }
                for chart in assigned_charts
                if chart['tab_id'] is None
            ]

            # Get filters for this dashboard
            filters_query = """
                SELECT field, label, model, expression, apply_to_tabs
                FROM dashboard_filters
                WHERE dashboard_id = %s
                ORDER BY position
            """
            filters = pg.execute(filters_query, (dashboard_id,), fetch=True)

            return {
                'id': dashboard['id'],
                'name': dashboard['name'],
                'description': dashboard['description'],
                'tabs': tabs_with_charts,
                'charts': unassigned_charts,  # Unassigned charts
                'filters': [dict(f) for f in filters]
            }

    except HTTPException:
        raise
    except Exception as e:
        import logging
        import traceback
        logging.error(f"Error getting dashboard: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/dashboards/{dashboard_id}")
async def update_dashboard(dashboard_id: str, request: Request):
    """Update a dashboard with new chart configuration and filters in database"""
    try:
        import logging
        from connection_manager import connection_manager

        body = await request.json()
        new_tabs = body.get("tabs", None)
        new_charts = body.get("charts", None)  # Unassigned charts
        new_filters = body.get("filters", [])

        with connection_manager.get_connection() as pg:
            # Check if dashboard exists
            dashboard_result = pg.execute(
                "SELECT id, name FROM dashboards WHERE id = %s",
                (dashboard_id,),
                fetch=True
            )

            if not dashboard_result:
                raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")

            dashboard_name = dashboard_result[0]['name']

            # Update tabs if provided
            if new_tabs is not None:
                # Delete existing tabs and their chart assignments
                pg.execute("DELETE FROM dashboard_tabs WHERE dashboard_id = %s", (dashboard_id,))

                # Insert new tabs
                for idx, tab in enumerate(new_tabs):
                    tab_id = tab.get('id')
                    tab_name = tab.get('name')

                    # Create tab
                    pg.execute("""
                        INSERT INTO dashboard_tabs (id, dashboard_id, name, position)
                        VALUES (%s, %s, %s, %s)
                    """, (tab_id, dashboard_id, tab_name, idx))

                    # Insert charts into this tab
                    tab_charts = tab.get('charts', [])
                    for chart_idx, chart in enumerate(tab_charts):
                        chart_id = chart.get('id')

                        # Check if chart exists in charts table; if not, create it
                        chart_exists = pg.execute(
                            "SELECT id FROM charts WHERE id = %s",
                            (chart_id,),
                            fetch=True
                        )

                        if not chart_exists:
                            # Create chart in global charts table
                            pg.execute("""
                                INSERT INTO charts (id, title, type, model, x_axis, y_axis, aggregation, columns, category, config)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                chart_id,
                                chart.get('title'),
                                chart.get('type'),
                                chart.get('model'),
                                chart.get('x_axis', ''),
                                chart.get('y_axis', ''),
                                chart.get('aggregation', 'sum'),
                                chart.get('columns'),
                                chart.get('category'),
                                chart.get('config')
                            ))

                        # Assign chart to tab via junction table
                        chart_size = chart.get('size', 'medium')
                        pg.execute("""
                            INSERT INTO dashboard_charts (dashboard_id, chart_id, tab_id, position, size)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (dashboard_id, chart_id, tab_id) DO UPDATE SET
                                position = EXCLUDED.position,
                                size = EXCLUDED.size
                        """, (dashboard_id, chart_id, tab_id, chart_idx, chart_size))

            # Update unassigned charts (charts with tab_id = NULL)
            if new_charts is not None:
                # Delete existing unassigned charts for this dashboard
                pg.execute(
                    "DELETE FROM dashboard_charts WHERE dashboard_id = %s AND tab_id IS NULL",
                    (dashboard_id,)
                )

                # Insert unassigned charts
                for chart_idx, chart in enumerate(new_charts):
                    chart_id = chart.get('id')

                    # Check if chart exists; if not, create it
                    chart_exists = pg.execute(
                        "SELECT id FROM charts WHERE id = %s",
                        (chart_id,),
                        fetch=True
                    )

                    if not chart_exists:
                        pg.execute("""
                            INSERT INTO charts (id, title, type, model, x_axis, y_axis, aggregation, columns, category, config)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            chart_id,
                            chart.get('title'),
                            chart.get('type'),
                            chart.get('model'),
                            chart.get('x_axis', ''),
                            chart.get('y_axis', ''),
                            chart.get('aggregation', 'sum'),
                            chart.get('columns'),
                            chart.get('category'),
                            chart.get('config')
                        ))

                    # Assign chart as unassigned (tab_id = NULL)
                    chart_size = chart.get('size', 'medium')
                    pg.execute("""
                        INSERT INTO dashboard_charts (dashboard_id, chart_id, tab_id, position, size)
                        VALUES (%s, %s, NULL, %s, %s)
                        ON CONFLICT (dashboard_id, chart_id, tab_id) DO UPDATE SET
                            position = EXCLUDED.position,
                            size = EXCLUDED.size
                    """, (dashboard_id, chart_id, chart_idx, chart_size))

            # Update filters if provided
            if new_filters is not None:
                # Delete existing filters
                pg.execute("DELETE FROM dashboard_filters WHERE dashboard_id = %s", (dashboard_id,))

                # Insert new filters
                for filter_idx, filter_def in enumerate(new_filters):
                    pg.execute("""
                        INSERT INTO dashboard_filters (dashboard_id, field, label, model, expression, apply_to_tabs, position)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        dashboard_id,
                        filter_def.get('field'),
                        filter_def.get('label'),
                        filter_def.get('model'),
                        filter_def.get('expression'),
                        filter_def.get('apply_to_tabs', []),
                        filter_idx
                    ))

            logging.info(f"Successfully updated dashboard {dashboard_id}")

        return {
            "success": True,
            "message": f"Dashboard '{dashboard_name}' updated successfully!"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error updating dashboard: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/dashboards/{dashboard_id}/metadata")
async def update_dashboard_metadata(dashboard_id: str, request: Request):
    """Update dashboard name and/or description"""
    try:
        body = await request.json()
        name = body.get('name')
        description = body.get('description')

        logging.info(f"Updating dashboard {dashboard_id} metadata: name={name}, description={description}")

        # Validate at least one field is provided
        if name is None and description is None:
            raise HTTPException(status_code=400, detail="At least one of 'name' or 'description' must be provided")

        with connection_manager.get_connection() as pg:
            # Check if dashboard exists
            existing = pg.execute(
                "SELECT id, name FROM dashboards WHERE id = %s",
                (dashboard_id,),
                fetch=True
            )

            if not existing or len(existing) == 0:
                raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")

            # Build dynamic UPDATE query based on what was provided
            update_fields = []
            update_values = []

            if name is not None:
                update_fields.append("name = %s")
                update_values.append(name)

            if description is not None:
                update_fields.append("description = %s")
                update_values.append(description)

            update_fields.append("updated_at = NOW()")
            update_values.append(dashboard_id)

            update_query = f"""
                UPDATE dashboards
                SET {', '.join(update_fields)}
                WHERE id = %s
            """

            pg.execute(update_query, tuple(update_values))

            logging.info(f"Dashboard {dashboard_id} metadata updated successfully")
            return {
                "success": True,
                "message": "Dashboard updated successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error updating dashboard metadata: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Datasets API Routes
# ============================================================================

@app.get("/api/datasets")
async def get_datasets():
    """Get all datasets"""
    return await datasets_api.get_all_datasets()


@app.get("/api/datasets/{dataset_id}")
async def get_dataset(dataset_id: str):
    """Get a single dataset by ID"""
    return await datasets_api.get_dataset_by_id(dataset_id)


@app.post("/api/datasets")
async def create_dataset_endpoint(request: Request):
    """Create a new dataset"""
    return await datasets_api.create_dataset(request)


@app.put("/api/datasets/{dataset_id}")
async def update_dataset_endpoint(dataset_id: str, request: Request):
    """Update an existing dataset"""
    return await datasets_api.update_dataset(dataset_id, request)


@app.delete("/api/datasets/{dataset_id}")
async def delete_dataset_endpoint(dataset_id: str):
    """Delete a dataset"""
    return await datasets_api.delete_dataset(dataset_id)


@app.post("/api/datasets/preview")
async def preview_dataset_endpoint(request: Request):
    """Preview data from a dataset"""
    return await datasets_api.preview_dataset(request)


@app.post("/api/datasets/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    dataset_id: str = Form(None),
    dataset_name: str = Form(None),
    dataset_description: str = Form(None),
    preview_only: str = Form(None)
):
    """Upload a CSV file and create a dataset"""
    from postgres import PostgresConnector
    import traceback

    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")

        # Read CSV file
        contents = await file.read()

        # Parse CSV with pandas
        try:
            import io
            df = pd.read_csv(io.BytesIO(contents))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

        # Get columns and data types
        columns = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            # Map pandas dtypes to SQL types
            if dtype.startswith('int'):
                sql_type = 'INTEGER'
            elif dtype.startswith('float'):
                sql_type = 'NUMERIC'
            elif dtype == 'bool':
                sql_type = 'BOOLEAN'
            elif dtype == 'datetime64':
                sql_type = 'TIMESTAMP'
            else:
                sql_type = 'TEXT'

            columns.append({
                'name': col,
                'type': sql_type
            })

        # Preview mode - just return data without saving
        if preview_only == 'true':
            preview_data = df.head(10).to_dict('records')
            return {
                "columns": columns,
                "data": preview_data,
                "row_count": len(df)
            }

        # Save mode - persist the file and create dataset record
        # Create uploads directory if it doesn't exist
        uploads_dir = Path(__file__).parent.parent / "uploads" / "csv"
        uploads_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = uploads_dir / unique_filename

        # Save file
        with open(file_path, 'wb') as f:
            f.write(contents)

        file_size = len(contents)

        # Create dataset record in database
        from connection_manager import connection_manager

        # Use provided dataset_id or generate new one
        if not dataset_id:
            dataset_id = f"dataset_{uuid.uuid4().hex[:8]}"

        # Generate table name from dataset name
        table_name = dataset_name or file.filename.replace('.csv', '')
        # Clean table name to be SQL-safe
        table_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in table_name.lower())
        table_name = f"csv_{table_name}"

        # Import CSV data into a database table
        with connection_manager.get_connection() as pg:
            import json

            # Create table with columns based on detected types
            create_cols = []
            for col in columns:
                col_name = col['name']
                col_type = col['type']
                # Escape column names with quotes to handle spaces and special chars
                create_cols.append(f'"{col_name}" {col_type}')

            create_table_sql = f"""
                DROP TABLE IF EXISTS {table_name};
                CREATE TABLE {table_name} (
                    {', '.join(create_cols)}
                );
            """

            pg.execute(create_table_sql)
            logging.info(f"Created table {table_name} for CSV data")

            # Insert data into table
            if len(df) > 0:
                # Use pandas to_sql for efficient bulk insert
                from sqlalchemy import create_engine
                import os

                # Create SQLAlchemy engine from connection details
                db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/transformdash')
                engine = create_engine(db_url)

                # Insert dataframe into table
                df.to_sql(table_name, engine, if_exists='replace', index=False)
                logging.info(f"Inserted {len(df)} rows into {table_name}")

            # Insert dataset record
            pg.execute("""
                INSERT INTO datasets (
                    id, name, description, source_type,
                    table_name, schema_name,
                    file_path, original_filename, file_size_bytes,
                    columns, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, NOW(), NOW()
                )
            """, (
                dataset_id,
                dataset_name or file.filename.replace('.csv', ''),
                dataset_description or '',
                'csv',
                table_name,
                'public',
                str(file_path),
                file.filename,
                file_size,
                json.dumps(columns)
            ))

        logging.info(f"CSV dataset created: {dataset_id} from file {file.filename}, imported to table {table_name}")

        return {
            "success": True,
            "dataset_id": dataset_id,
            "columns": columns,
            "row_count": len(df),
            "file_size": file_size
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error uploading CSV: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Table/Column Metadata Routes
# ============================================================================

@app.get("/api/tables/{table_name}/columns")
async def get_table_columns(table_name: str, schema: str = "public", connection_id: str = None):
    """Get columns for a specific table or view"""
    try:
        from connection_manager import connection_manager
        import logging

        # Get connection from connection manager
        with connection_manager.get_connection(connection_id) as pg:
            # Use pg_attribute for more reliable column information
            # Also check if column is part of any index
            query = """
                WITH index_columns AS (
                    SELECT
                        i.indrelid,
                        unnest(i.indkey) as attnum,
                        i.indisprimary,
                        i.indisunique
                    FROM pg_catalog.pg_index i
                    JOIN pg_catalog.pg_class c ON i.indrelid = c.oid
                    JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
                    WHERE n.nspname = %s
                    AND c.relname = %s
                )
                SELECT
                    a.attname as column_name,
                    pg_catalog.format_type(a.atttypid, a.atttypmod) as data_type,
                    CASE
                        WHEN bool_or(ic.indisprimary) THEN 'primary'
                        WHEN bool_or(ic.indisunique) THEN 'unique'
                        WHEN COUNT(ic.attnum) > 0 THEN 'index'
                        ELSE NULL
                    END as index_type,
                    a.attnum as column_order
                FROM pg_catalog.pg_attribute a
                JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
                JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
                LEFT JOIN index_columns ic ON a.attrelid = ic.indrelid AND a.attnum = ic.attnum
                WHERE n.nspname = %s
                AND c.relname = %s
                AND a.attnum > 0
                AND NOT a.attisdropped
                GROUP BY a.attname, a.atttypid, a.atttypmod, a.attnum
                ORDER BY column_order
            """
            logging.info(f"Fetching columns for connection {connection_id or 'default'}.{schema}.{table_name}")
            result = pg.execute(query, (schema, table_name, schema, table_name), fetch=True)
            columns = [{"name": row['column_name'], "type": row['data_type'], "index_type": row['index_type']} for row in result]
            logging.info(f"Found {len(columns)} columns for {schema}.{table_name}")
            return {"columns": columns}
    except Exception as e:
        import logging
        import traceback
        logging.error(f"Error fetching columns: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
async def query_data(request: Request):
    """Execute a query and return aggregated data for charting"""
    try:
        from postgres import PostgresConnector
        import logging

        body = await request.json()
        logging.info(f"Query request body: {body}")
        logging.info(f"Body keys: {body.keys()}")

        table = body.get('table') or body.get('model')
        chart_type = body.get('type', 'bar')
        metric = body.get('metric')
        x_axis = body.get('x_axis')
        y_axis = body.get('y_axis')
        aggregation = body.get('aggregation', 'sum')
        filters = body.get('filters', {})
        filter_expressions = body.get('filter_expressions', {})
        schema = body.get('schema', 'public')
        connection_id = body.get('connection_id')

        logging.info(f"Extracted table/model: {table}, schema: {schema}, connection_id: {connection_id}")
        logging.info(f"Filters: {filters}, Filter expressions: {filter_expressions}")

        if not table:
            logging.error(f"No table found! Body was: {body}")
            raise HTTPException(status_code=400, detail="Missing table/model parameter")

        from connection_manager import connection_manager

        # Helper function to build WHERE clause for filters with optional expressions
        def build_filter_clauses(filters, filter_expressions, available_columns):
            """Build WHERE clauses supporting SQL expressions for filters"""
            where_clauses = []
            params = []

            for field, value in filters.items():
                if not value:
                    continue

                # Check if there's an SQL expression for this filter
                if field in filter_expressions and filter_expressions[field]:
                    # Use the SQL expression instead of the raw field
                    expression = filter_expressions[field]
                    where_clauses.append(f"({expression}) = %s")
                    params.append(value)
                elif field in available_columns:
                    # Use the field directly
                    where_clauses.append(f"{field} = %s")
                    params.append(value)

            return where_clauses, params

        with connection_manager.get_connection(connection_id) as pg:
            # First, get available columns for this table
            col_query = """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
            """
            col_result = pg.execute(col_query, (schema, table), fetch=True)
            available_columns = {row['column_name'] for row in col_result}

            # Handle table type charts (data table display)
            if chart_type == 'table':
                columns = body.get('columns', [])
                if not columns:
                    raise HTTPException(status_code=400, detail="Missing columns for table chart")

                # Build WHERE clauses from filters using helper function
                where_clauses, params = build_filter_clauses(filters, filter_expressions, available_columns)
                where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

                # Build column selection
                column_names = ', '.join(columns)
                query = f"""
                    SELECT {column_names}
                    FROM {schema}.{table}
                    {where_sql}
                    LIMIT 100
                """

                df = pg.query_to_dataframe(query, tuple(params) if params else None)

                # Convert DataFrame to list of dictionaries
                data = df.to_dict('records')

                return {
                    "columns": columns,
                    "data": data
                }

            # Handle metric type charts (single value)
            if chart_type == 'metric' and metric:
                # Build WHERE clauses from filters using helper function
                where_clauses, params = build_filter_clauses(filters, filter_expressions, available_columns)
                where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

                agg_func = aggregation.upper()
                query = f"""
                    SELECT {agg_func}({metric}) as value
                    FROM {schema}.{table}
                    {where_sql}
                """

                df = pg.query_to_dataframe(query, tuple(params) if params else None)
                value = df['value'].iloc[0] if len(df) > 0 else 0

                # Handle NaN values
                import math
                if value is None or (isinstance(value, float) and math.isnan(value)):
                    value = 0

                return {
                    "value": float(value),
                    "labels": [],
                    "values": []
                }

            # Handle multi-metric charts (multiple series on same chart)
            metrics = body.get('metrics')
            if metrics and isinstance(metrics, list):
                if not x_axis:
                    raise HTTPException(status_code=400, detail="Missing x_axis for multi-metric chart")

                # Build WHERE clauses from filters using helper function
                filter_clauses, params = build_filter_clauses(filters, filter_expressions, available_columns)
                where_clauses = [f"{x_axis} IS NOT NULL"] + filter_clauses
                where_sql = "WHERE " + " AND ".join(where_clauses)

                # Build query with multiple aggregations
                metric_selects = []
                for metric in metrics:
                    field = metric.get('field')
                    agg = metric.get('aggregation', 'sum').upper()
                    label = metric.get('label', field)
                    metric_selects.append(f"{agg}({field}) as {field}")

                query = f"""
                    SELECT
                        {x_axis} as label,
                        {', '.join(metric_selects)}
                    FROM {schema}.{table}
                    {where_sql}
                    GROUP BY {x_axis}
                    ORDER BY {x_axis}
                    LIMIT 50
                """

                df = pg.query_to_dataframe(query, tuple(params) if params else None)

                # Convert to multi-series format
                import math
                labels = df['label'].astype(str).tolist()
                datasets = []

                for metric in metrics:
                    field = metric.get('field')
                    label = metric.get('label', field)
                    values = [
                        None if (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) else v
                        for v in df[field].tolist()
                    ]
                    datasets.append({
                        'label': label,
                        'data': values
                    })

                return {
                    "labels": labels,
                    "datasets": datasets
                }

            # Handle regular charts with x_axis and y_axis
            if not all([x_axis, y_axis]):
                raise HTTPException(status_code=400, detail="Missing x_axis or y_axis for chart")

            # Build WHERE clauses from filters using helper function
            filter_clauses, params = build_filter_clauses(filters, filter_expressions, available_columns)
            where_clauses = [f"{x_axis} IS NOT NULL"] + filter_clauses
            where_sql = "WHERE " + " AND ".join(where_clauses)

            # Check if this is a stacked bar chart with a category field
            category = body.get('category')
            if chart_type == 'bar-stacked' and category:
                # For stacked charts, we need to pivot data by category
                agg_func = aggregation.upper()
                query = f"""
                    SELECT
                        {x_axis} as label,
                        {category} as category,
                        {agg_func}({y_axis}) as value
                    FROM {schema}.{table}
                    {where_sql}
                    GROUP BY {x_axis}, {category}
                    ORDER BY {x_axis}, {category}
                    LIMIT 500
                """

                df = pg.query_to_dataframe(query, tuple(params) if params else None)

                # Pivot the data to create multiple datasets (one per category)
                import pandas as pd
                import math

                # Get unique categories and labels
                categories = df['category'].unique().tolist()
                labels = sorted(df['label'].unique().tolist(), key=str)

                # Build datasets for each category
                datasets = []
                for cat in categories:
                    cat_data = df[df['category'] == cat]
                    # Create a value for each label, filling missing with 0
                    values = []
                    for label in labels:
                        matching = cat_data[cat_data['label'] == label]
                        if len(matching) > 0:
                            val = matching['value'].iloc[0]
                            # Handle NaN/inf
                            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                                values.append(0)
                            else:
                                values.append(float(val) if val is not None else 0)
                        else:
                            values.append(0)

                    datasets.append({
                        "label": str(cat),
                        "data": values
                    })

                return {
                    "labels": [str(l) for l in labels],
                    "datasets": datasets
                }
            else:
                # Regular (non-stacked) chart
                agg_func = aggregation.upper()
                query = f"""
                    SELECT
                        {x_axis} as label,
                        {agg_func}({y_axis}) as value
                    FROM {schema}.{table}
                    {where_sql}
                    GROUP BY {x_axis}
                    ORDER BY {x_axis}
                    LIMIT 50
                """

                df = pg.query_to_dataframe(query, tuple(params) if params else None)

                # Convert to chart-friendly format
                # Replace NaN with None for JSON compatibility
                import math
                labels = df['label'].astype(str).tolist()
                values = [
                    None if (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) else v
                    for v in df['value'].tolist()
                ]

                return {
                    "labels": labels,
                    "values": values
                }
    except Exception as e:
        import traceback
        logging.error(f"Query error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/connections/list")
async def list_connections():
    """List all configured database connections"""
    try:
        from connection_manager import connection_manager
        import logging

        connections = connection_manager.list_connections()
        logging.info(f"Found {len(connections)} configured connections")
        return {"connections": connections}

    except Exception as e:
        import traceback
        logging.error(f"Error listing connections: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/databases/list")
async def list_databases():
    """List all databases"""
    try:
        from postgres import PostgresConnector
        import logging

        with PostgresConnector() as pg:
            query = """
                SELECT datname as name
                FROM pg_database
                WHERE datistemplate = false
                ORDER BY datname
            """
            result = pg.execute(query, fetch=True)
            databases = [row['name'] for row in result]
            logging.info(f"Found {len(databases)} databases")
            return {"databases": databases}

    except Exception as e:
        import traceback
        logging.error(f"Error listing databases: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/schemas/list")
async def list_schemas(connection_id: str = None):
    """List all schemas in specified connection"""
    try:
        from connection_manager import connection_manager
        import logging

        # Get connection from connection manager
        with connection_manager.get_connection(connection_id) as pg:
            query = """
                SELECT nspname as name
                FROM pg_namespace
                WHERE nspname NOT LIKE 'pg_%'
                  AND nspname != 'information_schema'
                ORDER BY nspname
            """
            result = pg.execute(query, fetch=True)
            schemas = [row['name'] for row in result]
            logging.info(f"Found {len(schemas)} schemas in connection {connection_id or 'default'}")
            return {"schemas": schemas}

    except Exception as e:
        import traceback
        logging.error(f"Error listing schemas: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tables/list")
async def list_tables(schema: str = "public", connection_id: str = None):
    """List all tables/views in the database for SQL Query Lab"""
    try:
        from connection_manager import connection_manager
        import logging

        # Get connection from connection manager
        with connection_manager.get_connection(connection_id) as pg:
            # Get all tables and views with their sizes
            query = """
                SELECT
                    t.tablename as name,
                    'table' as type,
                    pg_size_pretty(pg_total_relation_size(quote_ident(t.schemaname) || '.' || quote_ident(t.tablename))) as size
                FROM pg_catalog.pg_tables t
                WHERE t.schemaname = %s
                UNION ALL
                SELECT
                    v.viewname as name,
                    'view' as type,
                    '-' as size
                FROM pg_catalog.pg_views v
                WHERE v.schemaname = %s
                    AND v.viewname NOT LIKE 'pg_%%'
                ORDER BY name
            """
            result = pg.execute(query, (schema, schema), fetch=True)

            tables = []
            for row in result:
                tables.append({
                    'name': str(row['name']),
                    'type': str(row['type']),
                    'size': str(row['size']) if row['size'] else '-'
                })

            logging.info(f"Found {len(tables)} database objects in connection {connection_id or 'default'}.{schema}")
            return {"tables": tables}

    except Exception as e:
        import traceback
        logging.error(f"Error listing tables: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/filter/values")
async def get_filter_values(request: Request):
    """Get distinct values for a filter field (supports SQL expressions)"""
    try:
        from connection_manager import connection_manager
        import logging

        body = await request.json()
        table = body.get('table')
        field = body.get('field')
        expression = body.get('expression')  # Optional SQL expression
        schema = body.get('schema', 'public')
        connection_id = body.get('connection_id')

        if not table:
            raise HTTPException(status_code=400, detail="Table name is required")

        if not field and not expression:
            raise HTTPException(status_code=400, detail="Either field or expression is required")

        # Use expression if provided, otherwise use field
        query_field = expression if expression else field

        # Get connection from connection manager
        with connection_manager.get_connection(connection_id) as pg:
            # Set search path to use the selected schema
            if schema:
                pg.execute(f"SET search_path TO {schema}, public")

            # Build query to get distinct values
            query = f"""
                SELECT DISTINCT {query_field} as value
                FROM {table}
                WHERE {query_field} IS NOT NULL
                ORDER BY {query_field}
                LIMIT 1000
            """

            logging.info(f"Fetching filter values: {query}")
            result = pg.execute(query, fetch=True)

            values = [row['value'] for row in result]
            logging.info(f"Found {len(values)} distinct values for {field or expression}")

            return {"values": values}

    except Exception as e:
        import traceback
        logging.error(f"Error fetching filter values: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query/execute")
async def execute_query(request: Request):
    """Execute a SQL query and return results for SQL Query Lab"""
    try:
        from postgres import PostgresConnector
        import logging

        body = await request.json()
        sql = body.get('sql', '').strip()
        connection_id = body.get('connection_id')
        schema = body.get('schema', 'public')

        if not sql:
            raise HTTPException(status_code=400, detail="SQL query is required")

        # Safety check: only allow SELECT queries
        sql_upper = sql.upper().strip()
        if not sql_upper.startswith('SELECT') and not sql_upper.startswith('WITH'):
            raise HTTPException(
                status_code=400,
                detail="Only SELECT queries and CTEs (WITH) are allowed in SQL Query Lab"
            )

        # Additional safety: block dangerous keywords
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                raise HTTPException(
                    status_code=400,
                    detail=f"Query contains forbidden keyword: {keyword}"
                )

        logging.info(f"Executing query in connection={connection_id or 'default'}, schema={schema}")

        # Get connection from connection manager
        from connection_manager import connection_manager
        with connection_manager.get_connection(connection_id) as pg:
            # Set search path to use the selected schema
            if schema:
                pg.execute(f"SET search_path TO {schema}, public")
                logging.info(f"Set search_path to {schema}, public")

            # Execute query and convert to dataframe
            df = pg.query_to_dataframe(sql)

            # Convert to JSON-friendly format
            import math
            import numpy as np
            import json as json_lib

            columns = df.columns.tolist()

            # Replace NaN and Inf with None before converting to dict
            df = df.replace([np.inf, -np.inf], None)
            df = df.where(df.notna(), None)

            # Convert to list of dictionaries
            rows_raw = df.to_dict('records')
            rows = []

            for row_dict in rows_raw:
                row_data = {}
                for col, value in row_dict.items():
                    # Handle None first
                    if value is None:
                        row_data[col] = None
                    # Check for NaN/Inf in both Python float and numpy types BEFORE any conversion
                    elif isinstance(value, (float, np.floating)):
                        # Use pandas isna which handles both Python and numpy NaN
                        import pandas as pd
                        if pd.isna(value) or math.isinf(float(value)):
                            row_data[col] = None
                        else:
                            # Convert numpy float to Python float
                            row_data[col] = float(value)
                    # Convert pandas Timestamp to string
                    elif hasattr(value, 'isoformat'):
                        row_data[col] = value.isoformat()
                    # Handle lists and tuples (PostgreSQL arrays)
                    elif isinstance(value, (list, tuple)):
                        row_data[col] = list(value)
                    # Handle numpy arrays (convert to list)
                    elif isinstance(value, np.ndarray):
                        row_data[col] = value.tolist()
                    # Convert other numpy scalar types to Python native types
                    elif isinstance(value, np.integer):
                        row_data[col] = int(value)
                    elif isinstance(value, np.bool_):
                        row_data[col] = bool(value)
                    # Handle Python native types
                    elif isinstance(value, (int, str, bool)):
                        row_data[col] = value
                    else:
                        # For any other type (UUID, etc.), try JSON serialization or convert to string
                        try:
                            # Test if it's JSON serializable
                            json_lib.dumps(value)
                            row_data[col] = value
                        except (TypeError, ValueError):
                            # Convert to string as fallback (handles UUID, etc.)
                            row_data[col] = str(value)
                rows.append(row_data)

            logging.info(f"Query executed successfully: {len(rows)} rows returned")

            return {
                "success": True,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows)
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error executing query: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@app.post("/api/views/create")
async def create_view(request: Request):
    """Create a database view from a SQL query"""
    try:
        body = await request.json()
        connection_id = body.get('connection_id')
        schema = body.get('schema', 'public')
        view_name = body.get('view_name')
        query = body.get('query', '').strip()

        if not view_name:
            raise HTTPException(status_code=400, detail="View name is required")
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        # Validate view name (alphanumeric and underscores only)
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', view_name):
            raise HTTPException(
                status_code=400,
                detail="Invalid view name. Use only letters, numbers, and underscores."
            )

        # Get connection from connection manager
        from connection_manager import connection_manager
        with connection_manager.get_connection(connection_id) as pg:
            # Create the view
            create_view_sql = f"CREATE OR REPLACE VIEW {schema}.{view_name} AS\n{query}"
            logging.info(f"Creating view: {create_view_sql}")
            pg.execute(create_view_sql)

            logging.info(f"View {schema}.{view_name} created successfully")

            return {
                "success": True,
                "message": f"View {schema}.{view_name} created successfully",
                "view_name": view_name,
                "schema": schema
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error creating view: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to create view: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "transformdash"}


@app.post("/api/dashboard/{dashboard_id}/export")
async def export_dashboard_data(dashboard_id: str, request: Request):
    """Export all dashboard data as CSV or Excel"""
    try:
        from postgres import PostgresConnector
        import yaml
        import io
        from fastapi.responses import StreamingResponse

        body = await request.json()

        dashboards_file = models_dir / "dashboards.yml"
        with open(dashboards_file, 'r') as f:
            data = yaml.safe_load(f)

        dashboard = next((d for d in data.get('dashboards', []) if d['id'] == dashboard_id), None)
        if not dashboard:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        export_format = body.get('format', 'csv')  # csv or excel
        filters = body.get('filters', {})

        # Collect all data from all charts
        all_data = {}

        with PostgresConnector() as pg:
            for chart in dashboard.get('charts', []):
                # Skip metric-only charts and advanced charts
                if chart.get('type') == 'metric' or chart.get('metrics') or chart.get('calculation'):
                    continue

                if not chart.get('model') or not chart.get('x_axis') or not chart.get('y_axis'):
                    continue

                # Build query with filters
                table = chart['model']
                x_axis = chart['x_axis']
                y_axis = chart['y_axis']
                agg_func = chart.get('aggregation', 'sum').upper()

                # Apply filters from request
                where_clauses = []
                params = []
                if filters:
                    for field, value in filters.items():
                        where_clauses.append(f"{field} = %s")
                        params.append(value)

                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

                query = f"""
                    SELECT
                        {x_axis} as label,
                        {agg_func}({y_axis}) as value
                    FROM {schema}.{table}
                    {where_sql}
                    GROUP BY {x_axis}
                    ORDER BY {x_axis}
                """

                df = pg.query_to_dataframe(query, tuple(params) if params else None)
                all_data[chart['title']] = df

        # Export as requested format
        if export_format == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for sheet_name, df in all_data.items():
                    # Excel sheet names have 31 char limit
                    safe_name = sheet_name[:31]
                    df.to_excel(writer, sheet_name=safe_name, index=False)
            output.seek(0)

            return StreamingResponse(
                output,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment; filename="{dashboard_id}_data.xlsx"'}
            )
        else:  # CSV - combine all data
            output = io.StringIO()
            for chart_title, df in all_data.items():
                output.write(f"\n{chart_title}\n")
                df.to_csv(output, index=False)
                output.write("\n")
            output.seek(0)

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type='text/csv',
                headers={'Content-Disposition': f'attachment; filename="{dashboard_id}_data.csv"'}
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/{dashboard_id}/filters")
async def get_dashboard_filters(dashboard_id: str):
    """Get available filter options for a dashboard"""
    try:
        from postgres import PostgresConnector
        import yaml

        dashboards_file = models_dir / "dashboards.yml"
        with open(dashboards_file, 'r') as f:
            data = yaml.safe_load(f)

        dashboard = next((d for d in data.get('dashboards', []) if d['id'] == dashboard_id), None)
        if not dashboard:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        # Collect all possible filter fields from charts
        filter_fields = set()
        models_used = set()

        for chart in dashboard.get('charts', []):
            if chart.get('model'):
                models_used.add(chart['model'])
            if chart.get('filters'):
                for f in chart['filters']:
                    filter_fields.add(f['field'])

        # Get unique values for each filter field
        filters = {}
        with PostgresConnector() as pg:
            for model in models_used:
                # Get columns for this model
                query = f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                """
                result = pg.execute(query, (model,), fetch=True)
                columns = [row['column_name'] for row in result]

                # Get distinct values for common filter columns
                common_filters = ['order_year', 'order_month', 'sale_year', 'sale_month',
                                'order_value_tier', 'status', 'category', 'warehouse_id']

                for col in columns:
                    if any(cf in col.lower() for cf in ['year', 'month', 'tier', 'status', 'category', 'warehouse']):
                        try:
                            query = f"""
                                SELECT DISTINCT {col} as value
                                FROM public.{model}
                                WHERE {col} IS NOT NULL
                                ORDER BY {col}
                                LIMIT 100
                            """
                            result = pg.execute(query, fetch=True)
                            values = [row['value'] for row in result]
                            if values:
                                filters[col] = {
                                    'label': col.replace('_', ' ').title(),
                                    'values': values
                                }
                        except:
                            continue

        return {"filters": filters}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data-quality/orphaned-models")
async def get_orphaned_models():
    """
    Detect orphaned database objects - tables/views that exist in the database
    but are not defined in any dbt model files.

    This helps identify:
    - Old tables that should be cleaned up
    - Manual tables created outside the dbt workflow
    - Test tables that weren't removed
    """
    try:
        from postgres import PostgresConnector
        import logging

        # Get all database objects in public schema
        with PostgresConnector() as pg:
            db_objects_query = """
                SELECT tablename AS name, 'table' AS type
                FROM pg_catalog.pg_tables
                WHERE schemaname = 'public'
                UNION ALL
                SELECT matviewname AS name, 'materialized_view' AS type
                FROM pg_catalog.pg_matviews
                WHERE schemaname = 'public'
                UNION ALL
                SELECT viewname AS name, 'view' AS type
                FROM pg_catalog.pg_views
                WHERE schemaname = 'public'
                    AND viewname NOT LIKE 'pg_%'
                ORDER BY name
            """
            db_objects = pg.execute(db_objects_query, fetch=True)

        # Get all model names from dbt
        models = loader.load_all_models()
        model_names = set(model.name for model in models)

        # Also check sources from sources.yml
        import yaml
        sources_file = models_dir / "sources.yml"
        raw_tables = set()

        if sources_file.exists():
            with open(sources_file, 'r') as f:
                sources_config = yaml.safe_load(f) or {}
                for source in sources_config.get('sources', []):
                    for table in source.get('tables', []):
                        raw_tables.add(table['name'])

        # Find orphaned objects
        orphaned = []
        managed = []

        for obj in db_objects:
            obj_name = obj['name']
            obj_type = obj['type']

            is_model = obj_name in model_names
            is_source = obj_name in raw_tables

            if not is_model and not is_source:
                orphaned.append({
                    'name': obj_name,
                    'type': obj_type,
                    'reason': 'Not defined in any model or source'
                })
            else:
                managed.append({
                    'name': obj_name,
                    'type': obj_type,
                    'managed_by': 'dbt_model' if is_model else 'raw_source'
                })

        return {
            'orphaned': orphaned,
            'managed': managed,
            'summary': {
                'total_objects': len(db_objects),
                'orphaned_count': len(orphaned),
                'managed_count': len(managed),
                'status': 'clean' if len(orphaned) == 0 else 'needs_attention'
            }
        }

    except Exception as e:
        import traceback
        logging.error(f"Error detecting orphaned models: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SCHEDULE MANAGEMENT ENDPOINTS
# =============================================================================

from scheduler import get_scheduler
from connection_manager import connection_manager
from pydantic import BaseModel

class ScheduleCreate(BaseModel):
    schedule_name: str
    model_names: list[str]  # Changed to support multiple models
    cron_expression: str
    description: str = None
    timezone: str = 'UTC'
    max_retries: int = 0

class ScheduleUpdate(BaseModel):
    schedule_name: str = None
    model_names: list[str] = None
    cron_expression: str = None
    description: str = None
    is_active: bool = None
    timezone: str = None

@app.get("/api/schedules")
async def list_schedules():
    """Get all model schedules with their status"""
    try:
        with connection_manager.get_connection() as pg:
            schedules = pg.execute("""
                SELECT * FROM v_schedule_status
                ORDER BY created_at DESC
            """, fetch=True) or []
        return {"schedules": schedules}
    except Exception as e:
        import traceback
        logging.error(f"Error listing schedules: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/schedules")
async def create_schedule(schedule: ScheduleCreate):
    """Create a new model schedule with support for multiple models"""
    try:
        # Validate models exist
        all_models = loader.load_all_models()
        model_map = {m.name: m for m in all_models}

        for model_name in schedule.model_names:
            if model_name not in model_map:
                raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # Validate cron expression
        parts = schedule.cron_expression.split()
        if len(parts) != 5:
            raise HTTPException(status_code=400, detail="Invalid cron expression. Expected format: 'minute hour day month day_of_week'")

        # Insert into database
        with connection_manager.get_connection() as pg:
            # Create the schedule (no longer requires model_name)
            result = pg.execute("""
                INSERT INTO model_schedules (
                    schedule_name, cron_expression,
                    description, timezone, max_retries, is_active
                )
                VALUES (%s, %s, %s, %s, %s, TRUE)
                RETURNING id, schedule_name, cron_expression
            """, params=(
                schedule.schedule_name,
                schedule.cron_expression,
                schedule.description,
                schedule.timezone,
                schedule.max_retries
            ), fetch=True)

            schedule_record = result[0]
            schedule_id = schedule_record['id']

            # Add models to schedule_models table
            for idx, model_name in enumerate(schedule.model_names):
                pg.execute("""
                    INSERT INTO schedule_models (schedule_id, model_name, execution_order)
                    VALUES (%s, %s, %s)
                """, params=(schedule_id, model_name, idx))

        # Add to scheduler
        scheduler = get_scheduler()
        success = scheduler.add_schedule(
            schedule_id=schedule_id,
            model_names=schedule.model_names,
            cron_expression=schedule_record['cron_expression'],
            timezone=schedule.timezone
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to add schedule to scheduler")

        return {
            "message": "Schedule created successfully",
            "schedule": {
                **schedule_record,
                "models": schedule.model_names,
                "model_count": len(schedule.model_names)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error creating schedule: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/schedules/{schedule_id}")
async def get_schedule(schedule_id: int):
    """Get a specific schedule with its run history"""
    try:
        with connection_manager.get_connection() as pg:
            # Get schedule details
            schedule = pg.execute("""
                SELECT * FROM v_schedule_status
                WHERE id = %s
            """, params=(schedule_id,), fetch=True)

            if not schedule:
                raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

            # Get associated models
            models = pg.execute("""
                SELECT model_name
                FROM schedule_models
                WHERE schedule_id = %s
                ORDER BY model_name
            """, params=(schedule_id,), fetch=True)

            # Get recent runs
            runs = pg.execute("""
                SELECT * FROM schedule_runs
                WHERE schedule_id = %s
                ORDER BY started_at DESC
                LIMIT 50
            """, params=(schedule_id,), fetch=True)

        schedule_data = schedule[0]
        schedule_data['models'] = [m['model_name'] for m in models]

        return {
            "schedule": schedule_data,
            "recent_runs": runs
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error getting schedule: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/schedules/{schedule_id}")
async def update_schedule(schedule_id: int, update: ScheduleUpdate):
    """Update a schedule"""
    try:
        scheduler = get_scheduler()

        with connection_manager.get_connection() as pg:
            # Build dynamic update query
            updates = []
            params = []

            if update.schedule_name is not None:
                updates.append("schedule_name = %s")
                params.append(update.schedule_name)

            if update.cron_expression is not None:
                # Validate cron expression
                parts = update.cron_expression.split()
                if len(parts) != 5:
                    raise HTTPException(status_code=400, detail="Invalid cron expression")
                updates.append("cron_expression = %s")
                params.append(update.cron_expression)

            if update.description is not None:
                updates.append("description = %s")
                params.append(update.description)

            if update.is_active is not None:
                updates.append("is_active = %s")
                params.append(update.is_active)

            if update.timezone is not None:
                updates.append("timezone = %s")
                params.append(update.timezone)

            if not updates and update.model_names is None:
                raise HTTPException(status_code=400, detail="No fields to update")

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(schedule_id)

            # Update schedule table if there are updates
            if updates:
                query = f"""
                    UPDATE model_schedules
                    SET {', '.join(updates)}
                    WHERE id = %s
                    RETURNING id, schedule_name, cron_expression, timezone, is_active
                """
                result = pg.execute(query, params, fetch=True)

                if not result:
                    raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

                schedule_record = result[0]
            else:
                # Just get the existing schedule
                schedule_record = pg.execute("""
                    SELECT id, schedule_name, cron_expression, timezone, is_active
                    FROM model_schedules
                    WHERE id = %s
                """, params=(schedule_id,), fetch=True)
                if not schedule_record:
                    raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
                schedule_record = schedule_record[0]

            # Update models if provided
            if update.model_names is not None:
                if not update.model_names:
                    raise HTTPException(status_code=400, detail="At least one model must be selected")

                # Delete old model associations
                pg.execute("""
                    DELETE FROM schedule_models
                    WHERE schedule_id = %s
                """, params=(schedule_id,))

                # Insert new model associations
                for model_name in update.model_names:
                    pg.execute("""
                        INSERT INTO schedule_models (schedule_id, model_name)
                        VALUES (%s, %s)
                    """, params=(schedule_id, model_name))

            # Get updated models for the schedule
            models = pg.execute("""
                SELECT model_name
                FROM schedule_models
                WHERE schedule_id = %s
                ORDER BY model_name
            """, params=(schedule_id,), fetch=True)
            model_names = [m['model_name'] for m in models]

        # Update scheduler if cron, timezone, or models changed, or if activating
        needs_reschedule = (
            update.cron_expression is not None or
            update.timezone is not None or
            update.model_names is not None or
            (update.is_active and update.is_active == True)
        )

        if needs_reschedule:
            scheduler.remove_schedule(schedule_id)
            if schedule_record['is_active'] and model_names:
                scheduler.add_schedule(
                    schedule_id=schedule_record['id'],
                    model_names=model_names,
                    cron_expression=schedule_record['cron_expression'],
                    timezone=schedule_record['timezone']
                )
        elif update.is_active is not None and not update.is_active:
            # Deactivating - remove from scheduler
            scheduler.remove_schedule(schedule_id)

        # Add models to response
        schedule_record['models'] = model_names

        return {
            "message": "Schedule updated successfully",
            "schedule": schedule_record
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error updating schedule: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/schedules/{schedule_id}")
async def delete_schedule(schedule_id: int):
    """Delete a schedule"""
    try:
        scheduler = get_scheduler()

        # Remove from scheduler
        scheduler.remove_schedule(schedule_id)

        # Delete from database
        with connection_manager.get_connection() as pg:
            pg.execute("""
                DELETE FROM model_schedules
                WHERE id = %s
            """, [schedule_id])

        return {"message": "Schedule deleted successfully"}

    except Exception as e:
        import traceback
        logging.error(f"Error deleting schedule: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/schedules/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: int):
    """Toggle a schedule active/inactive"""
    try:
        with connection_manager.get_connection() as pg:
            # Toggle is_active
            result = pg.execute("""
                UPDATE model_schedules
                SET is_active = NOT is_active, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, model_name, cron_expression, timezone, is_active
            """, [schedule_id])

            if not result:
                raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

            schedule_record = result[0]

        scheduler = get_scheduler()

        if schedule_record['is_active']:
            # Activating - add to scheduler
            scheduler.add_schedule(
                schedule_id=schedule_record['id'],
                model_name=schedule_record['model_name'],
                cron_expression=schedule_record['cron_expression'],
                timezone=schedule_record['timezone']
            )
            message = "Schedule activated"
        else:
            # Deactivating - remove from scheduler
            scheduler.remove_schedule(schedule_id)
            message = "Schedule deactivated"

        return {
            "message": message,
            "is_active": schedule_record['is_active']
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error toggling schedule: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/schedules/{schedule_id}/runs")
async def get_schedule_runs(schedule_id: int, limit: int = 50):
    """Get run history for a schedule"""
    try:
        with connection_manager.get_connection() as pg:
            runs = pg.execute("""
                SELECT * FROM schedule_runs
                WHERE schedule_id = %s
                ORDER BY started_at DESC
                LIMIT %s
            """, params=(schedule_id, limit), fetch=True)

        return {"runs": runs}

    except Exception as e:
        import traceback
        logging.error(f"Error getting schedule runs: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


### Assets Management API ###

@app.get("/api/assets")
async def get_assets(asset_type: str = None, tags: str = None):
    """Get all assets, optionally filtered by type and tags"""
    try:
        from connection_manager import connection_manager

        with connection_manager.get_connection('transformdash') as pg:
            # Build query with optional filters
            query = "SELECT * FROM assets WHERE is_active = TRUE"
            params = []

            if asset_type:
                query += " AND asset_type = %s"
                params.append(asset_type)

            if tags:
                tag_list = [t.strip() for t in tags.split(',')]
                query += " AND tags && %s"
                params.append(tag_list)

            query += " ORDER BY created_at DESC"

            assets = pg.execute(query, tuple(params) if params else None, fetch=True)
            return {"assets": assets}

    except Exception as e:
        import traceback
        logging.error(f"Error fetching assets: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/assets/{asset_id}")
async def get_asset(asset_id: int):
    """Get a single asset by ID"""
    try:
        from connection_manager import connection_manager

        with connection_manager.get_connection('transformdash') as pg:
            assets = pg.execute(
                "SELECT * FROM assets WHERE id = %s AND is_active = TRUE",
                (asset_id,),
                fetch=True
            )

            if not assets:
                raise HTTPException(status_code=404, detail="Asset not found")

            return {"asset": assets[0]}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error fetching asset: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/assets/upload")
async def upload_asset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(None),
    asset_type: str = Form(...),
    tags: str = Form(None),
    created_by: str = Form(None)
):
    """Upload a new asset"""
    try:
        from connection_manager import connection_manager
        import shutil

        # Create assets directory if it doesn't exist
        assets_dir = Path(__file__).parent.parent / "assets" / asset_type
        assets_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = assets_dir / unique_filename

        # Save file
        with open(file_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)

        # Get file size
        file_size = file_path.stat().st_size

        # Get relative path
        relative_path = f"{asset_type}/{unique_filename}"

        # Parse tags
        tags_array = [t.strip() for t in tags.split(',')] if tags else []

        # Extract metadata based on file type
        metadata = {}
        if asset_type in ['csv', 'excel']:
            try:
                df = pd.read_csv(file_path) if asset_type == 'csv' else pd.read_excel(file_path)
                metadata = {
                    'columns': list(df.columns),
                    'row_count': len(df),
                    'column_types': {col: str(dtype) for col, dtype in df.dtypes.items()}
                }
            except:
                pass

        # Insert into database
        with connection_manager.get_connection('transformdash') as pg:
            result = pg.execute("""
                INSERT INTO assets (name, description, asset_type, file_path, file_size,
                                   mime_type, created_by, tags, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, asset_type, file_path, created_at
            """, (
                name,
                description,
                asset_type,
                relative_path,
                file_size,
                file.content_type,
                created_by,
                tags_array,
                json.dumps(metadata) if metadata else None
            ), fetch=True)

            asset = result[0] if result else None

            return {
                "message": "Asset uploaded successfully",
                "asset": asset
            }

    except Exception as e:
        import traceback
        logging.error(f"Error uploading asset: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/assets/{asset_id}")
async def update_asset(asset_id: int, request: Request):
    """Update asset metadata"""
    try:
        from connection_manager import connection_manager

        body = await request.json()
        name = body.get('name')
        description = body.get('description')
        tags = body.get('tags', [])

        with connection_manager.get_connection('transformdash') as pg:
            pg.execute("""
                UPDATE assets
                SET name = %s, description = %s, tags = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (name, description, tags, asset_id))

            return {"message": "Asset updated successfully"}

    except Exception as e:
        import traceback
        logging.error(f"Error updating asset: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/assets/{asset_id}")
async def delete_asset(asset_id: int):
    """Soft delete an asset"""
    try:
        from connection_manager import connection_manager

        with connection_manager.get_connection('transformdash') as pg:
            pg.execute(
                "UPDATE assets SET is_active = FALSE WHERE id = %s",
                (asset_id,)
            )

            return {"message": "Asset deleted successfully"}

    except Exception as e:
        import traceback
        logging.error(f"Error deleting asset: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/assets/{asset_id}/download")
async def download_asset(asset_id: int):
    """Download an asset file"""
    try:
        from connection_manager import connection_manager
        from fastapi.responses import FileResponse

        with connection_manager.get_connection('transformdash') as pg:
            assets = pg.execute(
                "SELECT name, file_path, mime_type FROM assets WHERE id = %s AND is_active = TRUE",
                (asset_id,),
                fetch=True
            )

            if not assets:
                raise HTTPException(status_code=404, detail="Asset not found")

            asset = assets[0]
            file_path = Path(__file__).parent.parent / "assets" / asset['file_path']

            if not file_path.exists():
                raise HTTPException(status_code=404, detail="File not found")

            return FileResponse(
                path=file_path,
                filename=asset['name'],
                media_type=asset['mime_type']
            )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error downloading asset: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    from scheduler import start_scheduler

    # Start the scheduler service
    start_scheduler()

    print("\n🚀 Starting TransformDash Web UI...")
    print("📊 Dashboard: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("⏰ Scheduler: Active")
    print("\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
