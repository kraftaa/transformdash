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

# Initialize run history
sys.path.append(str(Path(__file__).parent.parent))
from orchestration.history import RunHistory
run_history = RunHistory()


@app.get("/")
async def root():
    """Serve the main dashboard HTML"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>✨ TransformDash</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>✨</text></svg>">
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
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
            display: block;
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

        .run-btn {
            background: #10b981;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1em;
            font-weight: bold;
            transition: all 0.3s;
            margin-left: 10px;
        }

        .run-btn:hover {
            background: #059669;
            transform: scale(1.05);
        }

        .run-btn:disabled {
            background: #9ca3af;
            cursor: not-allowed;
            transform: none;
        }

        .execution-status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 8px;
            display: none;
        }

        .execution-status.success {
            background: #d1fae5;
            border-left: 4px solid #10b981;
            display: block;
        }

        .execution-status.error {
            background: #fee2e2;
            border-left: 4px solid #ef4444;
            display: block;
        }

        .execution-status.running {
            background: #dbeafe;
            border-left: 4px solid #3b82f6;
            display: block;
        }

        /* Modal styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }

        .modal-content {
            background-color: white;
            margin: 50px auto;
            padding: 0;
            border-radius: 12px;
            width: 90%;
            max-width: 900px;
            max-height: 80vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }

        .modal-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .modal-header h2 {
            margin: 0;
            color: white;
            border: none;
            padding: 0;
        }

        .close {
            color: white;
            font-size: 32px;
            font-weight: bold;
            cursor: pointer;
            line-height: 1;
        }

        .close:hover {
            opacity: 0.8;
        }

        .modal-body {
            padding: 30px;
            overflow-y: auto;
            flex: 1;
        }

        .code-block {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 14px;
            line-height: 1.6;
        }

        .model-meta-info {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .model-meta-info strong {
            color: #667eea;
        }

        /* Tabs */
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }

        .tab {
            padding: 12px 24px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 1em;
            font-weight: 500;
            color: #666;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
        }

        .tab:hover {
            color: #667eea;
        }

        .tab.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .run-item {
            padding: 15px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .run-item:hover {
            border-color: #667eea;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
        }

        .run-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .run-id {
            font-weight: bold;
            color: #333;
        }

        .run-time {
            color: #888;
            font-size: 0.9em;
        }

        .run-stats {
            display: flex;
            gap: 15px;
            font-size: 0.9em;
        }

        .stat-success {
            color: #10b981;
        }

        .stat-failure {
            color: #ef4444;
        }

        .log-viewer {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 13px;
            line-height: 1.6;
            max-height: 500px;
            overflow-y: auto;
            white-space: pre-wrap;
        }

        .log-entry {
            margin-bottom: 4px;
        }

        .log-level-INFO {
            color: #4fc3f7;
        }

        .log-level-SUCCESS {
            color: #66bb6a;
        }

        .log-level-ERROR {
            color: #ef5350;
        }

        .log-level-WARNING {
            color: #ffa726;
        }

        .dashboard-card {
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 12px;
            transition: all 0.3s;
            cursor: pointer;
            max-height: 80px;
            overflow: hidden;
        }

        .dashboard-card.expanded {
            max-height: none;
            overflow: visible;
        }

        .dashboard-card:hover {
            border-color: #667eea;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
        }

        .dashboard-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .dashboard-left {
            display: flex;
            align-items: center;
            gap: 12px;
            flex: 1;
        }

        .dashboard-name {
            font-size: 1.1em;
            font-weight: bold;
            color: #333;
        }

        .dashboard-id {
            background: #f3f4f6;
            color: #6b7280;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            font-family: monospace;
        }

        .dashboard-type {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }

        .type-dashboard {
            background: #dbeafe;
            color: #1e40af;
        }

        .type-report {
            background: #dcfce7;
            color: #15803d;
        }

        .dashboard-summary {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .dashboard-details {
            display: none;
            padding-top: 10px;
            border-top: 1px solid #e5e7eb;
            margin-top: 10px;
        }

        .dashboard-card.expanded .dashboard-details {
            display: block;
        }

        .dashboard-card.expanded .dashboard-summary {
            white-space: normal;
        }

        .dashboard-description {
            color: #666;
            margin-bottom: 15px;
            line-height: 1.6;
        }

        .dashboard-models {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 10px;
        }

        .model-tag {
            background: #f3f4f6;
            border: 1px solid #d1d5db;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.9em;
            color: #374151;
            cursor: pointer;
        }

        .model-tag:hover {
            background: #e5e7eb;
        }

        .dashboard-owner {
            color: #888;
            font-size: 0.9em;
        }

        .expand-indicator {
            font-size: 0.8em;
            color: #9ca3af;
            transition: transform 0.3s;
        }

        .dashboard-card.expanded .expand-indicator {
            transform: rotate(180deg);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>✨ TransformDash</h1>
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

        <div class="panel" style="grid-column: 1 / -1;">
            <div class="tabs">
                <button class="tab active" onclick="switchTab('models')">📋 Models</button>
                <button class="tab" onclick="switchTab('runs')">📊 Runs</button>
                <button class="tab" onclick="switchTab('lineage')">🔗 Lineage</button>
                <button class="tab" onclick="switchTab('dashboards')">✨ Dashboards</button>
                <button class="tab" onclick="switchTab('charts')">📈 Charts</button>
            </div>

            <!-- Models Tab -->
            <div id="models-tab" class="tab-content active">
                <div>
                    <button class="refresh-btn" onclick="loadModels()">🔄 Refresh</button>
                    <button class="run-btn" id="runBtn" onclick="runTransformations()">▶️ Run Transformations</button>
                </div>
                <div id="execution-status" class="execution-status"></div>
                <div id="models-list" style="margin-top: 20px;"></div>
            </div>

            <!-- Runs Tab -->
            <div id="runs-tab" class="tab-content">
                <div>
                    <button class="refresh-btn" onclick="loadRuns()">🔄 Refresh Runs</button>
                </div>
                <div id="runs-list" style="margin-top: 20px;"></div>
            </div>

            <!-- Lineage Tab -->
            <div id="lineage-tab" class="tab-content">
                <div id="lineage-graph" style="min-height: 600px;"></div>
            </div>

            <!-- Dashboards Tab -->
            <div id="dashboards-tab" class="tab-content">
                <div id="dashboards-list"></div>
            </div>

            <!-- Charts Tab -->
            <div id="charts-tab" class="tab-content">
                <div style="display: grid; grid-template-columns: 350px 1fr; gap: 20px; height: 600px;">
                    <!-- Chart Builder Panel -->
                    <div style="background: white; padding: 20px; border-radius: 12px; overflow-y: auto;">
                        <h3 style="margin-bottom: 15px;">📈 Chart Builder</h3>

                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">Chart Title</label>
                            <input type="text" id="chartTitle" placeholder="My Chart"
                                   style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 6px;">
                        </div>

                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">Data Source</label>
                            <select id="chartTable" onchange="loadTableColumns()"
                                    style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 6px;">
                                <option value="">Select table...</option>
                                <option value="fct_orders">fct_orders (Gold Layer)</option>
                                <option value="int_customer_orders">int_customer_orders (Silver)</option>
                                <option value="stg_customers">stg_customers (Bronze)</option>
                                <option value="stg_orders">stg_orders (Bronze)</option>
                            </select>
                        </div>

                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">Chart Type</label>
                            <select id="chartType"
                                    style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 6px;">
                                <option value="bar">📊 Bar Chart</option>
                                <option value="line">📈 Line Chart</option>
                                <option value="pie">🥧 Pie Chart</option>
                                <option value="doughnut">🍩 Doughnut Chart</option>
                            </select>
                        </div>

                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">X-Axis (Labels)</label>
                            <select id="chartXAxis"
                                    style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 6px;">
                                <option value="">Select column...</option>
                            </select>
                        </div>

                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">Y-Axis (Values)</label>
                            <select id="chartYAxis"
                                    style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 6px;">
                                <option value="">Select column...</option>
                            </select>
                        </div>

                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">Aggregation</label>
                            <select id="chartAggregation"
                                    style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 6px;">
                                <option value="sum">SUM</option>
                                <option value="avg">AVG</option>
                                <option value="count">COUNT</option>
                                <option value="min">MIN</option>
                                <option value="max">MAX</option>
                            </select>
                        </div>

                        <button onclick="createChart()"
                                style="width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 8px; font-size: 1em; cursor: pointer; font-weight: bold;">
                            ✨ Create Chart
                        </button>

                        <div id="chartError" style="margin-top: 15px; padding: 10px; background: #fee; border-radius: 6px; color: #c00; display: none;"></div>
                    </div>

                    <!-- Chart Preview Panel -->
                    <div style="background: white; padding: 20px; border-radius: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3>Preview</h3>
                            <button onclick="saveChart()" id="saveChartBtn" disabled
                                    style="padding: 8px 16px; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer;">
                                💾 Save Chart
                            </button>
                        </div>
                        <canvas id="chartCanvas" style="max-height: 500px;"></canvas>
                        <div id="chartPlaceholder" style="display: flex; align-items: center; justify-content: center; height: 400px; color: #999;">
                            Select options and click "Create Chart" to see preview
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Code Viewer Modal -->
    <div id="codeModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalTitle">Model Code</h2>
                <span class="close" onclick="closeModal('codeModal')">&times;</span>
            </div>
            <div class="modal-body">
                <div id="modalBody"></div>
            </div>
        </div>
    </div>

    <!-- Logs Viewer Modal -->
    <div id="logsModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="logsModalTitle">Run Logs</h2>
                <span class="close" onclick="closeModal('logsModal')">&times;</span>
            </div>
            <div class="modal-body">
                <div id="logsModalBody"></div>
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

        async function highlightModel(modelName) {
            try {
                const response = await fetch(`/api/models/${modelName}/code`);
                const data = await response.json();

                document.getElementById('modalTitle').textContent = data.name;

                const metaInfo = `
                    <div class="model-meta-info">
                        <p><strong>Type:</strong> ${data.config.materialized || 'view'}</p>
                        <p><strong>Depends on:</strong> ${data.depends_on.length > 0 ? data.depends_on.join(', ') : 'None'}</p>
                        <p><strong>File:</strong> ${data.file_path}</p>
                    </div>
                `;

                const code = `
                    <h3>SQL Code:</h3>
                    <pre class="code-block"><code>${escapeHtml(data.code)}</code></pre>
                `;

                document.getElementById('modalBody').innerHTML = metaInfo + code;
                document.getElementById('codeModal').style.display = 'block';

            } catch (error) {
                console.error('Error loading model code:', error);
                alert('Failed to load model code');
            }
        }

        function closeModal(modalId) {
            document.getElementById(modalId).style.display = 'none';
        }

        function switchTab(tabName) {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            event.target.classList.add('active');

            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            document.getElementById(`${tabName}-tab`).classList.add('active');

            // Load data if needed
            if (tabName === 'runs') {
                loadRuns();
            } else if (tabName === 'lineage') {
                drawLineage(modelsData);
            } else if (tabName === 'dashboards') {
                loadDashboards();
            }
        }

        async function loadDashboards() {
            try {
                const response = await fetch('/api/exposures');
                const data = await response.json();

                const dashboardsList = document.getElementById('dashboards-list');

                if (data.exposures.length === 0) {
                    dashboardsList.innerHTML = `
                        <div style="padding: 40px; text-align: center; color: #888;">
                            <h3>No dashboards defined yet</h3>
                            <p>Create an <code>exposures.yml</code> file to document which dashboards use which models.</p>
                        </div>
                    `;
                    return;
                }

                // Clear the list first
                dashboardsList.innerHTML = '';

                data.exposures.forEach(exposure => {
                    const typeClass = exposure.type === 'dashboard' ? 'type-dashboard' : 'type-report';
                    const icon = exposure.type === 'dashboard' ? '📊' : '📄';

                    // Extract model names from depends_on (remove ref() wrapper)
                    const models = exposure.depends_on.map(dep => {
                        const match = dep.match(/ref\(['"]([^'"]+)['"]\)/);
                        return match ? match[1] : dep;
                    });

                    // Safely get description
                    const description = (exposure.description || 'No description provided').trim();
                    const descriptionLines = description.split('\\n').filter(l => l.trim());
                    const shortDescription = descriptionLines[0] || 'No description provided';

                    // Create card element
                    const card = document.createElement('div');
                    card.className = 'dashboard-card';
                    card.id = 'card-' + exposure.slug;
                    card.onclick = (e) => toggleExpand(e, exposure.slug);

                    // Build header
                    const header = document.createElement('div');
                    header.className = 'dashboard-header';
                    header.innerHTML = `
                        <div class="dashboard-left">
                            <span>${icon}</span>
                            <span class="dashboard-name">${exposure.name}</span>
                            <span class="dashboard-id">#${exposure.id}</span>
                        </div>
                        <div>
                            <span class="dashboard-type ${typeClass}">${exposure.type.toUpperCase()}</span>
                            <span class="expand-indicator">▼</span>
                        </div>
                    `;

                    // Build summary
                    const summary = document.createElement('div');
                    summary.className = 'dashboard-summary';
                    summary.textContent = shortDescription;

                    // Build details section
                    const details = document.createElement('div');
                    details.className = 'dashboard-details';

                    // Description
                    const descDiv = document.createElement('div');
                    descDiv.className = 'dashboard-description';
                    descDiv.innerHTML = description.replace(/\\n/g, '<br>');
                    details.appendChild(descDiv);

                    // Models section
                    const modelsTitle = document.createElement('strong');
                    modelsTitle.style.color = '#667eea';
                    modelsTitle.textContent = '📋 Uses These Models:';
                    details.appendChild(modelsTitle);

                    const modelsDiv = document.createElement('div');
                    modelsDiv.className = 'dashboard-models';
                    models.forEach(model => {
                        const tag = document.createElement('span');
                        tag.className = 'model-tag';
                        tag.textContent = model;
                        tag.onclick = (e) => {
                            e.stopPropagation();
                            switchTab('lineage');
                            setTimeout(() => highlightModel(model), 100);
                        };
                        modelsDiv.appendChild(tag);
                    });
                    details.appendChild(modelsDiv);

                    // Owner info
                    if (exposure.owner) {
                        const ownerDiv = document.createElement('div');
                        ownerDiv.className = 'dashboard-owner';
                        ownerDiv.textContent = `👤 Owner: ${exposure.owner.name} (${exposure.owner.email})`;
                        details.appendChild(ownerDiv);
                    }

                    // View button
                    const btnDiv = document.createElement('div');
                    btnDiv.style.marginTop = '10px';
                    const btn = document.createElement('button');
                    btn.textContent = '🔗 View Dashboard Details';
                    btn.style.cssText = 'background: #667eea; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 0.9em;';
                    btn.onclick = (e) => {
                        e.stopPropagation();
                        viewDashboard(exposure.slug);
                    };
                    btnDiv.appendChild(btn);
                    details.appendChild(btnDiv);

                    // Assemble card
                    card.appendChild(header);
                    card.appendChild(summary);
                    card.appendChild(details);
                    dashboardsList.appendChild(card);
                });

            } catch (error) {
                console.error('Error loading dashboards:', error);
                document.getElementById('dashboards-list').innerHTML = '<p style="color: #ef4444;">Failed to load dashboards</p>';
            }
        }

        function toggleExpand(event, slug) {
            event.stopPropagation();
            const card = document.getElementById(`card-${slug}`);
            card.classList.toggle('expanded');
        }

        function viewDashboard(slug) {
            // In a real implementation, this would navigate to a detail page
            // For now, we'll show an alert
            alert(`Navigating to dashboard: /dashboards/${slug}\n\nIn a full implementation, this would show detailed dashboard analytics, usage metrics, and lineage visualization.`);
        }

        async function loadRuns() {
            try {
                const response = await fetch('/api/runs');
                const data = await response.json();

                const runsList = document.getElementById('runs-list');

                if (data.runs.length === 0) {
                    runsList.innerHTML = '<p style="color: #888;">No runs yet. Click "Run Transformations" to execute your first pipeline.</p>';
                    return;
                }

                runsList.innerHTML = data.runs.map(run => {
                    const timestamp = new Date(run.timestamp).toLocaleString();
                    const successRate = run.summary.total_models > 0
                        ? ((run.summary.successes / run.summary.total_models) * 100).toFixed(0)
                        : 0;

                    return `
                        <div class="run-item" onclick="viewRunLogs('${run.run_id}')">
                            <div class="run-header">
                                <span class="run-id">${run.run_id}</span>
                                <span class="run-time">${timestamp}</span>
                            </div>
                            <div class="run-stats">
                                <span class="stat-success">✓ ${run.summary.successes} success</span>
                                <span class="stat-failure">✗ ${run.summary.failures} failed</span>
                                <span>⏱️ ${run.summary.total_execution_time.toFixed(2)}s</span>
                                <span>📊 ${successRate}% success rate</span>
                            </div>
                        </div>
                    `;
                }).join('');

            } catch (error) {
                console.error('Error loading runs:', error);
                document.getElementById('runs-list').innerHTML = '<p style="color: #ef4444;">Failed to load runs</p>';
            }
        }

        async function viewRunLogs(runId) {
            try {
                const response = await fetch(`/api/runs/${runId}`);
                const data = await response.json();

                document.getElementById('logsModalTitle').textContent = `Run Logs - ${data.run_id}`;

                const summary = `
                    <div class="model-meta-info">
                        <p><strong>Timestamp:</strong> ${new Date(data.timestamp).toLocaleString()}</p>
                        <p><strong>Total Models:</strong> ${data.summary.total_models}</p>
                        <p><strong>Successes:</strong> ${data.summary.successes}</p>
                        <p><strong>Failures:</strong> ${data.summary.failures}</p>
                        <p><strong>Total Time:</strong> ${data.summary.total_execution_time.toFixed(3)}s</p>
                    </div>
                `;

                const logs = data.logs.map(log => {
                    // Extract log level for coloring
                    const levelMatch = log.match(/\[(INFO|SUCCESS|ERROR|WARNING)\]/);
                    const level = levelMatch ? levelMatch[1] : 'INFO';

                    return `<div class="log-entry log-level-${level}">${escapeHtml(log)}</div>`;
                }).join('');

                const logsViewer = `
                    <h3>Execution Logs:</h3>
                    <div class="log-viewer">${logs}</div>
                `;

                document.getElementById('logsModalBody').innerHTML = summary + logsViewer;
                document.getElementById('logsModal').style.display = 'block';

            } catch (error) {
                console.error('Error loading run logs:', error);
                alert('Failed to load run logs');
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        async function runTransformations() {
            const statusDiv = document.getElementById('execution-status');
            const runBtn = document.getElementById('runBtn');

            try {
                // Disable button and show running status
                runBtn.disabled = true;
                statusDiv.className = 'execution-status running';
                statusDiv.innerHTML = '<strong>⏳ Running transformations...</strong><br>Executing models in DAG order';

                // Execute transformations
                const response = await fetch('/api/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                const data = await response.json();

                if (response.ok) {
                    // Show success
                    statusDiv.className = 'execution-status success';
                    statusDiv.innerHTML = `
                        <strong>✅ Transformations completed successfully!</strong><br>
                        <p>Total Models: ${data.summary.total_models}</p>
                        <p>✓ Successes: ${data.summary.successes}</p>
                        <p>✗ Failures: ${data.summary.failures}</p>
                        <p>⏱️ Total Time: ${data.summary.total_execution_time.toFixed(3)}s</p>
                    `;

                    // Refresh models to show updated status
                    await loadModels();
                } else {
                    throw new Error(data.detail || 'Execution failed');
                }

            } catch (error) {
                console.error('Error executing transformations:', error);
                statusDiv.className = 'execution-status error';
                statusDiv.innerHTML = `
                    <strong>❌ Execution failed</strong><br>
                    <p>${error.message}</p>
                `;
            } finally {
                runBtn.disabled = false;
            }
        }

        // Close modal when clicking outside
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                closeModal(event.target.id);
            }
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
