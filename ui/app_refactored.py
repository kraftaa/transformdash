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


@app.get("/modern", response_class=HTMLResponse)
async def modern_dashboard(request: Request):
    """Serve the modern UI dashboard (work in progress)"""
    return templates.TemplateResponse("index_modern.html", {"request": request})


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


@app.post("/api/charts/save")
async def save_chart(request: Request):
    """Save a chart configuration to dashboards.yml"""
    try:
        import yaml
        import logging

        # Parse request body
        body = await request.json()
        logging.info(f"Received chart save request: {body}")

        dashboards_file = models_dir / "dashboards.yml"
        logging.info(f"Dashboards file path: {dashboards_file}")

        # Get chart config from request
        chart_config = {
            "id": body.get("id"),
            "title": body.get("title"),
            "type": body.get("type"),
            "model": body.get("model"),
            "x_axis": body.get("x_axis"),
            "y_axis": body.get("y_axis"),
            "aggregation": body.get("aggregation", "sum")
        }

        logging.info(f"Chart config: {chart_config}")

        # Load existing dashboards or create new structure
        if dashboards_file.exists():
            with open(dashboards_file, 'r') as f:
                data = yaml.safe_load(f) or {}
            logging.info(f"Loaded existing dashboards: {len(data.get('dashboards', []))} dashboards")
        else:
            data = {}
            logging.info("No existing dashboards file, creating new")

        if 'dashboards' not in data:
            data['dashboards'] = []

        # Find or create the "Custom Charts" dashboard
        custom_dashboard = None
        for dashboard in data['dashboards']:
            if dashboard.get('id') == 'custom_charts':
                custom_dashboard = dashboard
                break

        if not custom_dashboard:
            custom_dashboard = {
                'id': 'custom_charts',
                'name': 'Custom Charts',
                'description': 'User-created charts',
                'charts': []
            }
            data['dashboards'].append(custom_dashboard)
            logging.info("Created new Custom Charts dashboard")
        else:
            logging.info("Found existing Custom Charts dashboard")

        # Add chart to dashboard
        if 'charts' not in custom_dashboard:
            custom_dashboard['charts'] = []

        # Check if chart with same ID exists and update it
        chart_exists = False
        for i, chart in enumerate(custom_dashboard['charts']):
            if chart.get('id') == chart_config['id']:
                custom_dashboard['charts'][i] = chart_config
                chart_exists = True
                logging.info(f"Updated existing chart: {chart_config['id']}")
                break

        if not chart_exists:
            custom_dashboard['charts'].append(chart_config)
            logging.info(f"Added new chart: {chart_config['id']}")

        # Save back to file
        with open(dashboards_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        logging.info(f"Successfully saved chart to {dashboards_file}")

        return {
            "success": True,
            "message": "Chart saved successfully!",
            "dashboard_id": "custom_charts",
            "chart_id": chart_config['id']
        }
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        logging.error(f"Error saving chart: {error_detail}")
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
        filters = request.get('filters', {})

        if not all([table, x_axis, y_axis]):
            raise HTTPException(status_code=400, detail="Missing required parameters")

        with PostgresConnector() as pg:
            # First, get available columns for this table
            col_query = """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
            """
            col_result = pg.execute(col_query, (table,), fetch=True)
            available_columns = {row['column_name'] for row in col_result}

            # Build WHERE clauses from filters - only use filters that exist in this table
            where_clauses = [f"{x_axis} IS NOT NULL"]
            params = []

            if filters:
                for field, value in filters.items():
                    if value and field in available_columns:  # Check if column exists
                        where_clauses.append(f"{field} = %s")
                        params.append(value)

            where_sql = "WHERE " + " AND ".join(where_clauses)

            # Build aggregation query
            agg_func = aggregation.upper()
            query = f"""
                SELECT
                    {x_axis} as label,
                    {agg_func}({y_axis}) as value
                FROM public.{table}
                {where_sql}
                GROUP BY {x_axis}
                ORDER BY {x_axis}
                LIMIT 50
            """

            df = pg.query_to_dataframe(query, tuple(params) if params else None)

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


@app.post("/api/dashboard/{dashboard_id}/export")
async def export_dashboard_data(dashboard_id: str, request: dict):
    """Export all dashboard data as CSV or Excel"""
    try:
        from postgres import PostgresConnector
        import yaml
        import io
        from fastapi.responses import StreamingResponse

        dashboards_file = models_dir / "dashboards.yml"
        with open(dashboards_file, 'r') as f:
            data = yaml.safe_load(f)

        dashboard = next((d for d in data.get('dashboards', []) if d['id'] == dashboard_id), None)
        if not dashboard:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        export_format = request.get('format', 'csv')  # csv or excel
        filters = request.get('filters', {})

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
                    FROM public.{table}
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


if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting TransformDash Web UI...")
    print("📊 Dashboard: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
