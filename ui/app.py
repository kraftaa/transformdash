"""
TransformDash Web UI - FastAPI Application (Refactored)
Interactive lineage graphs and dashboard with separated concerns
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pathlib import Path
import sys
import pandas as pd
import logging
import uuid
import os
import json
import traceback
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from transformations.model_loader import ModelLoader
from transformations import DAG
from orchestration.history import RunHistory
import datasets_api

# Import authentication utilities
from auth import get_current_user, require_permission, require_role

# Import rate limiting
from rate_limiter import RateLimitMiddleware, check_rate_limit

# Import AI assistant (optional)
try:
    from dbt_assistant import DbtAssistant, AVAILABLE as AI_SEARCH_AVAILABLE
    if not AI_SEARCH_AVAILABLE:
        logger.info("dbt_assistant dependencies not installed - AI search disabled")
except ImportError as e:
    AI_SEARCH_AVAILABLE = False
    logger.info(f"dbt_assistant not available: {e} - AI search disabled")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# Authentication Helper Functions
# =============================================================================

async def require_auth(request: Request):
    """Require authentication for endpoint (any logged-in user)"""
    return await get_current_user(request)

def require_models_execute():
    """Require permission to execute transformation models"""
    return require_permission('models', 'execute')

def require_models_write():
    """Require permission to create/edit models"""
    return require_permission('models', 'write')

def require_models_read():
    """Require permission to view models"""
    return require_permission('models', 'read')

def require_datasets_write():
    """Require permission to create/edit/delete datasets"""
    return require_permission('datasets', 'write')

def require_datasets_read():
    """Require permission to view datasets"""
    return require_permission('datasets', 'read')

def require_charts_write():
    """Require permission to create/edit/delete charts"""
    return require_permission('charts', 'write')

def require_charts_read():
    """Require permission to view charts"""
    return require_permission('charts', 'read')

def require_dashboards_write():
    """Require permission to create/edit/delete dashboards"""
    return require_permission('dashboards', 'write')

def require_dashboards_read():
    """Require permission to view dashboards"""
    return require_permission('dashboards', 'read')

def require_schedules_manage():
    """Require permission to manage schedules"""
    return require_permission('schedules', 'write')

def require_schedules_read():
    """Require permission to view schedules"""
    return require_permission('schedules', 'read')

def require_users_manage():
    """Require permission to manage users"""
    return require_permission('users', 'write')

def require_users_read():
    """Require permission to view users"""
    return require_permission('users', 'read')

def require_permissions_manage():
    """Require permission to manage roles and permissions"""
    return require_permission('permissions', 'write')

def require_queries_execute():
    """Require permission to execute SQL queries"""
    return require_permission('queries', 'execute')

app = FastAPI(title="TransformDash", description="Hybrid Data Transformation Platform")

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Global state
models_dir = Path(__file__).parent.parent / "models"
loader = ModelLoader(models_dir=str(models_dir))
run_history = RunHistory()

# Initialize AI assistant if available
ai_assistant = None
# Check if AI search is explicitly disabled (useful for low-memory environments like Render free tier)
disable_ai_search = os.getenv('DISABLE_AI_SEARCH', 'false').lower() == 'true'

if AI_SEARCH_AVAILABLE and not disable_ai_search:
    try:
        logger.info("Initializing AI search assistant...")
        ai_assistant = DbtAssistant(models_dir=str(models_dir))
        logger.info("✅ AI search assistant ready")
    except Exception as e:
        logger.warning(f"Failed to initialize AI assistant: {e}")
        ai_assistant = None
elif disable_ai_search:
    logger.info("AI search disabled via DISABLE_AI_SEARCH environment variable")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve the login page"""
    import time
    response = templates.TemplateResponse("login.html", {
        "request": request,
        "cache_bust": int(time.time() * 1000)
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main dashboard HTML (requires authentication)"""
    import yaml
    import time
    from auth import get_optional_user

    # Check if user is authenticated
    user = await get_optional_user(request)
    if not user:
        # Redirect to login page
        return RedirectResponse(url="/login", status_code=302)

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
        "cache_bust": int(time.time() * 1000),
        "user": user
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
async def get_models(
    request: Request,
    user: dict = Depends(require_models_read())
):
    """Get all models with their dependencies (requires view_models permission)"""
    try:
        models = loader.load_all_models()

        return [{
            "name": model.name,
            "type": model.model_type.value,
            "depends_on": model.depends_on,
            "config": getattr(model, 'config', {}),
            "file_path": getattr(model, 'file_path', ''),
            "description": getattr(model, 'description', '')
        } for model in models]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/search")
async def ai_search_models(
    q: str,
    top_k: int = 5,
    request: Request = None,
    user: dict = Depends(require_models_read())
):
    """
    AI-powered semantic search for models using natural language

    Args:
        q: Natural language search query (e.g., 'customer revenue models')
        top_k: Number of results to return (default: 5)

    Returns:
        Search results with similarity scores

    Requires view_models permission
    """
    if not AI_SEARCH_AVAILABLE or ai_assistant is None:
        raise HTTPException(
            status_code=503,
            detail="AI search is not available. Install dependencies with: pip install -r dbt_assistant/requirements.txt"
        )

    try:
        results = ai_assistant.search(q, top_k=top_k)
        return results
    except Exception as e:
        logger.error(f"AI search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


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
async def get_model_code(
    model_name: str,
    request: Request,
    user: dict = Depends(require_models_read())
):
    """Get the code for a specific model (SQL or Python) (requires view_models permission)"""
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
async def execute_transformations(
    request: Request,
    user: dict = Depends(require_models_execute())
):
    """Execute all transformations in DAG order (requires execute_models permission)"""
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
async def execute_single_model(
    model_name: str,
    request: Request,
    user: dict = Depends(require_models_execute())
):
    """Execute a single transformation model (and its dependencies) (requires execute_models permission)"""
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

                    # Extract logs related to this specific model
                    model_logs = []
                    if 'logs' in run:
                        for log in run['logs']:
                            # Include logs that mention this model name
                            if model_name in log:
                                model_logs.append(log)

                    model_runs.append({
                        'run_id': run['run_id'],
                        'timestamp': run['timestamp'],
                        'status': model_info['status'],
                        'execution_time': model_info['execution_time'],
                        'error': model_info.get('error', None),
                        'logs': model_logs
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


@app.delete("/api/ml/models/{model_name}")
async def delete_ml_model(model_name: str):
    """Delete an ML model and all its versions"""
    try:
        from ml.registry.model_registry import model_registry

        # Delete model (this deletes all versions)
        model_registry.delete_model(model_name)

        return {
            "success": True,
            "message": f"Model '{model_name}' deleted successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
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
                        dc.position,
                        dc.custom_width,
                        dc.custom_height
                    FROM charts c
                    INNER JOIN dashboard_charts dc ON c.id = dc.chart_id
                    WHERE dc.dashboard_id = %s
                    ORDER BY dc.position
                """
                charts = pg.execute(charts_query, (dashboard_id,), fetch=True)

                # Map charts with camelCase for custom dimensions
                formatted_charts = []
                for chart in charts:
                    chart_dict = dict(chart)
                    # Add camelCase versions of custom dimensions
                    if 'custom_width' in chart_dict:
                        chart_dict['customWidth'] = chart_dict['custom_width']
                    if 'custom_height' in chart_dict:
                        chart_dict['customHeight'] = chart_dict['custom_height']
                    formatted_charts.append(chart_dict)

                result.append({
                    'id': dashboard['id'],
                    'name': dashboard['name'],
                    'description': dashboard['description'],
                    'tabs': [{'id': t['id'], 'name': t['name']} for t in tabs],
                    'filters': [dict(f) for f in filters],
                    'charts': formatted_charts
                })

            return {"dashboards": result}
    except Exception as e:
        import logging
        logging.error(f"Error getting dashboards: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dashboards")
async def create_dashboard(request: Request):
    """Create a new dashboard"""
    try:
        import logging
        import re
        from connection_manager import connection_manager

        body = await request.json()
        dashboard_name = body.get("name", "").strip()
        dashboard_description = body.get("description", "").strip()

        if not dashboard_name:
            raise HTTPException(status_code=400, detail="Dashboard name is required")

        # Generate dashboard ID from name (lowercase, replace spaces with hyphens)
        dashboard_id = re.sub(r'[^a-z0-9]+', '-', dashboard_name.lower()).strip('-')

        with connection_manager.get_connection() as pg:
            # Check if dashboard with this ID already exists
            existing = pg.execute(
                "SELECT id FROM dashboards WHERE id = %s",
                (dashboard_id,),
                fetch=True
            )

            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Dashboard with name '{dashboard_name}' already exists. Please choose a different name."
                )

            # Create new dashboard in database
            pg.execute("""
                INSERT INTO dashboards (id, name, description)
                VALUES (%s, %s, %s)
            """, (dashboard_id, dashboard_name, dashboard_description or f"Custom dashboard: {dashboard_name}"))

            # Create default tab
            pg.execute("""
                INSERT INTO dashboard_tabs (id, dashboard_id, name, position)
                VALUES (%s, %s, %s, %s)
            """, (f"{dashboard_id}-tab-default", dashboard_id, "Main", 0))

        logging.info(f"Created new dashboard: {dashboard_id}")

        return {
            "success": True,
            "message": f"Dashboard '{dashboard_name}' created successfully!",
            "dashboard": {
                "id": dashboard_id,
                "name": dashboard_name,
                "description": dashboard_description or f"Custom dashboard: {dashboard_name}",
                "charts": []
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating dashboard: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/dashboards/{dashboard_id}")
async def delete_dashboard(dashboard_id: str, request: Request):
    """Delete a dashboard and all its associated data"""
    try:
        import logging
        from connection_manager import connection_manager

        with connection_manager.get_connection() as pg:
            # Check if dashboard exists
            existing = pg.execute(
                "SELECT id, name FROM dashboards WHERE id = %s",
                (dashboard_id,),
                fetch=True
            )

            if not existing:
                raise HTTPException(status_code=404, detail=f"Dashboard '{dashboard_id}' not found")

            dashboard_name = existing[0][1]

            # Delete in order: filters, chart associations, tabs, dashboard
            pg.execute("DELETE FROM dashboard_filters WHERE dashboard_id = %s", (dashboard_id,))
            pg.execute("DELETE FROM dashboard_charts WHERE dashboard_id = %s", (dashboard_id,))
            pg.execute("DELETE FROM dashboard_tabs WHERE dashboard_id = %s", (dashboard_id,))
            pg.execute("DELETE FROM dashboards WHERE id = %s", (dashboard_id,))

        logging.info(f"Deleted dashboard: {dashboard_id}")

        return {
            "success": True,
            "message": f"Dashboard '{dashboard_name}' deleted successfully!"
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting dashboard: {str(e)}\n{traceback.format_exc()}")
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
                    dc.tab_id,
                    d.name as dashboard_name
                FROM charts c
                LEFT JOIN dashboard_charts dc ON c.id = dc.chart_id
                LEFT JOIN dashboards d ON dc.dashboard_id = d.id
                ORDER BY c.chart_number ASC
            """, fetch=True)

            # Group charts and aggregate their dashboard assignments
            charts_map = {}
            if charts_data:
                for row in charts_data:
                    chart_id = row['id']

                    # Create chart dict if it doesn't exist
                    if chart_id not in charts_map:
                        charts_map[chart_id] = {
                            'id': chart_id,
                            'chart_number': row['chart_number'],
                            'title': row['title'],
                            'description': row.get('description', ''),
                            'type': row['type'],
                            'model': row['model'],
                            'connection_id': row['connection_id'],
                            'x_axis': row['x_axis'],
                            'y_axis': row['y_axis'],
                            'aggregation': row['aggregation'],
                            'columns': row['columns'] if row['columns'] else [],
                            'category': row['category'],
                            'config': row['config'] if row['config'] else {},
                            'created_at': str(row['created_at']) if row['created_at'] else None,
                            'updated_at': str(row['updated_at']) if row['updated_at'] else None,
                            'dashboards': []  # Array of dashboard assignments
                        }

                    # Add dashboard assignment if it exists
                    if row['dashboard_id']:
                        charts_map[chart_id]['dashboards'].append({
                            'id': row['dashboard_id'],
                            'name': row['dashboard_name'],
                            'tab_id': row['tab_id']
                        })

            all_charts = list(charts_map.values())

            logging.info(f"Fetched {len(all_charts)} charts from database")
            return {"charts": all_charts}

    except Exception as e:
        import logging
        logging.error(f"Error fetching charts: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/charts/save")
async def save_chart(
    request: Request,
    user: dict = Depends(require_charts_write())
):
    """Save a chart configuration to database (requires create_charts permission)"""
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
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        logging.error(f"Error saving chart: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/charts/{chart_id}")
async def delete_chart(
    chart_id: str,
    request: Request,
    user: dict = Depends(require_charts_write())
):
    """Delete a chart from the database (requires delete_charts permission)"""
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
                    dc.tab_id, dc.position, dc.size, dc.custom_width, dc.custom_height
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
                        'size': chart.get('size', 'medium'),
                        'customWidth': chart.get('custom_width'),
                        'customHeight': chart.get('custom_height')
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
                    'size': chart.get('size', 'medium'),
                    'customWidth': chart.get('custom_width'),
                    'customHeight': chart.get('custom_height')
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
                        custom_width = chart.get('customWidth')
                        custom_height = chart.get('customHeight')
                        pg.execute("""
                            INSERT INTO dashboard_charts (dashboard_id, chart_id, tab_id, position, size, custom_width, custom_height)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (dashboard_id, chart_id, tab_id) DO UPDATE SET
                                position = EXCLUDED.position,
                                size = EXCLUDED.size,
                                custom_width = EXCLUDED.custom_width,
                                custom_height = EXCLUDED.custom_height
                        """, (dashboard_id, chart_id, tab_id, chart_idx, chart_size, custom_width, custom_height))

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
                    custom_width = chart.get('customWidth')
                    custom_height = chart.get('customHeight')
                    pg.execute("""
                        INSERT INTO dashboard_charts (dashboard_id, chart_id, tab_id, position, size, custom_width, custom_height)
                        VALUES (%s, %s, NULL, %s, %s, %s, %s)
                        ON CONFLICT (dashboard_id, chart_id, tab_id) DO UPDATE SET
                            position = EXCLUDED.position,
                            size = EXCLUDED.size,
                            custom_width = EXCLUDED.custom_width,
                            custom_height = EXCLUDED.custom_height
                    """, (dashboard_id, chart_id, chart_idx, chart_size, custom_width, custom_height))

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
        logging.error(f"Error updating dashboard metadata: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/dashboards/{dashboard_id}/charts/{chart_id}/dimensions")
async def update_chart_dimensions(dashboard_id: str, chart_id: str, request: Request):
    """Update custom dimensions (width/height) for a chart in a dashboard"""
    try:
        body = await request.json()
        custom_width = body.get('customWidth')
        custom_height = body.get('customHeight')

        # INPUT VALIDATION: Type and range checks
        if custom_width is not None:
            if not isinstance(custom_width, (int, float)):
                raise HTTPException(status_code=400, detail="customWidth must be a number")
            custom_width = int(custom_width)
            if custom_width < 250 or custom_width > 5000:
                raise HTTPException(status_code=400, detail="customWidth must be between 250 and 5000 pixels")

        if custom_height is not None:
            if not isinstance(custom_height, (int, float)):
                raise HTTPException(status_code=400, detail="customHeight must be a number")
            custom_height = int(custom_height)
            if custom_height < 200 or custom_height > 5000:
                raise HTTPException(status_code=400, detail="customHeight must be between 200 and 5000 pixels")

        logging.info(f"Updating chart {chart_id} dimensions in dashboard {dashboard_id}: {custom_width}x{custom_height}")

        with connection_manager.get_connection() as pg:
            # Check if the dashboard_chart relationship exists
            check_query = """
                SELECT id FROM dashboard_charts
                WHERE dashboard_id = %s AND chart_id = %s
            """
            existing = pg.execute(check_query, (dashboard_id, chart_id), fetch=True)

            if not existing or len(existing) == 0:
                raise HTTPException(status_code=404, detail=f"Chart {chart_id} not found in dashboard {dashboard_id}")

            # Update the custom dimensions in dashboard_charts table
            update_query = """
                UPDATE dashboard_charts
                SET custom_width = %s, custom_height = %s
                WHERE dashboard_id = %s AND chart_id = %s
            """
            pg.execute(update_query, (custom_width, custom_height, dashboard_id, chart_id))

            logging.info(f"Chart {chart_id} dimensions updated successfully")
            return {
                "success": True,
                "message": "Chart dimensions updated successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating chart dimensions: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Datasets API Routes
# ============================================================================

@app.get("/api/datasets")
async def get_datasets(
    request: Request,
    user: dict = Depends(require_datasets_read())
):
    """Get all datasets (requires view_datasets permission)"""
    return await datasets_api.get_all_datasets()


@app.get("/api/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    request: Request,
    user: dict = Depends(require_datasets_read())
):
    """Get a single dataset by ID (requires view_datasets permission)"""
    return await datasets_api.get_dataset_by_id(dataset_id)


@app.post("/api/datasets")
async def create_dataset_endpoint(
    request: Request,
    user: dict = Depends(require_datasets_write())
):
    """Create a new dataset (requires create_datasets permission)"""
    return await datasets_api.create_dataset(request)


@app.put("/api/datasets/{dataset_id}")
async def update_dataset_endpoint(
    dataset_id: str,
    request: Request,
    user: dict = Depends(require_datasets_write())
):
    """Update an existing dataset (requires edit_datasets permission)"""
    return await datasets_api.update_dataset(dataset_id, request)


@app.delete("/api/datasets/{dataset_id}")
async def delete_dataset_endpoint(
    dataset_id: str,
    request: Request,
    user: dict = Depends(require_datasets_write())
):
    """Delete a dataset (requires delete_datasets permission)"""
    return await datasets_api.delete_dataset(dataset_id)


@app.post("/api/datasets/preview")
async def preview_dataset_endpoint(
    request: Request,
    user: dict = Depends(require_datasets_read())
):
    """Preview data from a dataset (requires view_datasets permission)"""
    return await datasets_api.preview_dataset(request)


@app.post("/api/datasets/upload-csv")
async def upload_csv(
    request: Request,
    file: UploadFile = File(...),
    dataset_id: str = Form(None),
    dataset_name: str = Form(None),
    dataset_description: str = Form(None),
    preview_only: str = Form(None),
    user: dict = Depends(require_datasets_write())
):
    """Upload a CSV file and create a dataset (requires upload_datasets permission)"""
    from postgres import PostgresConnector

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
        logging.error(f"Error fetching columns: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
async def query_data(
    request: Request,
    user: dict = Depends(require_queries_execute())
):
    """Execute a query and return aggregated data for charting (requires execute_queries permission)"""
    try:
        from postgres import PostgresConnector
        import logging
        import pandas as pd

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

        def build_filter_clauses(filters, filter_expressions, available_columns):
            """Build WHERE clauses supporting SQL expressions for filters"""
            from psycopg2 import sql
            import re

            where_clauses = []
            params = []

            for field, value in filters.items():
                if not value:
                    continue

                # Check if there's an SQL expression for this filter
                if field in filter_expressions and filter_expressions[field]:
                    # Use the SQL expression instead of the raw field
                    expression = filter_expressions[field]

                    # Validate expression for safety
                    dangerous_patterns = [';', '--', '/*', '*/', 'DROP', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER', 'TRUNCATE', 'EXEC']
                    expr_upper = expression.upper()
                    for pattern in dangerous_patterns:
                        if pattern in expr_upper:
                            raise HTTPException(status_code=400, detail=f"Expression contains unsafe SQL pattern: {pattern}")

                    # Only allow safe characters
                    if not re.match(r'^[a-zA-Z0-9_\s\(\)\+\-\*\/\,\.\:\'\[\]]+$', expression):
                        raise HTTPException(status_code=400, detail="Expression contains invalid characters")

                    # Use parameterized query - expression goes in SQL, value as parameter
                    where_clauses.append(f"({expression}) = %s")
                    params.append(value)
                elif field in available_columns:
                    # Validate field name (must be valid SQL identifier)
                    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', field):
                        raise HTTPException(status_code=400, detail=f"Invalid field name: {field}")

                    # Use the field directly with parameterized value
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
                from psycopg2 import sql
                import re

                columns = body.get('columns', [])
                if not columns:
                    raise HTTPException(status_code=400, detail="Missing columns for table chart")

                # Validate each column name and check it exists
                for col in columns:
                    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', col):
                        raise HTTPException(status_code=400, detail=f"Invalid column name: {col}")
                    if col not in available_columns:
                        raise HTTPException(status_code=400, detail=f"Column not found in table: {col}")

                # Build WHERE clauses from filters using helper function
                where_clauses, params = build_filter_clauses(filters, filter_expressions, available_columns)
                where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

                # Build column selection safely with sql.Identifier
                column_identifiers = [sql.Identifier(col) for col in columns]
                column_names_sql = sql.SQL(', ').join(column_identifiers)

                # Build full query safely using psycopg2.sql.Composed
                query = sql.SQL("""
                    SELECT {columns}
                    FROM {schema}.{table}
                    {where_sql}
                    LIMIT 100
                """).format(
                    columns=column_names_sql,
                    schema=sql.Identifier(schema),
                    table=sql.Identifier(table),
                    where_sql=sql.SQL(where_sql)
                )

                # Execute composed SQL directly with cursor (psycopg2 handles Composed objects)
                from psycopg2.extras import RealDictCursor
                with pg.conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, tuple(params) if params else None)
                    result = cur.fetchall()
                    df = pd.DataFrame(result) if result else pd.DataFrame()

                # Convert DataFrame to list of dictionaries
                data = df.to_dict('records')

                return {
                    "columns": columns,
                    "data": data
                }

            # Handle metric type charts (single value)
            if chart_type == 'metric' and metric:
                from psycopg2 import sql
                import re

                # Validate metric column
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', metric):
                    raise HTTPException(status_code=400, detail=f"Invalid metric name: {metric}")
                if metric not in available_columns:
                    raise HTTPException(status_code=400, detail=f"Metric column not found: {metric}")

                # Validate aggregation function (whitelist)
                ALLOWED_AGGREGATIONS = ['SUM', 'AVG', 'COUNT', 'MIN', 'MAX', 'STDDEV', 'VARIANCE']
                agg_func = aggregation.upper()
                if agg_func not in ALLOWED_AGGREGATIONS:
                    raise HTTPException(status_code=400, detail=f"Invalid aggregation function: {aggregation}")

                # Build WHERE clauses from filters using helper function
                where_clauses, params = build_filter_clauses(filters, filter_expressions, available_columns)
                where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

                # Build query safely
                query = sql.SQL("""
                    SELECT {agg_func}({metric}) as value
                    FROM {schema}.{table}
                    {where_sql}
                """).format(
                    agg_func=sql.SQL(agg_func),
                    metric=sql.Identifier(metric),
                    schema=sql.Identifier(schema),
                    table=sql.Identifier(table),
                    where_sql=sql.SQL(where_sql)
                )

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
                from psycopg2 import sql
                import re

                if not x_axis:
                    raise HTTPException(status_code=400, detail="Missing x_axis for multi-metric chart")

                # Validate x_axis
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', x_axis):
                    raise HTTPException(status_code=400, detail=f"Invalid x_axis name: {x_axis}")
                if x_axis not in available_columns:
                    raise HTTPException(status_code=400, detail=f"x_axis column not found: {x_axis}")

                # Build WHERE clauses from filters using helper function
                filter_clauses, params = build_filter_clauses(filters, filter_expressions, available_columns)

                # Add x_axis IS NOT NULL - safely
                where_clauses = [f"{x_axis} IS NOT NULL"] + filter_clauses
                where_sql = "WHERE " + " AND ".join(where_clauses)

                # Build query with multiple aggregations - validate each metric
                ALLOWED_AGGREGATIONS = ['SUM', 'AVG', 'COUNT', 'MIN', 'MAX', 'STDDEV', 'VARIANCE']
                metric_sql_parts = []

                for metric in metrics:
                    field = metric.get('field')
                    agg = metric.get('aggregation', 'sum').upper()

                    # Validate field
                    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', field):
                        raise HTTPException(status_code=400, detail=f"Invalid metric field: {field}")
                    if field not in available_columns:
                        raise HTTPException(status_code=400, detail=f"Metric field not found: {field}")

                    # Validate aggregation
                    if agg not in ALLOWED_AGGREGATIONS:
                        raise HTTPException(status_code=400, detail=f"Invalid aggregation: {agg}")

                    # Build safe SQL part
                    metric_sql_parts.append(
                        sql.SQL("{agg}({field}) as {alias}").format(
                            agg=sql.SQL(agg),
                            field=sql.Identifier(field),
                            alias=sql.Identifier(field)
                        )
                    )

                # Build full query safely
                query = sql.SQL("""
                    SELECT
                        {x_axis} as label,
                        {metric_selects}
                    FROM {schema}.{table}
                    {where_sql}
                    GROUP BY {x_axis}
                    ORDER BY {x_axis}
                    LIMIT 50
                """).format(
                    x_axis=sql.Identifier(x_axis),
                    metric_selects=sql.SQL(', ').join(metric_sql_parts),
                    schema=sql.Identifier(schema),
                    table=sql.Identifier(table),
                    where_sql=sql.SQL(where_sql)
                )

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
        logging.error(f"Error listing tables: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/filter/values")
async def get_filter_values(request: Request):
    """Get distinct values for a filter field (supports SQL expressions)"""
    try:
        from connection_manager import connection_manager
        from psycopg2 import sql
        import logging
        import re

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

        # Validate schema name (must be valid SQL identifier)
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', schema):
            raise HTTPException(status_code=400, detail="Invalid schema name")

        # Validate table name (must be valid SQL identifier)
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
            raise HTTPException(status_code=400, detail="Invalid table name")

        # Get connection from connection manager
        with connection_manager.get_connection(connection_id) as pg:
            # Validate that table exists in schema
            table_check = pg.execute("""
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
            """, (schema, table), fetch=True)

            if not table_check:
                raise HTTPException(status_code=404, detail=f"Table {schema}.{table} not found")

            # Build query safely using psycopg2.sql for identifiers
            if expression:
                # For expressions, validate they don't contain dangerous patterns
                dangerous_patterns = [';', '--', '/*', '*/', 'xp_', 'sp_', 'DROP', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER', 'TRUNCATE', 'EXEC']
                expr_upper = expression.upper()
                for pattern in dangerous_patterns:
                    if pattern in expr_upper:
                        raise HTTPException(status_code=400, detail=f"Expression contains unsafe SQL pattern: {pattern}")

                # For safety, expressions should only use allowed functions and operators
                # Allow: CAST, EXTRACT, DATE, SUBSTRING, CONCAT, +, -, *, /, column names
                if not re.match(r'^[a-zA-Z0-9_\s\(\)\+\-\*\/\,\.\:\'\[\]]+$', expression):
                    raise HTTPException(status_code=400, detail="Expression contains invalid characters")

                # Use SQL literal for expression (still safer than f-string)
                query = sql.SQL("""
                    SELECT DISTINCT ({expression}) as value
                    FROM {schema}.{table}
                    WHERE ({expression}) IS NOT NULL
                    ORDER BY ({expression})
                    LIMIT 1000
                """).format(
                    expression=sql.SQL(expression),
                    schema=sql.Identifier(schema),
                    table=sql.Identifier(table)
                )
            else:
                # Validate field name (must be valid SQL identifier)
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', field):
                    raise HTTPException(status_code=400, detail="Invalid field name")

                # Use sql.Identifier for safe quoting
                query = sql.SQL("""
                    SELECT DISTINCT {field} as value
                    FROM {schema}.{table}
                    WHERE {field} IS NOT NULL
                    ORDER BY {field}
                    LIMIT 1000
                """).format(
                    field=sql.Identifier(field),
                    schema=sql.Identifier(schema),
                    table=sql.Identifier(table)
                )

            logging.info(f"Fetching filter values from {schema}.{table}")
            result = pg.execute(query, fetch=True)

            values = [row['value'] for row in result]
            logging.info(f"Found {len(values)} distinct values for {field or expression}")

            return {"values": values}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching filter values: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/query/execute")
async def execute_query(
    request: Request,
    user: dict = Depends(require_queries_execute())
):
    """Execute a SQL query and return results for SQL Query Lab (requires execute_queries permission)"""
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

        # Additional safety: block dangerous keywords (including in subqueries)
        dangerous_keywords = [
            'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE',
            'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'CALL',
            'xp_', 'sp_',  # SQL Server procedures
            ';--', '/*',  # Comment injection attempts
        ]
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                raise HTTPException(
                    status_code=400,
                    detail=f"Query contains forbidden keyword: {keyword}"
                )

        # Validate schema name to prevent SQL injection
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', schema):
            raise HTTPException(status_code=400, detail="Invalid schema name")

        logging.info(f"Executing query in connection={connection_id or 'default'}, schema={schema}")

        # Get connection from connection manager
        from connection_manager import connection_manager
        from psycopg2 import sql as psycopg_sql

        with connection_manager.get_connection(connection_id) as pg:
            # Set search path safely using parameterized query
            set_path_query = psycopg_sql.SQL("SET search_path TO {schema}, public").format(
                schema=psycopg_sql.Identifier(schema)
            )
            pg.execute(set_path_query)
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
        logging.error(f"Error creating view: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to create view: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "transformdash"}


@app.get("/api/status")
async def server_status():
    """Get comprehensive server status including scheduler and jobs"""
    import psutil
    import os
    from datetime import datetime

    try:
        # Get process info
        process = psutil.Process(os.getpid())

        # Get scheduler status
        scheduler = get_scheduler()
        active_jobs = scheduler.get_active_schedules() if scheduler else []

        # Get database connection status
        try:
            conn_status = {
                "transformdash": "connected" if connection_manager.get_connection('transformdash') else "disconnected",
                "app": "connected" if connection_manager.get_connection('app') else "disconnected"
            }
        except Exception:
            conn_status = {"error": "Unable to check connections"}

        return {
            "status": "healthy",
            "service": "transformdash",
            "timestamp": datetime.now().isoformat(),
            "process": {
                "pid": process.pid,
                "uptime_seconds": (datetime.now() - datetime.fromtimestamp(process.create_time())).total_seconds(),
                "memory_mb": round(process.memory_info().rss / (1024 * 1024), 2),
                "cpu_percent": process.cpu_percent(interval=0.1),
                "threads": process.num_threads()
            },
            "scheduler": {
                "active": scheduler is not None,
                "jobs_count": len(active_jobs),
                "jobs": active_jobs
            },
            "database": conn_status
        }
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@app.get("/api/jobs")
async def get_jobs():
    """Get all scheduled jobs and their status"""
    try:
        scheduler = get_scheduler()
        if not scheduler:
            return {"jobs": [], "message": "Scheduler not initialized"}

        jobs = scheduler.get_active_schedules()

        return {
            "jobs": jobs,
            "jobs_count": len(jobs)
        }
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        return {"error": str(e), "jobs": []}


@app.get("/api/jobs/{job_id}")
async def get_job_details(job_id: str):
    """Get details of a specific job"""
    try:
        scheduler = get_scheduler()
        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not available")

        # Get job from scheduler
        job = scheduler.scheduler.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        return {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
            "args": job.args,
            "kwargs": job.kwargs
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    """Pause a scheduled job"""
    try:
        scheduler = get_scheduler()
        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not available")

        # Extract schedule_id from job_id (format: "schedule_{id}")
        if job_id.startswith("schedule_"):
            schedule_id = int(job_id.replace("schedule_", ""))
            success = scheduler.pause_schedule(schedule_id)

            if success:
                return {"status": "paused", "job_id": job_id}
            else:
                raise HTTPException(status_code=500, detail="Failed to pause job")
        else:
            raise HTTPException(status_code=400, detail="Invalid job ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    """Resume a paused job"""
    try:
        scheduler = get_scheduler()
        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not available")

        if job_id.startswith("schedule_"):
            schedule_id = int(job_id.replace("schedule_", ""))
            success = scheduler.resume_schedule(schedule_id)

            if success:
                return {"status": "resumed", "job_id": job_id}
            else:
                raise HTTPException(status_code=500, detail="Failed to resume job")
        else:
            raise HTTPException(status_code=400, detail="Invalid job ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dashboard/{dashboard_id}/export")
async def export_dashboard_data(
    dashboard_id: str,
    request: Request,
    user: dict = Depends(require_queries_execute())
):
    """Export all dashboard data as CSV or Excel (requires execute_queries permission)"""
    try:
        from postgres import PostgresConnector
        from connection_manager import connection_manager
        import io
        from fastapi.responses import StreamingResponse

        body = await request.json()
        export_format = body.get('format', 'csv')  # csv or excel
        filters = body.get('filters', {})

        # Collect all data from all charts
        all_data = {}

        # Fetch charts for this dashboard from the database
        with connection_manager.get_connection() as viz_pg:
            charts_data = viz_pg.execute("""
                SELECT
                    c.id,
                    c.title,
                    c.type,
                    c.model,
                    c.connection_id,
                    c.x_axis,
                    c.y_axis,
                    c.aggregation,
                    c.columns,
                    c.category,
                    c.config
                FROM charts c
                INNER JOIN dashboard_charts dc ON c.id = dc.chart_id
                WHERE dc.dashboard_id = %s
                ORDER BY dc.position
            """, (dashboard_id,), fetch=True)

            if not charts_data:
                raise HTTPException(status_code=404, detail="No charts found for this dashboard")

        with PostgresConnector() as pg:
            for chart in charts_data:
                # Skip metric-only charts and advanced charts
                if chart.get('type') == 'metric' or chart.get('metrics') or chart.get('calculation'):
                    continue

                if not chart.get('model') or not chart.get('x_axis') or not chart.get('y_axis'):
                    continue

                # Build query with filters
                from psycopg2 import sql
                from psycopg2.extras import RealDictCursor
                import re

                model = chart['model']

                # Parse schema.table format (e.g., "raw.customers" or just "customers")
                if '.' in model:
                    schema, table = model.split('.', 1)
                else:
                    schema = 'public'  # Default schema
                    table = model

                # Validate identifier names (schema, table, columns)
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', schema):
                    continue  # Skip invalid schema
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
                    continue  # Skip invalid table

                x_axis = chart['x_axis']
                y_axis = chart['y_axis']
                agg_func = chart.get('aggregation', 'sum').upper()

                # Validate column names
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', x_axis):
                    continue
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', y_axis):
                    continue

                # Validate aggregation function (whitelist)
                ALLOWED_AGGREGATIONS = ['SUM', 'AVG', 'COUNT', 'MIN', 'MAX', 'STDDEV', 'VARIANCE']
                if agg_func not in ALLOWED_AGGREGATIONS:
                    continue

                # Apply filters from request
                where_clauses = []
                params = []
                if filters:
                    for field, value in filters.items():
                        # Validate filter field names
                        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', field):
                            continue
                        # Use sql.Identifier for safe field names
                        where_clauses.append(sql.SQL("{field} = %s").format(field=sql.Identifier(field)))
                        params.append(value)

                # Combine WHERE clauses with AND
                if where_clauses:
                    where_sql = sql.SQL("WHERE ") + sql.SQL(" AND ").join(where_clauses)
                else:
                    where_sql = sql.SQL("")

                # Build query safely using sql.SQL
                query = sql.SQL("""
                    SELECT
                        {x_axis} as label,
                        {agg_func}({y_axis}) as value
                    FROM {schema}.{table}
                    {where_sql}
                    GROUP BY {x_axis}
                    ORDER BY {x_axis}
                """).format(
                    x_axis=sql.Identifier(x_axis),
                    agg_func=sql.SQL(agg_func),
                    y_axis=sql.Identifier(y_axis),
                    schema=sql.Identifier(schema),
                    table=sql.Identifier(table),
                    where_sql=sql.SQL(where_sql)
                )

                # Execute with cursor to handle Composed SQL
                with pg.conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, tuple(params) if params else None)
                    result = cur.fetchall()
                    df = pd.DataFrame(result) if result else pd.DataFrame()

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
        import logging
        logging.error(f"Dashboard export error: {str(e)}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/charts/{chart_id}/export")
async def export_chart_data(
    chart_id: str,
    request: Request,
    user: dict = Depends(require_queries_execute())
):
    """Export individual chart data as CSV or Excel (requires execute_queries permission)"""
    try:
        from postgres import PostgresConnector
        from connection_manager import connection_manager
        import io
        import pandas as pd
        from fastapi.responses import StreamingResponse

        body = await request.json()
        export_format = body.get('format', 'csv')  # csv or excel
        filters = body.get('filters', {})

        # Fetch chart details from the database
        with connection_manager.get_connection() as viz_pg:
            chart_data = viz_pg.execute("""
                SELECT
                    c.id,
                    c.title,
                    c.type,
                    c.model,
                    c.connection_id,
                    c.x_axis,
                    c.y_axis,
                    c.aggregation,
                    c.columns,
                    c.category,
                    c.config
                FROM charts c
                WHERE c.id = %s
            """, (chart_id,), fetch=True)

            if not chart_data or len(chart_data) == 0:
                raise HTTPException(status_code=404, detail="Chart not found")

            chart = chart_data[0]

        # Query the chart data
        with PostgresConnector() as pg:
            from psycopg2 import sql
            from psycopg2.extras import RealDictCursor
            import re

            # Skip metric-only charts
            if chart.get('type') == 'metric':
                raise HTTPException(status_code=400, detail="Cannot export metric-only charts")

            if not chart.get('model'):
                raise HTTPException(status_code=400, detail="Chart has no data model")

            # Parse schema.table format
            model = chart['model']
            if '.' in model:
                schema, table = model.split('.', 1)
            else:
                schema = 'public'
                table = model

            # Validate schema and table names
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', schema):
                raise HTTPException(status_code=400, detail="Invalid schema name")
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
                raise HTTPException(status_code=400, detail="Invalid table name")

            # Handle table-type charts (columns specified)
            if chart.get('type') == 'table' and chart.get('columns'):
                columns = [col if isinstance(col, str) else col.get('name') for col in chart['columns']]

                # Validate all column names
                for col in columns:
                    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', col):
                        raise HTTPException(status_code=400, detail=f"Invalid column name: {col}")

                # Apply filters
                where_clauses = []
                params = []
                if filters:
                    for field, value in filters.items():
                        # Validate filter field names
                        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', field):
                            continue
                        # Use sql.Identifier for safe field names
                        where_clauses.append(sql.SQL("{field} = %s").format(field=sql.Identifier(field)))
                        params.append(value)

                # Combine WHERE clauses with AND
                if where_clauses:
                    where_sql = sql.SQL("WHERE ") + sql.SQL(" AND ").join(where_clauses)
                else:
                    where_sql = sql.SQL("")

                # Build safe query with sql.SQL
                column_identifiers = [sql.Identifier(col) for col in columns]
                columns_sql = sql.SQL(', ').join(column_identifiers)

                query = sql.SQL("""
                    SELECT {columns}
                    FROM {schema}.{table}
                    {where_sql}
                    LIMIT 10000
                """).format(
                    columns=columns_sql,
                    schema=sql.Identifier(schema),
                    table=sql.Identifier(table),
                    where_sql=sql.SQL(where_sql)
                )

                # Execute with cursor
                with pg.conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, tuple(params) if params else None)
                    result = cur.fetchall()
                    df = pd.DataFrame(result) if result else pd.DataFrame()

            # Handle aggregated charts (bar, line, pie, etc.)
            elif chart.get('x_axis') and chart.get('y_axis'):
                x_axis = chart['x_axis']
                y_axis = chart['y_axis']
                agg_func = chart.get('aggregation', 'sum').upper()

                # Validate column names
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', x_axis):
                    raise HTTPException(status_code=400, detail=f"Invalid x_axis name: {x_axis}")
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', y_axis):
                    raise HTTPException(status_code=400, detail=f"Invalid y_axis name: {y_axis}")

                # Validate aggregation function (whitelist)
                ALLOWED_AGGREGATIONS = ['SUM', 'AVG', 'COUNT', 'MIN', 'MAX', 'STDDEV', 'VARIANCE']
                if agg_func not in ALLOWED_AGGREGATIONS:
                    raise HTTPException(status_code=400, detail=f"Invalid aggregation function: {agg_func}")

                # Apply filters
                where_clauses = []
                params = []
                if filters:
                    for field, value in filters.items():
                        # Validate filter field names
                        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', field):
                            continue
                        # Use sql.Identifier for safe field names
                        where_clauses.append(sql.SQL("{field} = %s").format(field=sql.Identifier(field)))
                        params.append(value)

                # Combine WHERE clauses with AND
                if where_clauses:
                    where_sql = sql.SQL("WHERE ") + sql.SQL(" AND ").join(where_clauses)
                else:
                    where_sql = sql.SQL("")

                # Handle category (stacked charts)
                if chart.get('category'):
                    category = chart['category']

                    # Validate category name
                    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', category):
                        raise HTTPException(status_code=400, detail=f"Invalid category name: {category}")

                    query = sql.SQL("""
                        SELECT
                            {x_axis} as label,
                            {category} as category,
                            {agg_func}({y_axis}) as value
                        FROM {schema}.{table}
                        {where_sql}
                        GROUP BY {x_axis}, {category}
                        ORDER BY {x_axis}, {category}
                    """).format(
                        x_axis=sql.Identifier(x_axis),
                        category=sql.Identifier(category),
                        agg_func=sql.SQL(agg_func),
                        y_axis=sql.Identifier(y_axis),
                        schema=sql.Identifier(schema),
                        table=sql.Identifier(table),
                        where_sql=sql.SQL(where_sql)
                    )
                else:
                    query = sql.SQL("""
                        SELECT
                            {x_axis} as label,
                            {agg_func}({y_axis}) as value
                        FROM {schema}.{table}
                        {where_sql}
                        GROUP BY {x_axis}
                        ORDER BY {x_axis}
                    """).format(
                        x_axis=sql.Identifier(x_axis),
                        agg_func=sql.SQL(agg_func),
                        y_axis=sql.Identifier(y_axis),
                        schema=sql.Identifier(schema),
                        table=sql.Identifier(table),
                        where_sql=sql.SQL(where_sql)
                    )

                # Execute with cursor
                with pg.conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, tuple(params) if params else None)
                    result = cur.fetchall()
                    df = pd.DataFrame(result) if result else pd.DataFrame()
            else:
                raise HTTPException(status_code=400, detail="Chart configuration is incomplete")

        # Export as requested format
        chart_title = chart.get('title', chart_id)
        if export_format == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                safe_name = chart_title[:31]  # Excel sheet name limit
                df.to_excel(writer, sheet_name=safe_name, index=False)
            output.seek(0)

            return StreamingResponse(
                output,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment; filename="{chart_id}_data.xlsx"'}
            )
        else:  # CSV
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type='text/csv',
                headers={'Content-Disposition': f'attachment; filename="{chart_id}_data.csv"'}
            )

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Chart export error: {str(e)}")
        logging.error(f"Traceback: {traceback.format_exc()}")
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
        logging.error(f"Error downloading asset: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Authentication Endpoints
# =============================================================================

@app.post("/api/auth/login")
async def login(request: Request):
    """Login endpoint - authenticate user and return JWT token"""
    try:
        from auth import authenticate_user, create_access_token

        body = await request.json()
        username = body.get('username')
        password = body.get('password')

        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password required")

        # Authenticate user
        user = await authenticate_user(username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )

        # Create access token
        access_token = create_access_token(data={"sub": user['username']})

        # Return token in both body and cookie
        response = JSONResponse(content={
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "full_name": user.get('full_name'),
                "is_superuser": user['is_superuser']
            }
        })

        # Set cookie with security flags
        # secure=True only for production (HTTPS), False for local development
        is_production = os.getenv("DEMO_MODE") == "true" or os.getenv("ENV") == "production"
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=is_production,  # Only send over HTTPS in production
            max_age=480 * 60,  # 8 hours in seconds
            samesite="lax"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Login error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/logout")
async def logout():
    """Logout endpoint - clear authentication cookie"""
    from fastapi.responses import JSONResponse

    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie(key="access_token")
    return response


@app.get("/api/auth/me")
async def get_current_user_info(request: Request):
    """Get current authenticated user info"""
    try:
        from auth import get_current_user

        user = await get_current_user(request)
        return {
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "full_name": user.get('full_name'),
                "is_superuser": user['is_superuser'],
                "roles": user.get('roles', []),
                "permissions": user.get('permissions', [])
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting current user: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# User Management Endpoints
# =============================================================================

@app.get("/api/users")
async def get_users(
    request: Request,
    user: dict = Depends(require_users_read())
):
    """Get all users with their roles (requires view_users permission)"""
    try:
        from connection_manager import connection_manager

        with connection_manager.get_connection() as pg:
            users = pg.execute("""
                SELECT
                    u.id,
                    u.username,
                    u.email,
                    u.full_name,
                    u.is_active,
                    u.is_superuser,
                    u.created_at,
                    u.last_login,
                    COALESCE(
                        json_agg(
                            json_build_object('id', r.id, 'name', r.name)
                        ) FILTER (WHERE r.id IS NOT NULL),
                        '[]'::json
                    ) as roles
                FROM users u
                LEFT JOIN user_roles ur ON u.id = ur.user_id
                LEFT JOIN roles r ON ur.role_id = r.id
                GROUP BY u.id, u.username, u.email, u.full_name, u.is_active, u.is_superuser, u.created_at, u.last_login
                ORDER BY u.created_at DESC
            """, fetch=True)

            return {"users": [dict(u) for u in users]}

    except Exception as e:
        logging.error(f"Error fetching users: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/users")
async def create_user(
    request: Request,
    user: dict = Depends(require_users_manage())
):
    """Create a new user (requires manage_users permission)"""
    try:
        from connection_manager import connection_manager
        import bcrypt

        body = await request.json()
        username = body.get('username')
        email = body.get('email')
        password = body.get('password')
        full_name = body.get('full_name', '')
        role_ids = body.get('role_ids', [])

        if not username or not email or not password:
            raise HTTPException(status_code=400, detail="Username, email, and password are required")

        # Hash password (truncate to 72 bytes for bcrypt limit)
        password = password[:72]
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        with connection_manager.get_connection() as pg:
            # Create user
            user_id = pg.execute("""
                INSERT INTO users (username, email, password_hash, full_name, is_active, is_superuser)
                VALUES (%s, %s, %s, %s, TRUE, FALSE)
                RETURNING id
            """, (username, email, password_hash, full_name), fetch=True)[0]['id']

            # Assign roles
            for role_id in role_ids:
                pg.execute("""
                    INSERT INTO user_roles (user_id, role_id)
                    VALUES (%s, %s)
                """, (user_id, role_id))

            return {"message": "User created successfully", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating user: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/users/{user_id}")
async def update_user(
    user_id: int,
    request: Request,
    user: dict = Depends(require_users_manage())
):
    """Update user details"""
    try:
        from connection_manager import connection_manager
        import bcrypt

        body = await request.json()
        email = body.get('email')
        full_name = body.get('full_name')
        is_active = body.get('is_active')
        is_superuser = body.get('is_superuser')
        password = body.get('password')  # Optional - only if changing password
        role_ids = body.get('role_ids')

        with connection_manager.get_connection() as pg:
            # Update basic info
            update_fields = []
            params = []

            if email is not None:
                update_fields.append("email = %s")
                params.append(email)
            if full_name is not None:
                update_fields.append("full_name = %s")
                params.append(full_name)
            if is_active is not None:
                update_fields.append("is_active = %s")
                params.append(is_active)
            if is_superuser is not None:
                update_fields.append("is_superuser = %s")
                params.append(is_superuser)
            if password:
                # Truncate to 72 bytes for bcrypt limit
                password = password[:72]
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                update_fields.append("password_hash = %s")
                params.append(password_hash)

            if update_fields:
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                params.append(user_id)
                pg.execute(f"""
                    UPDATE users
                    SET {', '.join(update_fields)}
                    WHERE id = %s
                """, tuple(params))

            # Update roles if provided
            if role_ids is not None:
                # Remove existing roles
                pg.execute("DELETE FROM user_roles WHERE user_id = %s", (user_id,))

                # Add new roles
                for role_id in role_ids:
                    pg.execute("""
                        INSERT INTO user_roles (user_id, role_id)
                        VALUES (%s, %s)
                    """, (user_id, role_id))

            return {"message": "User updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating user: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/users/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    user: dict = Depends(require_users_manage())
):
    """Delete a user (requires manage_users permission)"""
    try:
        from connection_manager import connection_manager

        with connection_manager.get_connection() as pg:
            pg.execute("DELETE FROM users WHERE id = %s", (user_id,))
            return {"message": "User deleted successfully"}

    except Exception as e:
        logging.error(f"Error deleting user: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/roles")
async def get_roles(
    request: Request,
    user: dict = Depends(require_users_read())
):
    """Get all roles with their permissions (requires view_users permission)"""
    try:
        from connection_manager import connection_manager

        with connection_manager.get_connection() as pg:
            roles = pg.execute("""
                SELECT
                    r.id,
                    r.name,
                    r.description,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'id', p.id,
                                'name', p.name,
                                'resource', p.resource,
                                'action', p.action,
                                'description', p.description
                            )
                        ) FILTER (WHERE p.id IS NOT NULL),
                        '[]'::json
                    ) as permissions
                FROM roles r
                LEFT JOIN role_permissions rp ON r.id = rp.role_id
                LEFT JOIN permissions p ON rp.permission_id = p.id
                GROUP BY r.id, r.name, r.description
                ORDER BY r.name
            """, fetch=True)

            return {"roles": [dict(r) for r in roles]}

    except Exception as e:
        logging.error(f"Error fetching roles: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/permissions")
async def get_permissions():
    """Get all available permissions"""
    try:
        from connection_manager import connection_manager

        with connection_manager.get_connection() as pg:
            permissions = pg.execute("""
                SELECT id, name, resource, action, description
                FROM permissions
                ORDER BY resource, action
            """, fetch=True)

            return {"permissions": [dict(p) for p in permissions]}

    except Exception as e:
        logging.error(f"Error fetching permissions: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/roles")
async def create_role(request: Request):
    """Create a new role"""
    try:
        from connection_manager import connection_manager

        body = await request.json()
        name = body.get('name')
        description = body.get('description', '')
        permission_ids = body.get('permission_ids', [])

        if not name:
            raise HTTPException(status_code=400, detail="Role name is required")

        with connection_manager.get_connection() as pg:
            # Create role
            role_id = pg.execute("""
                INSERT INTO roles (name, description)
                VALUES (%s, %s)
                RETURNING id
            """, (name, description), fetch=True)[0]['id']

            # Assign permissions
            for permission_id in permission_ids:
                pg.execute("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (%s, %s)
                """, (role_id, permission_id))

            return {"message": "Role created successfully", "role_id": role_id}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating role: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/roles/{role_id}")
