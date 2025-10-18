"""
TransformDash Web UI - FastAPI Application
Interactive lineage graphs and dashboard
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from transformations.dbt_loader import DBTModelLoader
from transformations import DAG

app = FastAPI(title="TransformDash", description="Hybrid Data Transformation Platform")

# Global state
models_dir = Path(__file__).parent.parent / "models"
loader = DBTModelLoader(models_dir=str(models_dir))


@app.get("/")
async def root():
    """Serve the main dashboard HTML"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TransformDash - Data Transformation Platform</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #666;
            font-size: 1.1em;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .stat-label {
            color: #888;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .stat-value {
            color: #333;
            font-size: 2em;
            font-weight: bold;
            margin-top: 5px;
        }

        .main-content {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 20px;
        }

        .panel {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }

        .model-item {
            padding: 12px;
            border-left: 4px solid #667eea;
            background: #f8f9fa;
            margin-bottom: 10px;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .model-item:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }

        .model-name {
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }

        .model-meta {
            font-size: 0.85em;
            color: #666;
        }

        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: bold;
            margin-right: 5px;
        }

        .badge-bronze {
            background: #cd7f32;
            color: white;
        }

        .badge-silver {
            background: #c0c0c0;
            color: #333;
        }

        .badge-gold {
            background: #ffd700;
            color: #333;
        }

        .badge-sql {
            background: #0078d4;
            color: white;
        }

        #lineage-graph {
            min-height: 600px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background: #fafafa;
        }

        .node {
            cursor: pointer;
        }

        .node rect {
            fill: #667eea;
            stroke: #5568d3;
            stroke-width: 2px;
            rx: 8px;
        }

        .node.bronze rect {
            fill: #cd7f32;
            stroke: #b06727;
        }

        .node.silver rect {
            fill: #c0c0c0;
            stroke: #a8a8a8;
        }

        .node.gold rect {
            fill: #ffd700;
            stroke: #e6c200;
        }

        .node text {
            fill: white;
            font-size: 12px;
            font-weight: bold;
            text-anchor: middle;
        }

        .node.gold text, .node.silver text {
            fill: #333;
        }

        .link {
            fill: none;
            stroke: #999;
            stroke-width: 2px;
            marker-end: url(#arrowhead);
        }

        .link:hover {
            stroke: #667eea;
            stroke-width: 3px;
        }

        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1em;
            font-weight: bold;
            transition: all 0.3s;
        }

        .refresh-btn:hover {
            background: #5568d3;
            transform: scale(1.05);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 TransformDash</h1>
            <p class="subtitle">Hybrid Data Transformation & Dashboard Platform</p>
        </header>

        <div class="stats" id="stats">
            <div class="stat-card">
                <div class="stat-label">Total Models</div>
                <div class="stat-value" id="total-models">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Bronze Layer</div>
                <div class="stat-value" id="bronze-count">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Silver Layer</div>
                <div class="stat-value" id="silver-count">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Gold Layer</div>
                <div class="stat-value" id="gold-count">-</div>
            </div>
        </div>

        <div class="main-content">
            <div class="panel">
                <h2>📋 Models</h2>
                <button class="refresh-btn" onclick="loadModels()">🔄 Refresh</button>
                <div id="models-list" style="margin-top: 20px;"></div>
            </div>

            <div class="panel">
                <h2>🔗 Data Lineage</h2>
                <div id="lineage-graph"></div>
            </div>
        </div>
    </div>

    <script>
        let modelsData = [];

        async function loadModels() {
            try {
                const response = await fetch('/api/models');
                modelsData = await response.json();

                // Update stats
                document.getElementById('total-models').textContent = modelsData.length;
                document.getElementById('bronze-count').textContent =
                    modelsData.filter(m => m.name.startsWith('stg_')).length;
                document.getElementById('silver-count').textContent =
                    modelsData.filter(m => m.name.startsWith('int_')).length;
                document.getElementById('gold-count').textContent =
                    modelsData.filter(m => m.name.startsWith('fct_') || m.name.startsWith('dim_')).length;

                // Display models list
                const modelsList = document.getElementById('models-list');
                modelsList.innerHTML = modelsData.map(model => {
                    const layer = getModelLayer(model.name);
                    const badge = `<span class="badge badge-${layer}">${layer.toUpperCase()}</span>`;
                    const typeBadge = `<span class="badge badge-sql">${model.type.toUpperCase()}</span>`;

                    return `
                        <div class="model-item" onclick="highlightModel('${model.name}')">
                            <div class="model-name">${model.name}</div>
                            <div class="model-meta">
                                ${badge}
                                ${typeBadge}
                                ${model.depends_on.length > 0 ?
                                    `<br>Depends on: ${model.depends_on.join(', ')}` :
                                    '<br>No dependencies'}
                            </div>
                        </div>
                    `;
                }).join('');

                // Draw lineage graph
                drawLineage(modelsData);

            } catch (error) {
                console.error('Error loading models:', error);
                alert('Failed to load models');
            }
        }

        function getModelLayer(name) {
            if (name.startsWith('stg_')) return 'bronze';
            if (name.startsWith('int_')) return 'silver';
            if (name.startsWith('fct_') || name.startsWith('dim_')) return 'gold';
            return 'unknown';
        }

        function drawLineage(models) {
            const container = document.getElementById('lineage-graph');
            container.innerHTML = '';

            const width = container.clientWidth;
            const height = 600;

            const svg = d3.select('#lineage-graph')
                .append('svg')
                .attr('width', width)
                .attr('height', height);

            // Define arrowhead marker
            svg.append('defs').append('marker')
                .attr('id', 'arrowhead')
                .attr('markerWidth', 10)
                .attr('markerHeight', 10)
                .attr('refX', 9)
                .attr('refY', 3)
                .attr('orient', 'auto')
                .append('polygon')
                .attr('points', '0 0, 10 3, 0 6')
                .attr('fill', '#999');

            // Create nodes and links
            const nodes = models.map(m => ({
                id: m.name,
                layer: getModelLayer(m.name),
                type: m.type
            }));

            const links = [];
            models.forEach(model => {
                model.depends_on.forEach(dep => {
                    links.push({
                        source: dep,
                        target: model.name
                    });
                });
            });

            // Layout nodes by layer
            const layers = { bronze: [], silver: [], gold: [] };
            nodes.forEach(node => {
                if (layers[node.layer]) {
                    layers[node.layer].push(node);
                }
            });

            const layerX = { bronze: width * 0.2, silver: width * 0.5, gold: width * 0.8 };

            Object.keys(layers).forEach(layer => {
                const layerNodes = layers[layer];
                const spacing = height / (layerNodes.length + 1);
                layerNodes.forEach((node, i) => {
                    node.x = layerX[layer];
                    node.y = spacing * (i + 1);
                });
            });

            // Draw links
            svg.selectAll('.link')
                .data(links)
                .enter()
                .append('path')
                .attr('class', 'link')
                .attr('d', d => {
                    const source = nodes.find(n => n.id === d.source);
                    const target = nodes.find(n => n.id === d.target);
                    if (!source || !target) return '';

                    return `M ${source.x + 60} ${source.y}
                            C ${(source.x + target.x) / 2} ${source.y},
                              ${(source.x + target.x) / 2} ${target.y},
                              ${target.x - 60} ${target.y}`;
                });

            // Draw nodes
            const nodeGroups = svg.selectAll('.node')
                .data(nodes)
                .enter()
                .append('g')
                .attr('class', d => `node ${d.layer}`)
                .attr('transform', d => `translate(${d.x - 60}, ${d.y - 20})`);

            nodeGroups.append('rect')
                .attr('width', 120)
                .attr('height', 40);

            nodeGroups.append('text')
                .attr('x', 60)
                .attr('y', 25)
                .text(d => d.id.length > 12 ? d.id.substring(0, 10) + '...' : d.id)
                .append('title')
                .text(d => d.id);
        }

        function highlightModel(modelName) {
            console.log('Highlighting model:', modelName);
            // Future: highlight in graph
        }

        // Load on page load
        loadModels();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


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
