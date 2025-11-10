"""
TransformDash Web UI - FastAPI Application (Refactored)
Interactive lineage graphs and dashboard with separated concerns
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pathlib import Path
import sys
import pandas as pd

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
                "summary": summary
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
            "summary": summary
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
                INSERT INTO charts (id, title, type, model, x_axis, y_axis, aggregation, columns, category, config)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
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
                chart_id, chart_title, chart_type, chart_model,
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
                    dc.tab_id, dc.position
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
                        'config': chart['config']
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
                    'config': chart['config']
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
                        pg.execute("""
                            INSERT INTO dashboard_charts (dashboard_id, chart_id, tab_id, position)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (dashboard_id, chart_id, tab_id) DO UPDATE SET
                                position = EXCLUDED.position
                        """, (dashboard_id, chart_id, tab_id, chart_idx))

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
                    pg.execute("""
                        INSERT INTO dashboard_charts (dashboard_id, chart_id, tab_id, position)
                        VALUES (%s, %s, NULL, %s)
                        ON CONFLICT (dashboard_id, chart_id, tab_id) DO UPDATE SET
                            position = EXCLUDED.position
                    """, (dashboard_id, chart_id, chart_idx))

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
            query = """
                SELECT
                    a.attname as column_name,
                    pg_catalog.format_type(a.atttypid, a.atttypmod) as data_type
                FROM pg_catalog.pg_attribute a
                JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
                JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
                WHERE n.nspname = %s
                AND c.relname = %s
                AND a.attnum > 0
                AND NOT a.attisdropped
                ORDER BY a.attnum
            """
            logging.info(f"Fetching columns for connection {connection_id or 'default'}.{schema}.{table_name}")
            result = pg.execute(query, (schema, table_name), fetch=True)
            columns = [{"name": row['column_name'], "type": row['data_type']} for row in result]
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


if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting TransformDash Web UI...")
    print("📊 Dashboard: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