async def update_role(role_id: int, request: Request):
    """Update role details and permissions"""
    try:
        from connection_manager import connection_manager

        body = await request.json()
        name = body.get('name')
        description = body.get('description')
        permission_ids = body.get('permission_ids')

        with connection_manager.get_connection() as pg:
            # Update basic info
            update_fields = []
            params = []

            if name is not None:
                update_fields.append("name = %s")
                params.append(name)
            if description is not None:
                update_fields.append("description = %s")
                params.append(description)

            if update_fields:
                params.append(role_id)
                pg.execute(f"""
                    UPDATE roles
                    SET {', '.join(update_fields)}
                    WHERE id = %s
                """, tuple(params))

            # Update permissions if provided
            if permission_ids is not None:
                # Remove existing permissions
                pg.execute("DELETE FROM role_permissions WHERE role_id = %s", (role_id,))

                # Add new permissions
                for permission_id in permission_ids:
                    pg.execute("""
                        INSERT INTO role_permissions (role_id, permission_id)
                        VALUES (%s, %s)
                    """, (role_id, permission_id))

            return {"message": "Role updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating role: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/roles/{role_id}")
async def delete_role(role_id: int):
    """Delete a role"""
    try:
        from connection_manager import connection_manager

        with connection_manager.get_connection() as pg:
            # Check if role is in use
            users_with_role = pg.execute("""
                SELECT COUNT(*) as count
                FROM user_roles
                WHERE role_id = %s
            """, (role_id,), fetch=True)[0]['count']

            if users_with_role > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot delete role: {users_with_role} user(s) still have this role"
                )

            pg.execute("DELETE FROM roles WHERE id = %s", (role_id,))
            return {"message": "Role deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting role: {e}\n{traceback.format_exc()}")
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
