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

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from transformations.dbt_loader import DBTModelLoader
from transformations import DAG
from orchestration.history import RunHistory

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
    return templates.TemplateResponse("index.html", {"request": request})


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
    """Get the SQL code for a specific model"""
    try:
        models = loader.load_all_models()
        model = next((m for m in models if m.name == model_name), None)

        if not model:
            raise HTTPException(status_code=404, detail=f"Model {model_name} not found")

        return {
            "name": model.name,
            "code": model.sql_query,
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
    """Get dashboard configurations with charts from dashboards.yml"""
    try:
        import yaml
        dashboards_file = models_dir / "dashboards.yml"

        if not dashboards_file.exists():
            return {"dashboards": []}

        with open(dashboards_file, 'r') as f:
            data = yaml.safe_load(f)

        return {"dashboards": data.get('dashboards', [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tables/{table_name}/columns")
async def get_table_columns(table_name: str):
    """Get columns for a specific table"""
    try:
        from postgres import PostgresConnector
        with PostgresConnector() as pg:
            query = """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = %s
                ORDER BY ordinal_position
            """
            result = pg.execute(query, (table_name,), fetch=True)
            columns = [{"name": row['column_name'], "type": row['data_type']} for row in result]
            return {"columns": columns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
async def query_data(request: dict):
    """Execute a query and return aggregated data for charting"""
    try:
        from postgres import PostgresConnector

        table = request.get('table')
        x_axis = request.get('x_axis')
        y_axis = request.get('y_axis')
        aggregation = request.get('aggregation', 'sum')

        if not all([table, x_axis, y_axis]):
            raise HTTPException(status_code=400, detail="Missing required parameters")

        # Build aggregation query
        agg_func = aggregation.upper()
        query = f"""
            SELECT
                {x_axis} as label,
                {agg_func}({y_axis}) as value
            FROM public.{table}
            WHERE {x_axis} IS NOT NULL
            GROUP BY {x_axis}
            ORDER BY {x_axis}
            LIMIT 50
        """

        with PostgresConnector() as pg:
            df = pg.query_to_dataframe(query)

            # Convert to chart-friendly format
            labels = df['label'].astype(str).tolist()
            values = df['value'].tolist()

            return {
                "labels": labels,
                "values": values
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "transformdash"}


if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting TransformDash Web UI...")
    print("📊 Dashboard: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
