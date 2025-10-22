/**
 * TransformDash JavaScript - Modern UI
 * Main application logic for dashboard interactivity with sidebar navigation
 */

// ============================================
// UTILITY FUNCTIONS
// ============================================

// Show Toast Notification
function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: slideInRight 0.3s ease-out;
        font-size: 0.9rem;
        max-width: 350px;
    `;
    toast.textContent = message;

    // Add to page
    document.body.appendChild(toast);

    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================
// SIDEBAR & NAVIGATION FUNCTIONS
// ============================================

// Toggle Sidebar
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
    sidebar.classList.toggle('open');
}

// Switch Between Views
function switchView(viewName) {
    // Hide all views
    document.querySelectorAll('.view-content').forEach(view => {
        view.classList.remove('active');
    });

    // Show selected view
    const targetView = document.getElementById(viewName + '-view');
    if (targetView) {
        targetView.classList.add('active');
    }

    // Update navigation active state
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    const activeNav = document.querySelector(`[data-view="${viewName}"]`);
    if (activeNav) {
        activeNav.classList.add('active');
    }

    // Load content for the view
    switch(viewName) {
        case 'overview':
            loadOverview();
            break;
        case 'dashboards':
            loadDashboards();
            break;
        case 'models':
            loadModels();
            break;
        case 'lineage':
            loadLineageGraph();
            break;
        case 'charts':
            loadAllCharts();
            break;
        case 'chart-builder':
            // Chart builder view is ready to use
            break;
        case 'runs':
            loadRuns();
            break;
        case 'settings':
            // Settings view is static
            break;
    }
}

// Load Overview Data
async function loadOverview() {
    await loadModels(); // This will update the metrics
    await loadDashboardsAndChartsCount();
    loadRecentRuns();
    loadDataFreshness();
    loadTableStats();
}

// Load Dashboards and Charts Count
async function loadDashboardsAndChartsCount() {
    try {
        // Load dashboards
        const dashboardsResponse = await fetch('/api/dashboards');
        const dashboardsData = await dashboardsResponse.json();
        const totalDashboards = dashboardsData.dashboards ? dashboardsData.dashboards.length : 0;
        document.getElementById('total-dashboards').textContent = totalDashboards;

        // Count total charts across all dashboards
        let totalCharts = 0;
        if (dashboardsData.dashboards) {
            dashboardsData.dashboards.forEach(dashboard => {
                if (dashboard.charts) {
                    totalCharts += dashboard.charts.length;
                }
            });
        }
        document.getElementById('total-charts').textContent = totalCharts;
    } catch (error) {
        console.error('Error loading dashboards/charts count:', error);
        document.getElementById('total-dashboards').textContent = '0';
        document.getElementById('total-charts').textContent = '0';
    }
}

// Load Data Freshness (Last Run Time)
async function loadDataFreshness() {
    try {
        const response = await fetch('/api/runs?limit=1');
        const data = await response.json();
        const lastRunEl = document.getElementById('last-run-time');

        if (data.runs && data.runs.length > 0) {
            const lastRun = new Date(data.runs[0].timestamp);
            const now = new Date();
            const diffMs = now - lastRun;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);

            if (diffMins < 1) {
                lastRunEl.textContent = 'Just now';
            } else if (diffMins < 60) {
                lastRunEl.textContent = `${diffMins}m ago`;
            } else if (diffHours < 24) {
                lastRunEl.textContent = `${diffHours}h ago`;
            } else {
                lastRunEl.textContent = `${diffDays}d ago`;
            }
        } else {
            lastRunEl.textContent = 'Never';
        }
    } catch (error) {
        console.error('Error loading data freshness:', error);
        document.getElementById('last-run-time').textContent = 'Unknown';
    }
}

// Load Table Stats (Total Rows)
async function loadTableStats() {
    try {
        // Query to get approximate total rows from all tables in gold schema
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: `
                    SELECT SUM(n_live_tup)::bigint as total_rows
                    FROM pg_stat_user_tables
                    WHERE schemaname IN ('gold', 'silver', 'bronze', 'raw')
                `
            })
        });

        const data = await response.json();
        const totalRowsEl = document.getElementById('total-rows');

        if (data.data && data.data.length > 0 && data.data[0].total_rows) {
            const totalRows = parseInt(data.data[0].total_rows);
            // Format with commas
            totalRowsEl.textContent = totalRows.toLocaleString();
        } else {
            totalRowsEl.textContent = '0';
        }
    } catch (error) {
        console.error('Error loading table stats:', error);
        document.getElementById('total-rows').textContent = '—';
    }
}

// Load Recent Runs for Overview
async function loadRecentRuns() {
    try {
        const response = await fetch('/api/runs?limit=5');
        const data = await response.json();
        const container = document.getElementById('recent-runs-list');

        if (!data.runs || data.runs.length === 0) {
            container.innerHTML = '<p style="color: #888; padding: 20px;">No recent runs</p>';
            return;
        }

        container.innerHTML = data.runs.map(run => {
            const status = run.status || 'completed';
            const badgeClass = status === 'success' || status === 'completed' ? 'success' :
                              status === 'error' || status === 'failed' ? 'error' : 'info';
            const timestamp = run.timestamp ? new Date(run.timestamp).toLocaleString() : 'Unknown time';

            return `
                <div class="run-item" style="padding: 12px; border-bottom: 1px solid var(--color-border); cursor: pointer;" onclick="switchView('runs')">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="color: var(--color-text-primary);">${run.run_id}</strong>
                            <span class="badge badge-${badgeClass}" style="margin-left: 8px; font-size: 0.75rem;">
                                ${status}
                            </span>
                        </div>
                        <small style="color: #888; font-size: 0.8rem;">${timestamp}</small>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading recent runs:', error);
    }
}

// Toggle Notifications
function toggleNotifications() {
    alert('Notifications feature coming soon!');
}

// Open Settings
function openSettings() {
    switchView('settings');
}

// Global Search
function handleGlobalSearch(event) {
    const query = event.target.value.toLowerCase();
    const results = document.getElementById('searchResults');

    if (query.length < 2) {
        results.classList.remove('active');
        return;
    }

    // Search across models, dashboards, charts
    const searchResults = [];

    // Search models
    modelsData.forEach(model => {
        if (model.name.toLowerCase().includes(query)) {
            searchResults.push({
                type: 'model',
                name: model.name,
                subtitle: model.type
            });
        }
    });

    // Display results
    if (searchResults.length === 0) {
        results.innerHTML = '<div style="padding: 12px; color: #888;">No results found</div>';
    } else {
        results.innerHTML = searchResults.map(result => `
            <div class="search-result-item" style="padding: 12px; border-bottom: 1px solid var(--color-border); cursor: pointer;" onclick="goToResult('${result.type}', '${result.name}')">
                <div style="font-weight: 600;">${result.name}</div>
                <div style="font-size: 0.85em; color: #888;">${result.subtitle}</div>
            </div>
        `).join('');
    }

    results.classList.add('active');
}

function goToResult(type, name) {
    const results = document.getElementById('searchResults');
    results.classList.remove('active');
    document.getElementById('globalSearch').value = '';

    if (type === 'model') {
        switchView('models');
    }
}

// Settings Functions
function saveBranding() {
    const appName = document.getElementById('app-name').value;
    const logoUrl = document.getElementById('logo-url').value;
    const primaryColor = document.getElementById('primary-color').value;

    // Save to localStorage
    localStorage.setItem('appName', appName);
    localStorage.setItem('logoUrl', logoUrl);
    localStorage.setItem('primaryColor', primaryColor);

    // Apply changes
    if (primaryColor) {
        document.documentElement.style.setProperty('--color-primary', primaryColor);
    }

    alert('Branding saved!');
}

function createNewDashboard() {
    alert('Dashboard creation feature coming soon!');
}

function runTransformations() {
    // Reuse existing function
    if (typeof window.runTransformations === 'function') {
        window.runTransformations();
    }
}

// ============================================
// INITIALIZE ON PAGE LOAD
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Load overview by default
    switchView('overview');

    // Close search results when clicking outside
    document.addEventListener('click', function(event) {
        const searchContainer = document.querySelector('.search-container');
        if (searchContainer && !searchContainer.contains(event.target)) {
            document.getElementById('searchResults')?.classList.remove('active');
        }
    });
});

// Global state
let modelsData = [];
let allRuns = [];
let currentFilter = 'all';

// Dark Mode Toggle
function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');

    // Update theme icons
    const lightIcon = document.getElementById('theme-icon-light');
    const darkIcon = document.getElementById('theme-icon-dark');

    if (isDark) {
        lightIcon?.classList.add('hidden');
        darkIcon?.classList.remove('hidden');
    } else {
        lightIcon?.classList.remove('hidden');
        darkIcon?.classList.add('hidden');
    }

    localStorage.setItem('darkMode', isDark);
}

// Load dark mode preference on page load
// Dark mode by default (unless explicitly disabled)
const darkModeSetting = localStorage.getItem('darkMode');
if (darkModeSetting === null || darkModeSetting === 'true') {
    document.body.classList.add('dark-mode');
    const lightIcon = document.getElementById('theme-icon-light');
    const darkIcon = document.getElementById('theme-icon-dark');
    lightIcon?.classList.add('hidden');
    darkIcon?.classList.remove('hidden');
    // Set to true if not set yet
    if (darkModeSetting === null) {
        localStorage.setItem('darkMode', 'true');
    }
}

// Load Models
let currentModelFilter = null; // Track current filter

async function loadModels() {
    try {
        const response = await fetch('/api/models');
        modelsData = await response.json();

        // Update stats (these exist in overview)
        const totalModelsEl = document.getElementById('total-models');
        const bronzeEl = document.getElementById('bronze-count');
        const silverEl = document.getElementById('silver-count');
        const goldEl = document.getElementById('gold-count');

        if (totalModelsEl) totalModelsEl.textContent = modelsData.length;
        if (bronzeEl) bronzeEl.textContent = modelsData.filter(m => m.name.startsWith('stg_')).length;
        if (silverEl) silverEl.textContent = modelsData.filter(m => m.name.startsWith('int_')).length;
        if (goldEl) goldEl.textContent = modelsData.filter(m => m.name.startsWith('fct_') || m.name.startsWith('dim_')).length;

        // Display models list (if we're in models view)
        displayModels(modelsData, currentModelFilter);

    } catch (error) {
        console.error('Error loading models:', error);
        const modelsList = document.getElementById('models-list');
        if (modelsList) {
            modelsList.innerHTML = `
                <div style="text-align: center; padding: 60px 20px; background: #fee; border-radius: 12px; border: 1px solid #fcc;">
                    <div style="font-size: 4em; margin-bottom: 20px;">❌</div>
                    <h3 style="margin-bottom: 10px; color: #c00;">Failed to Load Models</h3>
                    <p style="color: #666;">There was an error loading the transformation models. Check the console for details.</p>
                    <pre style="margin-top: 20px; padding: 12px; background: white; border-radius: 8px; text-align: left; font-size: 0.85em;">${error.message}</pre>
                </div>
            `;
        }
    }
}

function filterModelsByLayer(layer) {
    currentModelFilter = layer;
    setTimeout(() => displayModels(modelsData, layer), 100);
}

// Find which dashboards/charts use a specific model
async function findModelUsage(modelName) {
    try {
        const response = await fetch('/api/dashboards');
        const data = await response.json();
        const usage = [];

        if (data.dashboards) {
            data.dashboards.forEach(dashboard => {
                if (dashboard.charts) {
                    dashboard.charts.forEach(chart => {
                        // Check if the chart uses this model
                        if (chart.model === modelName || chart.model === `gold.${modelName}` ||
                            chart.model === `silver.${modelName}` || chart.model === `bronze.${modelName}` ||
                            chart.model === `raw.${modelName}`) {
                            usage.push({
                                dashboardId: dashboard.id,
                                dashboardName: dashboard.name,
                                chartId: chart.id,
                                chartTitle: chart.title
                            });
                        }
                    });
                }
            });
        }

        return usage;
    } catch (error) {
        console.error('Error finding model usage:', error);
        return [];
    }
}

async function displayModels(models, filterLayer = null) {
    const modelsList = document.getElementById('models-list');
    if (!modelsList) return; // Not in models view

    if (models.length === 0) {
        modelsList.innerHTML = `
            <div style="text-align: center; padding: 60px 20px; background: white; border-radius: 12px; border: 1px solid var(--color-border);">
                <div style="font-size: 4em; margin-bottom: 20px;">📦</div>
                <h3 style="margin-bottom: 10px;">No Models Found</h3>
                <p style="color: #888;">Add SQL or Python transformation models to the models/ directory to get started.</p>
            </div>
        `;
        return;
    }

    // Group models by layer
    const groupedModels = {
        bronze: models.filter(m => getModelLayer(m.name) === 'bronze'),
        silver: models.filter(m => getModelLayer(m.name) === 'silver'),
        gold: models.filter(m => getModelLayer(m.name) === 'gold')
    };

    // Apply filter if specified
    const layersToShow = filterLayer ? [filterLayer] : ['bronze', 'silver', 'gold'];

    // Filter button styles
    const filterButtons = `
        <div style="display: flex; gap: 0.5rem; margin-bottom: 1.5rem; align-items: center;">
            <span style="font-weight: 600; color: #6b7280; margin-right: 0.5rem;">Filter:</span>
            <button onclick="currentModelFilter = null; displayModels(modelsData, null)"
                    class="btn ${!filterLayer ? 'btn-primary' : 'btn-secondary'}"
                    style="padding: 0.4rem 0.8rem; font-size: 0.875rem;">
                All Layers
            </button>
            <button onclick="filterModelsByLayer('bronze')"
                    class="btn ${filterLayer === 'bronze' ? 'btn-primary' : 'btn-secondary'}"
                    style="padding: 0.4rem 0.8rem; font-size: 0.875rem;">
                🥉 Bronze
            </button>
            <button onclick="filterModelsByLayer('silver')"
                    class="btn ${filterLayer === 'silver' ? 'btn-primary' : 'btn-secondary'}"
                    style="padding: 0.4rem 0.8rem; font-size: 0.875rem;">
                🥈 Silver
            </button>
            <button onclick="filterModelsByLayer('gold')"
                    class="btn ${filterLayer === 'gold' ? 'btn-primary' : 'btn-secondary'}"
                    style="padding: 0.4rem 0.8rem; font-size: 0.875rem;">
                🥇 Gold
            </button>
        </div>
    `;

    let html = filterButtons;

    layersToShow.forEach(layer => {
        const layerModels = groupedModels[layer];
        if (layerModels.length === 0) return;

        const layerIcons = { bronze: '🥉', silver: '🥈', gold: '🥇' };
        const layerColors = {
            bronze: { bg: 'rgba(205, 127, 50, 0.1)', text: '#b06727' },
            silver: { bg: 'rgba(192, 192, 192, 0.2)', text: '#6b7280' },
            gold: { bg: 'rgba(255, 215, 0, 0.15)', text: '#e6c200' }
        };

        html += `
            <div style="margin-bottom: 2rem;">
                <h3 style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; color: ${layerColors[layer].text}; font-size: 1.25rem;">
                    <span>${layerIcons[layer]}</span>
                    <span>${layer.charAt(0).toUpperCase() + layer.slice(1)} Layer</span>
                    <span style="font-size: 0.875rem; font-weight: normal; color: #9ca3af;">(${layerModels.length} models)</span>
                </h3>
                <div style="display: grid; gap: 1rem;">
        `;

        layerModels.forEach(model => {
            html += `
                <div class="model-card" id="model-${model.name}">
                    <div class="model-card-content" onclick="toggleModelCode('${model.name}')">
                        <div class="model-info">
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <span class="expand-icon" id="expand-model-${model.name}">▶</span>
                                <h4 class="model-name">${model.name}</h4>
                            </div>
                            <div class="model-badges">
                                <span class="badge badge-${layer}">${layer.toUpperCase()}</span>
                                <span class="badge badge-type">${model.type.toUpperCase()}</span>
                            </div>
                            ${model.depends_on.length > 0 ?
                                `<div class="model-dependencies"><strong>Depends on:</strong> ${model.depends_on.join(', ')}</div>` :
                                '<div class="model-dependencies">No dependencies</div>'}
                            <div class="model-usage" id="usage-${model.name}" style="margin-top: 0.5rem;">
                                <em style="color: #888; font-size: 0.875rem;">Loading usage...</em>
                            </div>
                        </div>
                    </div>
                    <div class="model-code-section" id="code-${model.name}" style="display: none;">
                        <div class="model-code-actions">
                            <input type="text" class="code-search" id="search-${model.name}" placeholder="Search in code..." onkeyup="searchModelCode('${model.name}')">
                            <button class="action-btn-small" onclick="copyModelCode('${model.name}')">📋 Copy Code</button>
                        </div>
                        <div class="model-code-content" id="content-${model.name}">
                            <div class="loading">Loading code...</div>
                        </div>
                    </div>
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;
    });

    modelsList.innerHTML = html;

    // Load usage information for all models asynchronously
    models.forEach(async (model) => {
        const usage = await findModelUsage(model.name);
        const usageEl = document.getElementById(`usage-${model.name}`);

        if (usageEl) {
            if (usage.length === 0) {
                usageEl.innerHTML = '<em style="color: #888; font-size: 0.875rem;">Not used in any dashboards</em>';
            } else {
                // Group usage by dashboard
                const dashboardMap = {};
                usage.forEach(u => {
                    if (!dashboardMap[u.dashboardId]) {
                        dashboardMap[u.dashboardId] = {
                            id: u.dashboardId,
                            name: u.dashboardName,
                            charts: []
                        };
                    }
                    dashboardMap[u.dashboardId].charts.push(u.chartTitle);
                });

                const dashboards = Object.values(dashboardMap);
                const totalCharts = usage.length;

                usageEl.innerHTML = `
                    <div style="font-size: 0.875rem;">
                        <strong style="color: #374151;">Used in:</strong>
                        ${dashboards.map(d => `
                            <span style="display: inline-block; margin: 2px 4px 2px 0;">
                                <a href="#" onclick="event.stopPropagation(); openDashboard('${d.id}'); return false;"
                                   style="color: #667eea; text-decoration: none;"
                                   onmouseover="this.style.textDecoration='underline'"
                                   onmouseout="this.style.textDecoration='none'"
                                   title="${d.charts.join(', ')}">
                                    📊 ${d.name}
                                </a>
                                <span style="color: #888; font-size: 0.8rem;">(${d.charts.length})</span>
                            </span>
                        `).join('')}
                    </div>
                `;
            }
        }
    });
}

// Navigate to a specific dashboard
function openDashboard(dashboardId) {
    window.location.href = `/dashboard/${dashboardId}`;
}

function getModelLayer(name) {
    if (name.startsWith('stg_')) return 'bronze';
    if (name.startsWith('int_')) return 'silver';
    if (name.startsWith('fct_') || name.startsWith('dim_')) return 'gold';
    return 'unknown';
}

// Draw Lineage Graph with D3.js
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

    // Draw links (adjusted for wider nodes)
    const nodeHalfWidth = 120;  // Half of nodeWidth (240/2)

    const linkPaths = svg.selectAll('.link')
        .data(links)
        .enter()
        .append('path')
        .attr('class', 'link')
        .attr('data-source', d => d.source)
        .attr('data-target', d => d.target)
        .attr('d', d => {
            const source = nodes.find(n => n.id === d.source);
            const target = nodes.find(n => n.id === d.target);
            if (!source || !target) return '';

            return `M ${source.x + nodeHalfWidth} ${source.y}
                    C ${(source.x + target.x) / 2} ${source.y},
                      ${(source.x + target.x) / 2} ${target.y},
                      ${target.x - nodeHalfWidth} ${target.y}`;
        })
        .style('cursor', 'pointer');

    // Draw nodes (wider and taller for better readability)
    const nodeWidth = 240;  // Increased to accommodate longer names
    const nodeHeight = 56;  // Slightly taller
    const halfWidth = nodeWidth / 2;
    const halfHeight = nodeHeight / 2;

    const nodeGroups = svg.selectAll('.node')
        .data(nodes)
        .enter()
        .append('g')
        .attr('class', d => `node ${d.layer}`)
        .attr('transform', d => `translate(${d.x - halfWidth}, ${d.y - halfHeight})`);

    nodeGroups.append('rect')
        .attr('width', nodeWidth)
        .attr('height', nodeHeight)
        .attr('rx', 8)
        .attr('ry', 8);

    nodeGroups.append('text')
        .attr('x', halfWidth)
        .attr('y', halfHeight + 5)
        .text(d => d.id.length > 30 ? d.id.substring(0, 28) + '...' : d.id)  // Show more characters
        .append('title')
        .text(d => d.id);

    // Add click functionality to nodes
    nodeGroups
        .style('cursor', 'pointer')
        .on('click', function(event, d) {
            viewModelCode(d.id);
        });

    // Add click and hover functionality to links
    linkPaths
        .on('click', function(event, d) {
            event.stopPropagation();
            highlightConnection(d.source, d.target, svg);
        })
        .on('mouseenter', function(event, d) {
            // Temporary highlight on hover
            d3.select(this)
                .style('stroke', '#667eea')
                .style('stroke-width', '4px')
                .style('opacity', '1');
        })
        .on('mouseleave', function(event, d) {
            // Reset hover unless this link is clicked/highlighted
            const isHighlighted = d3.select(this).classed('highlighted');
            if (!isHighlighted) {
                d3.select(this)
                    .style('stroke', null)
                    .style('stroke-width', null)
                    .style('opacity', null);
            }
        });

    // Click on background to clear highlights
    svg.on('click', function(event) {
        if (event.target === this) {
            clearLineageHighlights(svg);
        }
    });
}

// Highlight a specific connection in the lineage graph
function highlightConnection(sourceId, targetId, svg) {
    // Clear previous highlights
    clearLineageHighlights(svg);

    // Highlight the clicked link
    svg.selectAll('.link')
        .filter(function() {
            const source = d3.select(this).attr('data-source');
            const target = d3.select(this).attr('data-target');
            return source === sourceId && target === targetId;
        })
        .classed('highlighted', true)
        .style('stroke', '#667eea')
        .style('stroke-width', '4px')
        .style('opacity', '1');

    // Highlight connected nodes
    svg.selectAll('.node')
        .filter(function(d) {
            return d.id === sourceId || d.id === targetId;
        })
        .classed('highlighted', true)
        .select('rect')
        .style('stroke', '#667eea')
        .style('stroke-width', '3px')
        .style('filter', 'brightness(1.2)');

    // Dim other elements
    svg.selectAll('.link:not(.highlighted)')
        .style('opacity', '0.2');

    svg.selectAll('.node:not(.highlighted)')
        .style('opacity', '0.3');
}

// Clear all highlights in the lineage graph
function clearLineageHighlights(svg) {
    // Reset links
    svg.selectAll('.link')
        .classed('highlighted', false)
        .style('stroke', null)
        .style('stroke-width', null)
        .style('opacity', null);

    // Reset nodes
    svg.selectAll('.node')
        .classed('highlighted', false)
        .style('opacity', null)
        .select('rect')
        .style('stroke', null)
        .style('stroke-width', null)
        .style('filter', null);
}

// Highlight Model (show code in modal)
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

// Alias for viewModelCode - calls highlightModel (for lineage graph compatibility)
function viewModelCode(modelName) {
    // For lineage graph clicks, open modal
    highlightModel(modelName);
}

// Toggle model code inline (for model cards)
let expandedModels = new Set();

async function toggleModelCode(modelName) {
    const codeSection = document.getElementById(`code-${modelName}`);
    const expandIcon = document.getElementById(`expand-model-${modelName}`);
    const contentDiv = document.getElementById(`content-${modelName}`);

    if (expandedModels.has(modelName)) {
        // Collapse
        codeSection.style.display = 'none';
        expandIcon.textContent = '▶';
        expandedModels.delete(modelName);
    } else {
        // Expand
        codeSection.style.display = 'block';
        expandIcon.textContent = '▼';
        expandedModels.add(modelName);

        // Load code if not already loaded
        if (contentDiv.innerHTML.includes('Loading code')) {
            await loadModelCodeInline(modelName);
        }
    }
}

async function loadModelCodeInline(modelName) {
    const contentDiv = document.getElementById(`content-${modelName}`);

    try {
        const response = await fetch(`/api/models/${modelName}/code`);
        const data = await response.json();

        const metaInfo = `
            <div class="model-meta-info">
                <div><strong>Type:</strong> ${data.config.materialized || 'view'}</div>
                <div><strong>Depends on:</strong> ${data.depends_on.length > 0 ? data.depends_on.join(', ') : 'None'}</div>
                <div><strong>File:</strong> ${data.file_path}</div>
            </div>
        `;

        const code = `
            <pre class="code-block" id="code-block-${modelName}"><code>${escapeHtml(data.code)}</code></pre>
        `;

        contentDiv.innerHTML = metaInfo + code;
    } catch (error) {
        console.error('Error loading model code:', error);
        contentDiv.innerHTML = '<div class="error-logs">Failed to load model code</div>';
    }
}

// Search in model code
function searchModelCode(modelName) {
    const searchInput = document.getElementById(`search-${modelName}`);
    const query = searchInput.value.toLowerCase();
    const codeBlock = document.getElementById(`code-block-${modelName}`);

    if (!codeBlock) return;

    const code = codeBlock.querySelector('code');
    if (!code) return;

    // Get original text (stored in data attribute)
    if (!code.dataset.originalText) {
        code.dataset.originalText = code.textContent;
    }

    const originalText = code.dataset.originalText;

    if (!query) {
        // Reset to original
        code.innerHTML = escapeHtml(originalText);
        return;
    }

    // Highlight matches
    const lines = originalText.split('\n');
    const highlightedLines = lines.map(line => {
        if (line.toLowerCase().includes(query)) {
            const regex = new RegExp(`(${query})`, 'gi');
            return escapeHtml(line).replace(regex, '<mark>$1</mark>');
        }
        return escapeHtml(line);
    });

    code.innerHTML = highlightedLines.join('\n');
}

// Copy model code to clipboard
async function copyModelCode(modelName) {
    const codeBlock = document.getElementById(`code-block-${modelName}`);
    if (!codeBlock) return;

    const code = codeBlock.querySelector('code');
    if (!code) return;

    const text = code.dataset.originalText || code.textContent;

    try {
        await navigator.clipboard.writeText(text);

        // Show feedback
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = '✓ Copied!';
        btn.style.background = 'var(--color-success)';
        btn.style.color = 'white';

        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.background = '';
            btn.style.color = '';
        }, 2000);
    } catch (error) {
        console.error('Error copying to clipboard:', error);
        alert('Failed to copy code');
    }
}

// Load Lineage Graph
async function loadLineageGraph() {
    try {
        const response = await fetch('/api/models');
        const models = await response.json();

        if (models.length === 0) {
            const container = document.getElementById('lineage-graph');
            if (container) {
                container.innerHTML = `
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 400px; color: #888;">
                        <div style="font-size: 4em; margin-bottom: 20px;">🔗</div>
                        <h3 style="color: #666;">No Models to Display</h3>
                        <p>Add models to see their lineage relationships</p>
                    </div>
                `;
            }
            return;
        }

        drawLineage(models);
    } catch (error) {
        console.error('Error loading lineage graph:', error);
        const container = document.getElementById('lineage-graph');
        if (container) {
            container.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 400px; background: #fee; color: #c00; padding: 20px; border-radius: 12px;">
                    <div style="font-size: 4em; margin-bottom: 20px;">❌</div>
                    <h3>Failed to Load Lineage Graph</h3>
                    <pre style="margin-top: 10px; padding: 10px; background: white; border-radius: 6px;">${error.message}</pre>
                </div>
            `;
        }
    }
}

// Close Modal
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Edit Dashboard - Add Charts
let currentEditingDashboardId = null;

async function openEditDashboardModal(dashboardId, dashboardName) {
    currentEditingDashboardId = dashboardId;
    document.getElementById('editDashboardModalTitle').textContent = `Edit Dashboard: ${dashboardName}`;

    // Fetch all available charts
    try {
        const response = await fetch('/api/charts');
        const data = await response.json();

        const chartsList = document.getElementById('availableChartsList');
        chartsList.innerHTML = '';

        if (data.charts.length === 0) {
            chartsList.innerHTML = '<p style="color: #6b7280; text-align: center; padding: 2rem;">No charts available. Create charts first in the Charts view.</p>';
        } else {
            data.charts.forEach(chart => {
                const chartCard = document.createElement('div');
                chartCard.style.cssText = 'padding: 1rem; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 0.75rem; display: flex; justify-content: space-between; align-items: center; background: white;';

                chartCard.innerHTML = `
                    <div>
                        <div style="font-weight: 600; color: #111827; margin-bottom: 0.25rem;">${chart.title || chart.id}</div>
                        <div style="font-size: 0.875rem; color: #6b7280;">
                            ${chart.type} • ${chart.model} • ${chart.x_axis} vs ${chart.y_axis}
                            ${chart.dashboardName ? `<br/>Current: ${chart.dashboardName}` : ''}
                        </div>
                    </div>
                    <button class="btn btn-primary btn-sm" onclick="addChartToDashboard('${chart.id}', '${dashboardId}')" style="white-space: nowrap;">
                        Add to Dashboard
                    </button>
                `;

                chartsList.appendChild(chartCard);
            });
        }

        document.getElementById('editDashboardModal').style.display = 'flex';
    } catch (error) {
        console.error('Error loading charts:', error);
        showToast('Failed to load charts', 'error');
    }
}

async function addChartToDashboard(chartId, dashboardId) {
    try {
        const response = await fetch(`/api/dashboards/${dashboardId}/charts/add`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({chart_id: chartId})
        });

        const result = await response.json();

        if (result.success) {
            showToast(result.message, 'success');
            // Reload dashboards to show the new chart
            setTimeout(() => {
                loadDashboards();
            }, 500);
        } else {
            showToast(result.message, 'warning');
        }
    } catch (error) {
        console.error('Error adding chart to dashboard:', error);
        showToast('Failed to add chart to dashboard', 'error');
    }
}

// Switch Tabs
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
        // Activate the matching tab button
        if (tab.getAttribute('onclick') && tab.getAttribute('onclick').includes(`'${tabName}'`)) {
            tab.classList.add('active');
        }
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    const tabContent = document.getElementById(`${tabName}-tab`);
    if (tabContent) {
        tabContent.classList.add('active');
    }

    // Load data if needed
    if (tabName === 'runs') {
        loadRuns();
    } else if (tabName === 'lineage') {
        drawLineage(modelsData);
    } else if (tabName === 'dashboards') {
        loadDashboards();
    } else if (tabName === 'charts') {
        loadAllCharts();
    }
}

// Load Dashboards with Charts
async function loadDashboards() {
    try {
        const response = await fetch('/api/dashboards');
        const data = await response.json();

        const dashboardsList = document.getElementById('dashboards-list');

        if (data.dashboards.length === 0) {
            dashboardsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📊</div>
                    <h3>No dashboards configured</h3>
                    <p>Create a <code>dashboards.yml</code> file to define dashboards with charts.</p>
                </div>
            `;
            return;
        }

        // Clear the list first
        dashboardsList.innerHTML = '';

        data.dashboards.forEach(dashboard => {
            // Create dashboard card
            const card = document.createElement('div');
            card.className = 'dashboard-card';
            card.id = 'dashboard-' + dashboard.id;

            // Dashboard header
            const header = document.createElement('div');
            header.className = 'dashboard-header';
            header.style.cssText = 'cursor: pointer; display: flex; justify-content: space-between; align-items: center;';

            // Left side with name
            const headerLeft = document.createElement('div');
            headerLeft.className = 'dashboard-left';
            headerLeft.onclick = () => toggleDashboard(dashboard.id);
            headerLeft.innerHTML = `
                <span>📊</span>
                <span class="dashboard-name" style="color: #111827 !important;">${dashboard.name}</span>
                <span class="dashboard-id">${dashboard.charts?.length || 0} charts</span>
            `;

            // Right side with action buttons
            const headerRight = document.createElement('div');
            headerRight.style.cssText = 'display: flex; gap: 8px; align-items: center;';
            headerRight.innerHTML = `
                <button class="icon-btn" onclick="event.stopPropagation(); openEditDashboardModal('${dashboard.id}', '${dashboard.name}')" title="Edit Dashboard - Add Charts">
                    ✏️
                </button>
                <button class="icon-btn" onclick="event.stopPropagation(); openDashboardInTab('${dashboard.id}')" title="Open in new tab">
                    🔗
                </button>
                <button class="icon-btn" onclick="event.stopPropagation(); exportDashboardPDF('${dashboard.id}')" title="Export as PDF">
                    📄
                </button>
                <button class="icon-btn" onclick="event.stopPropagation(); exportDashboardData('${dashboard.id}', 'csv')" title="Export as CSV">
                    📊
                </button>
                <button class="icon-btn" onclick="event.stopPropagation(); exportDashboardData('${dashboard.id}', 'excel')" title="Export as Excel">
                    📈
                </button>
                <span class="expand-indicator" id="expand-${dashboard.id}" onclick="toggleDashboard('${dashboard.id}')" style="cursor: pointer; padding: 0 8px;">▼</span>
            `;

            header.appendChild(headerLeft);
            header.appendChild(headerRight);

            // Dashboard description
            const desc = document.createElement('div');
            desc.className = 'dashboard-summary';
            desc.textContent = dashboard.description || 'No description';

            // Filters container
            const filtersContainer = document.createElement('div');
            filtersContainer.id = 'filters-' + dashboard.id;
            filtersContainer.className = 'dashboard-filters';
            filtersContainer.style.display = 'none';  // Hidden until dashboard expanded

            // Charts container (hidden by default, CSS handles styling)
            const chartsContainer = document.createElement('div');
            chartsContainer.id = 'charts-' + dashboard.id;
            chartsContainer.className = 'dashboard-details';

            // Assemble card
            card.appendChild(header);
            card.appendChild(desc);
            card.appendChild(filtersContainer);
            card.appendChild(chartsContainer);
            dashboardsList.appendChild(card);
        });

    } catch (error) {
        console.error('Error loading dashboards:', error);
        document.getElementById('dashboards-list').innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">❌</div>
                <h3>Failed to Load Dashboards</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// Toggle dashboard expansion and load charts
// Use a lock to prevent double-toggling
let toggleLock = new Set();

async function toggleDashboard(dashboardId) {
    console.log('>>> toggleDashboard CALLED for:', dashboardId);
    console.log('>>> Call stack:', new Error().stack);

    // Prevent double-toggle
    if (toggleLock.has(dashboardId)) {
        console.log('>>> Toggle BLOCKED (lock exists) for:', dashboardId);
        return;
    }

    toggleLock.add(dashboardId);
    console.log('>>> Toggle PROCEEDING for:', dashboardId);

    try {
        const dashboardCard = document.getElementById('dashboard-' + dashboardId);
        const chartsContainer = document.getElementById('charts-' + dashboardId);
        const expandIndicator = document.getElementById('expand-' + dashboardId);

        if (!dashboardCard || !chartsContainer || !expandIndicator) {
            console.error('>>> Could not find elements for dashboard:', dashboardId);
            console.error('>>> Missing elements: card=', !!dashboardCard, 'charts=', !!chartsContainer, 'indicator=', !!expandIndicator);
            toggleLock.delete(dashboardId);
            return;
        }

        // Check if currently expanded by looking at the card's class
        const isExpanded = dashboardCard.classList.contains('expanded');
        console.log('>>> Current expanded state:', isExpanded);

        if (!isExpanded) {
            // Expand
            console.log('>>> EXPANDING dashboard:', dashboardId);
            dashboardCard.classList.add('expanded');
            expandIndicator.textContent = '▲';

            // Show filters
            const filtersContainer = document.getElementById('filters-' + dashboardId);
            if (filtersContainer) {
                filtersContainer.style.display = 'flex';
                // Load filters if not already loaded
                if (filtersContainer.children.length === 0) {
                    await loadDashboardFilters(dashboardId, filtersContainer);
                }
            }

            // Show charts container and add active class
            chartsContainer.style.display = 'grid';
            chartsContainer.classList.add('active');

            // Load charts if not already loaded
            if (chartsContainer.children.length === 0) {
                console.log('>>> Loading charts for:', dashboardId);
                await loadDashboardCharts(dashboardId, chartsContainer);
            } else {
                console.log('>>> Charts already loaded (', chartsContainer.children.length, 'children)');
            }
        } else {
            // Collapse
            console.log('>>> COLLAPSING dashboard:', dashboardId);
            dashboardCard.classList.remove('expanded');
            expandIndicator.textContent = '▼';

            // Hide filters
            const filtersContainer = document.getElementById('filters-' + dashboardId);
            if (filtersContainer) {
                filtersContainer.style.display = 'none';
            }

            // Hide charts container
            chartsContainer.style.display = 'none';
            chartsContainer.classList.remove('active');
        }
    } finally {
        // Release lock after a short delay
        setTimeout(() => {
            toggleLock.delete(dashboardId);
            console.log('>>> Toggle lock released for:', dashboardId);
        }, 300);
    }
}

// Load charts for a specific dashboard
async function loadDashboardCharts(dashboardId, container, filters = {}) {
    console.log('loadDashboardCharts called for:', dashboardId, 'with filters:', filters);

    try {
        const response = await fetch('/api/dashboards');
        const data = await response.json();

        const dashboard = data.dashboards.find(d => d.id === dashboardId);
        if (!dashboard || !dashboard.charts) {
            console.log('No dashboard or charts found for:', dashboardId);
            container.innerHTML = '<p style="color: #888;">No charts configured for this dashboard</p>';
            return;
        }

        console.log('Found dashboard with', dashboard.charts.length, 'charts');

        // Show loading state
        container.innerHTML = '<p style="color: #888;">⏳ Loading charts...</p>';

        // Wait a moment for loading state to be visible
        await new Promise(resolve => setTimeout(resolve, 100));

        // Clear container before adding charts
        container.innerHTML = '';

        // Render each chart sequentially to avoid overwhelming the server
        let chartsRendered = 0;
        for (const chartConfig of dashboard.charts) {
            await renderDashboardChart(chartConfig, container, filters);
            chartsRendered++;
        }

        console.log('Finished rendering', chartsRendered, 'charts. Container has', container.children.length, 'children');

        // Show message if no charts were rendered
        if (container.children.length === 0) {
            console.log('No children in container after rendering, showing empty state');
            container.innerHTML = `
                <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; text-align: center; color: #6b7280;">
                    <div style="font-size: 2em; margin-bottom: 10px;">📊</div>
                    <div style="font-weight: bold; margin-bottom: 5px;">No charts loaded</div>
                    <div style="font-size: 0.9em;">Chart configurations may need adjustment</div>
                </div>
            `;
        } else {
            console.log('Successfully loaded', container.children.length, 'chart elements');
        }

    } catch (error) {
        console.error('Error loading dashboard charts:', error);
        container.innerHTML = `<p style="color: #ef4444;">Error loading charts: ${error.message}</p>`;
    }
}

// Render a single chart from configuration
async function renderDashboardChart(chartConfig, container, filters = {}) {
    try {
        // Skip only calculation-based charts (not multi-metric)
        if (chartConfig.calculation) {
            console.log('Skipping calculation chart type:', chartConfig.id);
            const infoCard = document.createElement('div');
            infoCard.style.cssText = 'background: #fef3c7; padding: 15px; border-radius: 8px; border-left: 4px solid #f59e0b;';
            infoCard.innerHTML = `
                <div style="font-weight: bold; color: #92400e; margin-bottom: 5px;">⚠️ ${chartConfig.title}</div>
                <div style="font-size: 0.85em; color: #78350f;">Calculation-based chart - coming soon!</div>
            `;
            container.appendChild(infoCard);
            return;
        }

        // Validate required fields for multi-metric charts
        if (chartConfig.metrics && (!chartConfig.model || !chartConfig.x_axis)) {
            console.warn('Skipping multi-metric chart with missing config:', chartConfig.id, chartConfig);
            return;
        }

        // Validate required fields for standard charts
        if (!chartConfig.metrics && chartConfig.type !== 'metric' && chartConfig.type !== 'table' && (!chartConfig.model || !chartConfig.x_axis || !chartConfig.y_axis)) {
            console.warn('Skipping chart with missing config:', chartConfig.id, chartConfig);
            return;
        }

        // Validate metric charts
        if (chartConfig.type === 'metric' && (!chartConfig.model || !chartConfig.metric)) {
            console.warn('Skipping metric chart with missing config:', chartConfig.id);
            return;
        }

        // Create chart wrapper
        const chartWrapper = document.createElement('div');
        chartWrapper.style.cssText = 'background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);';

        // Chart title
        const title = document.createElement('h4');
        title.style.cssText = 'margin: 0 0 10px 0; color: #333; font-size: 1.1em;';
        title.textContent = chartConfig.title;
        chartWrapper.appendChild(title);

        // Chart description (if available)
        if (chartConfig.description) {
            const desc = document.createElement('p');
            desc.style.cssText = 'margin: 0 0 15px 0; color: #666; font-size: 0.85em;';
            desc.textContent = chartConfig.description;
            chartWrapper.appendChild(desc);
        }

        // Handle table type differently - no canvas needed
        if (chartConfig.type === 'table') {
            const tableContainer = document.createElement('div');
            tableContainer.style.cssText = 'max-height: 400px; overflow: auto;';
            chartWrapper.appendChild(tableContainer);
            container.appendChild(chartWrapper);
            await renderTableChart(tableContainer, chartConfig, filters);
            return;
        }

        // Canvas for chart
        const canvas = document.createElement('canvas');
        canvas.id = 'chart-' + chartConfig.id;
        canvas.style.maxHeight = '300px';
        chartWrapper.appendChild(canvas);

        // Add to container first
        container.appendChild(chartWrapper);

        // Handle metric type
        if (chartConfig.type === 'metric') {
            await renderMetricChart(canvas, chartConfig, filters);
            return;
        }

        // Build query payload
        const queryPayload = {
            table: chartConfig.model,
            type: chartConfig.type,
            x_axis: chartConfig.x_axis,
            filters: filters
        };

        // Handle multi-metric charts
        if (chartConfig.metrics) {
            queryPayload.metrics = chartConfig.metrics;
        } else {
            queryPayload.y_axis = chartConfig.y_axis;
            queryPayload.aggregation = chartConfig.aggregation || 'sum';
        }

        // Fetch data from API
        const queryResponse = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(queryPayload)
        });

        if (!queryResponse.ok) {
            throw new Error('Failed to fetch chart data');
        }

        const chartData = await queryResponse.json();

        // Validate response
        if (!chartData.labels) {
            throw new Error('Invalid chart data received');
        }

        // Prepare datasets
        let datasets;
        if (chartData.datasets) {
            // Multi-series chart
            const colorPalette = [
                { bg: 'rgba(102, 126, 234, 0.2)', border: 'rgba(102, 126, 234, 1)' },
                { bg: 'rgba(16, 185, 129, 0.2)', border: 'rgba(16, 185, 129, 1)' },
                { bg: 'rgba(245, 158, 11, 0.2)', border: 'rgba(245, 158, 11, 1)' },
                { bg: 'rgba(239, 68, 68, 0.2)', border: 'rgba(239, 68, 68, 1)' },
                { bg: 'rgba(139, 92, 246, 0.2)', border: 'rgba(139, 92, 246, 1)' }
            ];

            datasets = chartData.datasets.map((dataset, index) => {
                const color = colorPalette[index % colorPalette.length];
                return {
                    label: dataset.label,
                    data: dataset.data,
                    backgroundColor: color.bg,
                    borderColor: color.border,
                    borderWidth: 2,
                    tension: 0.4
                };
            });
        } else {
            // Single-series chart
            const colors = getChartColors(chartConfig, chartData.labels.length || 1);
            datasets = [{
                label: chartConfig.title,
                data: chartData.values,
                backgroundColor: colors.background,
                borderColor: colors.border,
                borderWidth: 2,
                tension: 0.4
            }];
        }

        // Check if there's any data
        const hasData = chartData.labels.length > 0 && datasets.some(ds => ds.data && ds.data.length > 0);

        // Determine actual chart type and options
        let actualChartType = chartConfig.type;
        let chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: ['pie', 'doughnut'].includes(chartConfig.type) || (chartData.datasets && chartData.datasets.length > 1),
                    labels: {
                        color: '#374151',  // Darker gray for better contrast
                        font: {
                            size: 12,
                            weight: '500'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#667eea',
                    borderWidth: 1
                }
            },
            scales: {}
        };

        // Handle stacked bar chart
        if (chartConfig.type === 'bar-stacked') {
            actualChartType = 'bar';
            chartOptions.scales = {
                x: {
                    stacked: true,
                    ticks: {
                        color: '#374151',
                        font: {
                            size: 11
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    ticks: {
                        color: '#374151',
                        font: {
                            size: 11
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            };
        } else if (['line', 'bar'].includes(chartConfig.type)) {
            chartOptions.scales = {
                x: {
                    ticks: {
                        color: '#374151',  // Darker text
                        font: {
                            size: 11
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#374151',  // Darker text
                        font: {
                            size: 11
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            };
        }

        // Create Chart.js chart
        new Chart(canvas, {
            type: actualChartType,
            data: {
                labels: chartData.labels,
                datasets: datasets
            },
            options: chartOptions
        });

        // Add "No data" overlay if chart is empty
        if (!hasData) {
            const noDataDiv = document.createElement('div');
            noDataDiv.style.cssText = 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; pointer-events: none;';
            noDataDiv.innerHTML = `
                <div style="font-size: 1.2em; font-weight: 500; color: #9ca3af;">No data available</div>
                <div style="font-size: 0.85em; color: #d1d5db; margin-top: 5px;">Try adjusting your filters</div>
            `;
            // Make canvas wrapper position relative
            canvas.parentElement.style.position = 'relative';
            canvas.parentElement.appendChild(noDataDiv);
        }

    } catch (error) {
        console.error('Error rendering chart:', chartConfig.id, error);
        // Show error in the container
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = 'background: #fee; padding: 15px; border-radius: 8px; color: #c00; margin-bottom: 15px;';
        errorDiv.textContent = `Error loading ${chartConfig.title}: ${error.message}`;
        container.appendChild(errorDiv);
    }
}

// Render metric chart (single KPI value)
async function renderMetricChart(canvas, chartConfig, filters = {}) {
    try {
        // Determine which field to query
        const metricField = chartConfig.metric || chartConfig.y_axis;
        if (!metricField) {
            throw new Error('No metric field specified');
        }

        // For metrics, query the data with filters
        const queryResponse = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                table: chartConfig.model,
                x_axis: metricField,
                y_axis: metricField,
                aggregation: chartConfig.aggregation || 'sum',
                filters: filters  // Pass filters to backend
            })
        });

        if (!queryResponse.ok) {
            throw new Error('Failed to fetch metric data');
        }

        const chartData = await queryResponse.json();

        // Check if we have data
        const hasData = chartData.values && chartData.values.length > 0;
        const value = hasData ? chartData.values.reduce((a, b) => a + b, 0) : 0;

        // Hide canvas and show metric value instead
        canvas.style.display = 'none';
        const metricDiv = document.createElement('div');
        metricDiv.style.cssText = 'text-align: center; padding: 30px 0; position: relative;';

        if (hasData) {
            metricDiv.innerHTML = `
                <div style="font-size: 3em; font-weight: bold; color: #667eea;">${formatMetricValue(value)}</div>
                <div style="font-size: 0.9em; color: #888; margin-top: 5px;">${chartConfig.aggregation?.toUpperCase() || 'TOTAL'}</div>
            `;
        } else {
            // Show empty state for metrics
            metricDiv.innerHTML = `
                <div style="font-size: 2.5em; font-weight: bold; color: #d1d5db;">—</div>
                <div style="font-size: 0.85em; color: #9ca3af; margin-top: 8px;">No data available</div>
                <div style="font-size: 0.75em; color: #d1d5db; margin-top: 4px;">Try adjusting your filters</div>
            `;
        }
        canvas.parentElement.appendChild(metricDiv);

    } catch (error) {
        console.error('Error rendering metric:', error);
        canvas.style.display = 'none';
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = 'text-align: center; padding: 20px; color: #ef4444;';
        errorDiv.textContent = `Error loading metric: ${error.message}`;
        canvas.parentElement.appendChild(errorDiv);
    }
}

// Render table chart type
async function renderTableChart(container, chartConfig, filters = {}) {
    try {
        // Fetch data from API
        const queryResponse = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                table: chartConfig.model,
                x_axis: chartConfig.x_axis,
                y_axis: chartConfig.y_axis,
                aggregation: chartConfig.aggregation || 'sum',
                filters: filters
            })
        });

        if (!queryResponse.ok) {
            throw new Error('Failed to fetch table data');
        }

        const chartData = await queryResponse.json();

        // Check if we have data
        const hasData = chartData.labels && chartData.labels.length > 0;

        if (!hasData) {
            container.innerHTML = '<div style="padding: 30px; text-align: center; color: #888;">No data available</div>';
            return;
        }

        // Create HTML table
        let tableHTML = '<table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">';
        tableHTML += '<thead><tr>';
        tableHTML += `<th style="padding: 0.75rem; text-align: left; border-bottom: 2px solid var(--color-border); background: var(--color-bg-secondary); font-weight: 600;">${chartConfig.x_axis}</th>`;
        tableHTML += `<th style="padding: 0.75rem; text-align: right; border-bottom: 2px solid var(--color-border); background: var(--color-bg-secondary); font-weight: 600;">${chartConfig.aggregation?.toUpperCase() || 'SUM'}(${chartConfig.y_axis})</th>`;
        tableHTML += '</tr></thead><tbody>';

        for (let i = 0; i < chartData.labels.length; i++) {
            const rowStyle = i % 2 === 0 ? 'background: #f9fafb;' : '';
            tableHTML += `<tr style="${rowStyle}">`;
            tableHTML += `<td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">${chartData.labels[i]}</td>`;
            tableHTML += `<td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-border); font-weight: 500;">${chartData.values[i]}</td>`;
            tableHTML += '</tr>';
        }

        tableHTML += '</tbody></table>';
        container.innerHTML = tableHTML;

    } catch (error) {
        console.error('Error rendering table:', error);
        container.innerHTML = `<div style="padding: 20px; color: #ef4444; text-align: center;">Error loading table: ${error.message}</div>`;
    }
}

// Format metric values
function formatMetricValue(value) {
    if (value >= 1000000) {
        return (value / 1000000).toFixed(1) + 'M';
    } else if (value >= 1000) {
        return (value / 1000).toFixed(1) + 'K';
    } else if (value % 1 !== 0) {
        return value.toFixed(2);
    }
    return value.toString();
}

// Get colors for charts based on config
function getChartColors(chartConfig, dataLength) {
    const colorSchemes = {
        blue: '#3b82f6',
        green: '#10b981',
        red: '#ef4444',
        purple: '#8b5cf6',
        orange: '#f59e0b',
        teal: '#14b8a6'
    };

    // Use custom colors if provided
    if (chartConfig.colors && chartConfig.colors.length > 0) {
        return {
            background: chartConfig.colors.map(c => c + 'cc'),
            border: chartConfig.colors
        };
    }

    // Use color scheme
    const baseColor = colorSchemes[chartConfig.color_scheme] || colorSchemes.blue;

    if (['pie', 'doughnut'].includes(chartConfig.type)) {
        // Generate multiple colors for pie/doughnut
        const colors = [];
        for (let i = 0; i < dataLength; i++) {
            const hue = (i * 360 / dataLength) % 360;
            colors.push(`hsl(${hue}, 70%, 60%)`);
        }
        return {
            background: colors.map(c => c.replace('60%', '60%, 0.8')),
            border: colors
        };
    }

    // Single color for bar/line charts
    return {
        background: baseColor + 'cc',
        border: baseColor
    };
}

// Load all charts catalog
async function loadAllCharts() {
    try {
        const response = await fetch('/api/dashboards');
        const data = await response.json();

        const chartsList = document.getElementById('all-charts-list');

        if (data.dashboards.length === 0) {
            chartsList.innerHTML = '<p style="color: #888;">No charts available</p>';
            return;
        }

        // Clear the list
        chartsList.innerHTML = '';

        // Collect all charts from all dashboards
        const allCharts = [];
        data.dashboards.forEach(dashboard => {
            if (dashboard.charts) {
                dashboard.charts.forEach(chart => {
                    allCharts.push({
                        ...chart,
                        dashboardName: dashboard.name,
                        dashboardId: dashboard.id
                    });
                });
            }
        });

        // Display each chart as a card
        allCharts.forEach(chart => {
            const card = document.createElement('div');
            card.className = 'chart-item-card';

            // Chart type icon
            const typeIcons = {
                line: '📈',
                bar: '📊',
                pie: '🥧',
                doughnut: '🍩',
                metric: '🔢'
            };

            card.innerHTML = `
                <div class="chart-item-icon">${typeIcons[chart.type] || '📊'}</div>
                <div class="chart-item-title">${chart.title}</div>
                <div class="chart-item-dashboard">${chart.dashboardName}</div>
                <div class="chart-item-badges">
                    <span class="chart-badge chart-badge-type">${chart.type}</span>
                    <span class="chart-badge chart-badge-model">${chart.model}</span>
                </div>
            `;

            // Click to show chart in modal
            card.onclick = () => {
                showChartModal(chart);
            };

            chartsList.appendChild(card);
        });

        // Show total count
        const countDiv = document.createElement('div');
        countDiv.className = 'charts-count';
        countDiv.textContent = `📊 Total: ${allCharts.length} charts across ${data.dashboards.length} dashboards`;
        chartsList.appendChild(countDiv);

    } catch (error) {
        console.error('Error loading charts:', error);
        document.getElementById('all-charts-list').innerHTML = '<p style="color: #ef4444;">Failed to load charts</p>';
    }
}

function toggleExpand(event, slug) {
    event.stopPropagation();
    const card = document.getElementById(`card-${slug}`);
    card.classList.toggle('expanded');
}

function viewDashboard(slug) {
    // In a real implementation, this would navigate to a detail page
    alert(`Navigating to dashboard: /dashboards/${slug}\n\nIn a full implementation, this would show detailed dashboard analytics, usage metrics, and lineage visualization.`);
}

// Chart Builder Functions
let currentChart = null;

async function loadTableColumns() {
    const table = document.getElementById('chartTable').value;
    const chartType = document.getElementById('chartType').value;
    if (!table) return;

    try {
        const response = await fetch(`/api/tables/${table}/columns`);
        const data = await response.json();

        // Handle table type separately
        if (chartType === 'table') {
            loadTableColumnsForBuilder();
            return;
        }

        const xAxis = document.getElementById('chartXAxis');
        const yAxis = document.getElementById('chartYAxis');

        // Clear existing options
        xAxis.innerHTML = '<option value="">Select column...</option>';
        yAxis.innerHTML = '<option value="">Select column...</option>';

        // Add columns
        data.columns.forEach(col => {
            const optionX = document.createElement('option');
            optionX.value = col.name;
            optionX.textContent = `${col.name} (${col.type})`;
            xAxis.appendChild(optionX);

            const optionY = document.createElement('option');
            optionY.value = col.name;
            optionY.textContent = `${col.name} (${col.type})`;
            yAxis.appendChild(optionY);
        });
    } catch (error) {
        console.error('Error loading columns:', error);
    }
}

// Global variable to store table columns configuration
let tableColumns = [];

function toggleChartBuilder() {
    const builderSection = document.getElementById('chart-builder-section');
    const btn = document.getElementById('toggleChartBuilderBtn');

    if (builderSection.style.display === 'none') {
        builderSection.style.display = 'block';
        btn.textContent = '✖ Close Chart Builder';
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-secondary');
        // Scroll to chart builder
        builderSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
        builderSection.style.display = 'none';
        btn.textContent = '✨ Create New Chart';
        btn.classList.remove('btn-secondary');
        btn.classList.add('btn-primary');
    }
}

// Handle chart type change to show/hide appropriate fields
function handleChartTypeChange() {
    const chartType = document.getElementById('chartType').value;
    const regularFields = document.getElementById('regularChartFields');
    const tableFields = document.getElementById('tableChartFields');

    if (chartType === 'table') {
        regularFields.style.display = 'none';
        tableFields.style.display = 'block';
        // Load table columns if table is selected
        const table = document.getElementById('chartTable').value;
        if (table) {
            loadTableColumnsForBuilder();
        }
    } else {
        regularFields.style.display = 'block';
        tableFields.style.display = 'none';
    }
}

// Load available columns for table builder
async function loadTableColumnsForBuilder() {
    const table = document.getElementById('chartTable').value;
    if (!table) return;

    try {
        const response = await fetch(`/api/tables/${table}/columns`);
        const data = await response.json();
        const container = document.getElementById('tableColumnsContainer');

        // Clear and reset
        tableColumns = [];
        container.innerHTML = '<p style="color: var(--color-text-muted); font-size: 0.875rem; padding: 1rem;">Click "+ Add Column" to add columns to your table</p>';
    } catch (error) {
        console.error('Error loading columns:', error);
    }
}

// Add a column configuration to the table
function addTableColumn() {
    const table = document.getElementById('chartTable').value;
    if (!table) {
        document.getElementById('chartError').style.display = 'block';
        document.getElementById('chartError').textContent = 'Please select a data source first';
        return;
    }

    // Fetch columns and show modal
    fetch(`/api/tables/${table}/columns`)
        .then(response => response.json())
        .then(data => {
            const columnId = 'col_' + Date.now();
            const column = {
                id: columnId,
                field: '',
                function: 'none',
                label: ''
            };

            tableColumns.push(column);
            renderTableColumns(data.columns);
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('chartError').style.display = 'block';
            document.getElementById('chartError').textContent = 'Error loading columns';
        });
}

// Render table columns configuration UI
function renderTableColumns(availableColumns) {
    const container = document.getElementById('tableColumnsContainer');

    if (tableColumns.length === 0) {
        container.innerHTML = '<p style="color: var(--color-text-muted); font-size: 0.875rem; padding: 1rem;">Click "+ Add Column" to add columns to your table</p>';
        return;
    }

    let html = '';
    tableColumns.forEach((col, index) => {
        html += `
            <div style="background: var(--color-bg-primary); padding: 0.75rem; margin-bottom: 0.5rem; border-radius: var(--radius-md); border: 1px solid var(--color-border);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <strong style="font-size: 0.875rem; color: var(--color-text-primary);">Column ${index + 1}</strong>
                    <button onclick="removeTableColumn('${col.id}')" style="background: none; border: none; color: var(--color-error); cursor: pointer; font-size: 1.2rem; padding: 0; margin-left: auto;">×</button>
                </div>
                <div style="margin-bottom: 0.5rem;">
                    <label style="display: block; font-size: 0.75rem; margin-bottom: 0.25rem; color: var(--color-text-muted);">Field</label>
                    <select onchange="updateTableColumn('${col.id}', 'field', this.value)" class="input" style="font-size: 0.875rem; padding: 0.5rem;">
                        <option value="">Select field...</option>
                        <option value="__custom__" ${col.field === '__custom__' ? 'selected' : ''}>Custom SQL Expression</option>
                        ${availableColumns.map(c => `<option value="${c}" ${col.field === c ? 'selected' : ''}>${c}</option>`).join('')}
                    </select>
                </div>
                ${col.field === '__custom__' ? `
                <div style="margin-bottom: 0.5rem;">
                    <label style="display: block; font-size: 0.75rem; margin-bottom: 0.25rem; color: var(--color-text-muted);">SQL Expression</label>
                    <input type="text" value="${col.sqlExpression || ''}" onchange="updateTableColumn('${col.id}', 'sqlExpression', this.value)" placeholder="e.g., quantity * price" class="input" style="font-size: 0.875rem; padding: 0.5rem; font-family: monospace;">
                    <div style="font-size: 0.7rem; color: var(--color-text-muted); margin-top: 0.25rem;">Use field names and SQL operators (+, -, *, /, CASE, etc.)</div>
                </div>
                ` : ''}
                ${col.field !== '__custom__' ? `
                <div style="margin-bottom: 0.5rem;">
                    <label style="display: block; font-size: 0.75rem; margin-bottom: 0.25rem; color: var(--color-text-muted);">Aggregation Function</label>
                    <select onchange="updateTableColumn('${col.id}', 'function', this.value)" class="input" style="font-size: 0.875rem; padding: 0.5rem;">
                        <option value="none" ${col.function === 'none' ? 'selected' : ''}>None (Show values)</option>
                        <option value="sum" ${col.function === 'sum' ? 'selected' : ''}>SUM</option>
                        <option value="avg" ${col.function === 'avg' ? 'selected' : ''}>AVG</option>
                        <option value="count" ${col.function === 'count' ? 'selected' : ''}>COUNT</option>
                        <option value="min" ${col.function === 'min' ? 'selected' : ''}>MIN</option>
                        <option value="max" ${col.function === 'max' ? 'selected' : ''}>MAX</option>
                    </select>
                </div>
                ` : ''}
                <div>
                    <label style="display: block; font-size: 0.75rem; margin-bottom: 0.25rem; color: var(--color-text-muted);">Column Label</label>
                    <input type="text" value="${col.label}" onchange="updateTableColumn('${col.id}', 'label', this.value)" placeholder="Auto-generated" class="input" style="font-size: 0.875rem; padding: 0.5rem;">
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Update a table column configuration
function updateTableColumn(columnId, field, value) {
    const column = tableColumns.find(c => c.id === columnId);
    if (column) {
        column[field] = value;
        // If field selection changes, re-render to show/hide custom SQL or aggregation
        if (field === 'field') {
            const table = document.getElementById('chartTable').value;
            fetch(`/api/tables/${table}/columns`)
                .then(response => response.json())
                .then(data => renderTableColumns(data.columns))
                .catch(error => console.error('Error:', error));
        }
    }
}

// Remove a table column
function removeTableColumn(columnId) {
    tableColumns = tableColumns.filter(c => c.id !== columnId);
    const table = document.getElementById('chartTable').value;
    fetch(`/api/tables/${table}/columns`)
        .then(response => response.json())
        .then(data => renderTableColumns(data.columns))
        .catch(error => console.error('Error:', error));
}

async function createChart() {
    const title = document.getElementById('chartTitle').value || 'Chart';
    const table = document.getElementById('chartTable').value;
    const chartType = document.getElementById('chartType').value;
    const xAxis = document.getElementById('chartXAxis').value;
    const yAxis = document.getElementById('chartYAxis').value;
    const aggregation = document.getElementById('chartAggregation').value;

    // Validation
    if (!table || !xAxis || !yAxis) {
        document.getElementById('chartError').style.display = 'block';
        document.getElementById('chartError').textContent = 'Please select table, X-axis, and Y-axis';
        return;
    }

    document.getElementById('chartError').style.display = 'none';

    try {
        // Query data
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ table, x_axis: xAxis, y_axis: yAxis, aggregation })
        });

        const data = await response.json();

        // Hide all preview containers
        document.getElementById('chartPlaceholder').style.display = 'none';
        document.getElementById('chartCanvas').style.display = 'none';
        document.getElementById('chartTableContainer').style.display = 'none';

        // Handle table chart type
        if (chartType === 'table') {
            const tableContainer = document.getElementById('chartTableContainer');
            tableContainer.style.display = 'block';

            // Create HTML table
            let tableHTML = '<table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">';
            tableHTML += '<thead><tr>';
            tableHTML += `<th style="padding: 0.75rem; text-align: left; border-bottom: 2px solid var(--color-border); background: var(--color-bg-secondary); font-weight: 600;">${xAxis}</th>`;
            tableHTML += `<th style="padding: 0.75rem; text-align: right; border-bottom: 2px solid var(--color-border); background: var(--color-bg-secondary); font-weight: 600;">${aggregation.toUpperCase()}(${yAxis})</th>`;
            tableHTML += '</tr></thead><tbody>';

            for (let i = 0; i < data.labels.length; i++) {
                tableHTML += '<tr>';
                tableHTML += `<td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">${data.labels[i]}</td>`;
                tableHTML += `<td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-border); font-weight: 500;">${data.values[i]}</td>`;
                tableHTML += '</tr>';
            }

            tableHTML += '</tbody></table>';
            tableContainer.innerHTML = tableHTML;
        } else {
            // Show canvas for chart types
            document.getElementById('chartCanvas').style.display = 'block';

            // Destroy existing chart if any
            if (currentChart) {
                currentChart.destroy();
            }

            // Determine actual Chart.js type and options
            let actualChartType = chartType;
            let chartOptions = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: title,
                        font: { size: 18, weight: 'bold' }
                    },
                    legend: {
                        display: chartType === 'pie' || chartType === 'doughnut'
                    }
                },
                scales: {}
            };

            // Handle stacked bar chart
            if (chartType === 'bar-stacked') {
                actualChartType = 'bar';
                chartOptions.scales = {
                    x: { stacked: true },
                    y: { stacked: true, beginAtZero: true }
                };
            } else if (chartType !== 'pie' && chartType !== 'doughnut') {
                chartOptions.scales = {
                    y: { beginAtZero: true }
                };
            }

            // Create new chart
            const ctx = document.getElementById('chartCanvas').getContext('2d');
            currentChart = new Chart(ctx, {
                type: actualChartType,
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: `${aggregation.toUpperCase()}(${yAxis})`,
                        data: data.values,
                        backgroundColor: [
                            'rgba(102, 126, 234, 0.8)',
                            'rgba(16, 185, 129, 0.8)',
                            'rgba(245, 158, 11, 0.8)',
                            'rgba(239, 68, 68, 0.8)',
                            'rgba(139, 92, 246, 0.8)',
                            'rgba(236, 72, 153, 0.8)',
                        ],
                        borderColor: 'rgba(102, 126, 234, 1)',
                        borderWidth: 2
                    }]
                },
                options: chartOptions
            });
        }

        // Enable save button
        document.getElementById('saveChartBtn').disabled = false;

    } catch (error) {
        console.error('Error creating chart:', error);
        document.getElementById('chartError').style.display = 'block';
        document.getElementById('chartError').textContent = 'Error creating chart: ' + error.message;
    }
}

async function saveChart() {
    const title = document.getElementById('chartTitle').value || 'Chart';
    const table = document.getElementById('chartTable').value;
    let chartType = document.getElementById('chartType').value;
    const xAxis = document.getElementById('chartXAxis').value;
    const yAxis = document.getElementById('chartYAxis').value;
    const aggregation = document.getElementById('chartAggregation').value;

    // Validation
    if (!table || !xAxis || !yAxis) {
        alert('Please fill in all required fields before saving');
        return;
    }

    const saveBtn = document.getElementById('saveChartBtn');
    const originalText = saveBtn.textContent;
    saveBtn.textContent = '💾 Saving...';
    saveBtn.disabled = true;

    try {
        // Generate chart ID
        const chartId = `chart_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

        // Convert bar-stacked to bar for storage (with metadata to indicate stacking)
        let actualType = chartType;
        if (chartType === 'bar-stacked') {
            actualType = 'bar';
        }

        // Save chart configuration
        const response = await fetch('/api/charts/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: chartId,
                title: title,
                type: chartType,  // Save the original type
                model: table,
                x_axis: xAxis,
                y_axis: yAxis,
                aggregation: aggregation
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Server error: ${response.status}`);
        }

        const result = await response.json();

        if (result.success) {
            saveBtn.textContent = '✓ Saved!';
            saveBtn.style.background = 'var(--color-success)';

            // Show success modal with options
            showChartSavedModal(result.dashboard_id, chartId, title);

            setTimeout(() => {
                saveBtn.textContent = originalText;
                saveBtn.style.background = '';
                saveBtn.disabled = false;
            }, 3000);
        } else {
            throw new Error(result.message || 'Failed to save chart');
        }
    } catch (error) {
        console.error('Error saving chart:', error);
        saveBtn.textContent = '❌ Failed';
        saveBtn.style.background = 'var(--color-error)';

        setTimeout(() => {
            saveBtn.textContent = originalText;
            saveBtn.style.background = '';
            saveBtn.disabled = false;
        }, 3000);

        alert('Failed to save chart: ' + error.message);
    }
}

function showChartSavedModal(dashboardId, chartId, title) {
    const modal = document.createElement('div');
    modal.className = 'modal active';
    modal.id = 'chart-saved-modal';
    modal.innerHTML = `
        <div class="modal-overlay" onclick="closeChartSavedModal()"></div>
        <div class="modal-container" style="max-width: 500px;">
            <div class="modal-header">
                <h2>✓ Chart Saved Successfully!</h2>
                <button class="modal-close" onclick="closeChartSavedModal()">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                </button>
            </div>
            <div class="modal-body">
                <p style="color: var(--color-text-secondary); margin-bottom: 1.5rem;">
                    Your chart "<strong>${title}</strong>" has been saved to the "Custom Charts" dashboard.
                </p>
                <div style="display: flex; gap: 0.75rem; flex-direction: column;">
                    <button class="btn btn-primary" style="width: 100%;" onclick="viewChartInDashboard('${dashboardId}'); closeChartSavedModal();">
                        📊 View in Dashboard
                    </button>
                    <button class="btn btn-secondary" style="width: 100%;" onclick="closeChartSavedModal();">
                        Continue Creating Charts
                    </button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

function closeChartSavedModal() {
    const modal = document.getElementById('chart-saved-modal');
    if (modal) {
        modal.remove();
    }
}

async function viewChartInDashboard(dashboardId) {
    // Switch to dashboards tab
    switchTab('dashboards');

    // Wait for dashboards to load
    await new Promise(resolve => setTimeout(resolve, 500));

    // Expand the dashboard
    const dashboardCard = document.getElementById('dashboard-' + dashboardId);
    if (dashboardCard && !dashboardCard.classList.contains('expanded')) {
        await toggleDashboard(dashboardId);
    }

    // Scroll to dashboard
    if (dashboardCard) {
        dashboardCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Runs Management
async function loadRuns() {
    try {
        const response = await fetch('/api/runs');
        const data = await response.json();
        allRuns = data.runs;

        displayRuns();

    } catch (error) {
        console.error('Error loading runs:', error);
        const runsList = document.getElementById('runs-list');
        runsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">❌</div>
                <h3>Failed to Load Runs</h3>
                <p>There was an error loading the run history. Please try refreshing.</p>
            </div>
        `;
    }
}

function displayRuns() {
    const runsList = document.getElementById('runs-list');

    if (allRuns.length === 0) {
        runsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📊</div>
                <h3>No Runs Yet</h3>
                <p>Click "Run Transformations" in the Models tab to execute your first pipeline.</p>
                <div class="empty-state-action">
                    <button class="empty-state-btn" onclick="switchTab('models'); setTimeout(() => document.getElementById('runBtn').focus(), 100)">
                        ▶️ Run Your First Transformation
                    </button>
                </div>
            </div>
        `;
        return;
    }

    // Filter runs based on current filter
    let filteredRuns = allRuns;
    if (currentFilter !== 'all') {
        filteredRuns = allRuns.filter(run => {
            const status = getRunStatus(run);
            return status === currentFilter;
        });
    }

    if (filteredRuns.length === 0) {
        runsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <h3>No Matching Runs</h3>
                <p>No runs match the current filter. Try selecting a different filter.</p>
            </div>
        `;
        return;
    }

    runsList.innerHTML = filteredRuns.map(run => {
        const timestamp = new Date(run.timestamp).toLocaleString();
        const successRate = run.summary.total_models > 0
            ? ((run.summary.successes / run.summary.total_models) * 100).toFixed(0)
            : 0;

        const status = getRunStatus(run);
        const statusBadge = getStatusBadge(status);

        return `
            <div class="run-card ${status}">
                <div class="run-header" onclick="toggleRunDetails('${run.run_id}')">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span class="expand-icon" id="expand-run-${run.run_id}">▶</span>
                        <span class="run-id">${run.run_id}</span>
                        ${statusBadge}
                    </div>
                    <span class="run-time">${timestamp}</span>
                </div>
                <div class="run-stats">
                    <span class="run-stat-item stat-success">✓ ${run.summary.successes}</span>
                    <span class="run-stat-item stat-failure">✗ ${run.summary.failures}</span>
                    <span class="run-stat-item stat-neutral">⏱️ ${run.summary.total_execution_time.toFixed(2)}s</span>
                    <span class="run-stat-item stat-neutral">📊 ${successRate}% success</span>
                </div>
                <div class="run-details" id="run-details-${run.run_id}" style="display: none;">
                    <div class="run-details-actions">
                        <input type="text" class="log-search" id="search-${run.run_id}"
                               placeholder="Search logs..." onkeyup="searchRunLogs('${run.run_id}')">
                        <button class="action-btn-small" onclick="printRunLogs('${run.run_id}')">🖨️ Print</button>
                        <button class="action-btn-small" onclick="saveRunLogs('${run.run_id}')">💾 Save</button>
                    </div>
                    <div class="run-logs" id="logs-${run.run_id}">
                        <div class="loading">Loading logs...</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function getRunStatus(run) {
    if (run.summary.failures === 0) return 'success';
    if (run.summary.successes === 0) return 'failed';
    return 'partial';
}

function getStatusBadge(status) {
    const badges = {
        'success': '<span class="run-status-badge success">✓ Success</span>',
        'failed': '<span class="run-status-badge failed">✗ Failed</span>',
        'partial': '<span class="run-status-badge partial">⚠️ Partial</span>'
    };
    return badges[status] || '';
}

function filterRuns(filter) {
    currentFilter = filter;

    // Update active filter button
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    // Re-display runs with filter
    displayRuns();
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

// Toggle run details expansion (inline)
let expandedRuns = new Set();

async function toggleRunDetails(runId) {
    const detailsDiv = document.getElementById(`run-details-${runId}`);
    const expandIcon = document.getElementById(`expand-run-${runId}`);
    const logsDiv = document.getElementById(`logs-${runId}`);

    if (expandedRuns.has(runId)) {
        // Collapse
        detailsDiv.style.display = 'none';
        expandIcon.textContent = '▶';
        expandedRuns.delete(runId);
    } else {
        // Expand
        detailsDiv.style.display = 'block';
        expandIcon.textContent = '▼';
        expandedRuns.add(runId);

        // Load logs if not already loaded
        if (logsDiv.innerHTML.includes('Loading logs')) {
            await loadRunLogsInline(runId);
        }
    }
}

async function loadRunLogsInline(runId) {
    const logsDiv = document.getElementById(`logs-${runId}`);

    try {
        const response = await fetch(`/api/runs/${runId}`);
        const data = await response.json();

        const logs = data.logs.map(log => {
            const levelMatch = log.match(/\[(INFO|SUCCESS|ERROR|WARNING)\]/);
            const level = levelMatch ? levelMatch[1] : 'INFO';
            return `<div class="log-entry log-level-${level}" data-log="${escapeHtml(log)}">${escapeHtml(log)}</div>`;
        }).join('');

        logsDiv.innerHTML = logs || '<div class="empty-logs">No logs available</div>';
    } catch (error) {
        console.error('Error loading run logs:', error);
        logsDiv.innerHTML = '<div class="error-logs">Failed to load logs</div>';
    }
}

// Search run logs
function searchRunLogs(runId) {
    const searchInput = document.getElementById(`search-${runId}`);
    const query = searchInput.value.toLowerCase();
    const logsDiv = document.getElementById(`logs-${runId}`);
    const logEntries = logsDiv.querySelectorAll('.log-entry');

    logEntries.forEach(entry => {
        const text = entry.textContent.toLowerCase();
        if (!query || text.includes(query)) {
            entry.style.display = '';
            if (query) {
                // Highlight matched text
                const originalText = entry.getAttribute('data-log');
                const regex = new RegExp(`(${query})`, 'gi');
                entry.innerHTML = originalText.replace(regex, '<mark>$1</mark>');
            }
        } else {
            entry.style.display = 'none';
        }
    });
}

// Print run logs
function printRunLogs(runId) {
    const logsDiv = document.getElementById(`logs-${runId}`);
    const logEntries = Array.from(logsDiv.querySelectorAll('.log-entry:not([style*="display: none"])'));

    const printWindow = window.open('', '', 'width=800,height=600');
    printWindow.document.write(`
        <html>
        <head>
            <title>Run Logs - ${runId}</title>
            <style>
                body { font-family: 'Courier New', monospace; padding: 20px; }
                h1 { font-size: 18px; margin-bottom: 20px; }
                .log-entry { padding: 4px 0; white-space: pre-wrap; }
                .log-level-ERROR { color: #dc2626; }
                .log-level-SUCCESS { color: #16a34a; }
                .log-level-WARNING { color: #ea580c; }
                @media print {
                    body { margin: 0; padding: 15px; }
                }
            </style>
        </head>
        <body>
            <h1>Run Logs - ${runId}</h1>
            ${logEntries.map(e => `<div class="log-entry ${e.className}">${e.textContent}</div>`).join('')}
        </body>
        </html>
    `);
    printWindow.document.close();
    printWindow.print();
}

// Save run logs
function saveRunLogs(runId) {
    const logsDiv = document.getElementById(`logs-${runId}`);
    const logEntries = Array.from(logsDiv.querySelectorAll('.log-entry:not([style*="display: none"])'));
    const logsText = logEntries.map(e => e.textContent).join('\n');

    const blob = new Blob([logsText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${runId}-logs.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Run Transformations
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

// Global variable to store current chart context
let currentChartContext = null;

// Show chart in modal
async function showChartModal(chart) {
    // Store chart context for "Go to Dashboard" button
    currentChartContext = chart;

    // Set modal title
    document.getElementById('chartModalTitle').textContent = chart.title;

    // Clear and show modal
    const modalBody = document.getElementById('chartModalBody');
    modalBody.innerHTML = '<p style="text-align: center; color: #888;">⏳ Loading chart...</p>';
    document.getElementById('chartModal').style.display = 'block';

    try {
        // Create a temporary container for the chart
        const chartWrapper = document.createElement('div');
        chartWrapper.style.cssText = 'background: white; padding: 20px; border-radius: 12px;';

        // Add chart description
        if (chart.description) {
            const desc = document.createElement('p');
            desc.style.cssText = 'margin: 0 0 20px 0; color: #666; text-align: center;';
            desc.textContent = chart.description;
            chartWrapper.appendChild(desc);
        }

        // Add chart info badges
        const infoBadges = document.createElement('div');
        infoBadges.style.cssText = 'display: flex; gap: 10px; justify-content: center; margin-bottom: 20px; flex-wrap: wrap;';
        infoBadges.innerHTML = `
            <span style="background: #e0e7ff; color: #667eea; padding: 6px 12px; border-radius: 6px; font-size: 0.9em;">📊 ${chart.type}</span>
            <span style="background: #e0f2fe; color: #0284c7; padding: 6px 12px; border-radius: 6px; font-size: 0.9em;">📋 ${chart.model}</span>
            <span style="background: #f0fdf4; color: #16a34a; padding: 6px 12px; border-radius: 6px; font-size: 0.9em;">🔢 ${chart.aggregation || 'sum'}</span>
            <span style="background: #fef3c7; color: #d97706; padding: 6px 12px; border-radius: 6px; font-size: 0.9em;">📂 ${chart.dashboardName}</span>
        `;
        chartWrapper.appendChild(infoBadges);

        // Canvas for chart
        const canvas = document.createElement('canvas');
        canvas.id = 'modal-chart-canvas';
        canvas.style.cssText = 'max-height: 500px; width: 100%;';
        chartWrapper.appendChild(canvas);

        // Clear modal and add wrapper
        modalBody.innerHTML = '';
        modalBody.appendChild(chartWrapper);

        // Render the chart based on type
        if (chart.type === 'metric') {
            await renderMetricChart(canvas, chart);
        } else {
            // Skip only calculation-based charts
            if (chart.calculation) {
                throw new Error('Calculation-based charts not yet implemented');
            }

            // Build query payload
            const queryPayload = {
                table: chart.model,
                type: chart.type,
                x_axis: chart.x_axis
            };

            // Handle multi-metric charts
            if (chart.metrics) {
                queryPayload.metrics = chart.metrics;
            } else {
                queryPayload.y_axis = chart.y_axis;
                queryPayload.aggregation = chart.aggregation || 'sum';
            }

            // Fetch data
            const queryResponse = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(queryPayload)
            });

            if (!queryResponse.ok) {
                throw new Error('Failed to fetch chart data');
            }

            const chartData = await queryResponse.json();

            if (!chartData.labels) {
                throw new Error('Invalid chart data received');
            }

            // Prepare datasets
            let datasets;
            if (chartData.datasets) {
                // Multi-series chart
                const colorPalette = [
                    { bg: 'rgba(102, 126, 234, 0.2)', border: 'rgba(102, 126, 234, 1)' },
                    { bg: 'rgba(16, 185, 129, 0.2)', border: 'rgba(16, 185, 129, 1)' },
                    { bg: 'rgba(245, 158, 11, 0.2)', border: 'rgba(245, 158, 11, 1)' },
                    { bg: 'rgba(239, 68, 68, 0.2)', border: 'rgba(239, 68, 68, 1)' },
                    { bg: 'rgba(139, 92, 246, 0.2)', border: 'rgba(139, 92, 246, 1)' }
                ];

                datasets = chartData.datasets.map((dataset, index) => {
                    const color = colorPalette[index % colorPalette.length];
                    return {
                        label: dataset.label,
                        data: dataset.data,
                        backgroundColor: color.bg,
                        borderColor: color.border,
                        borderWidth: 2,
                        tension: 0.4
                    };
                });
            } else {
                // Single-series chart
                const colors = getChartColors(chart, chartData.labels.length);
                datasets = [{
                    label: chart.title,
                    data: chartData.values,
                    backgroundColor: colors.background,
                    borderColor: colors.border,
                    borderWidth: 2,
                    tension: 0.4
                }];
            }

            // Create Chart.js chart
            new Chart(canvas, {
                type: chart.type,
                data: {
                    labels: chartData.labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            display: true,  // Always show legend in modal
                            position: 'bottom'
                        },
                        title: {
                            display: false
                        }
                    },
                    scales: ['line', 'bar'].includes(chart.type) ? {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: chart.x_axis || 'X Axis'
                            }
                        },
                        y: {
                            display: true,
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: `${chart.aggregation || 'sum'}(${chart.y_axis})`
                            }
                        }
                    } : {}
                }
            });
        }

    } catch (error) {
        console.error('Error loading chart in modal:', error);
        modalBody.innerHTML = `
            <div style="background: #fee; padding: 20px; border-radius: 8px; color: #c00; text-align: center;">
                <strong>Error loading chart</strong><br>
                ${error.message}
            </div>
        `;
    }
}

// Go to dashboard from chart modal
async function goToChartDashboard() {
    if (!currentChartContext) {
        console.log('No current chart context');
        return;
    }

    const dashboardId = currentChartContext.dashboardId;
    console.log('=== goToChartDashboard START ===');
    console.log('Dashboard ID:', dashboardId);

    // Close modal
    closeModal('chartModal');
    console.log('Modal closed');

    // Navigate to the dashboard detail page
    window.location.href = `/dashboard/${dashboardId}`;
    console.log('Navigating to dashboard detail page:', dashboardId);
    console.log('=== goToChartDashboard END ===');
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        closeModal(event.target.id);
    }
}

// ============= Dashboard Filters =============

// Store current filter selections per dashboard
let dashboardFilters = {};

async function loadDashboardFilters(dashboardId, container) {
    try {
        const response = await fetch(`/api/dashboard/${dashboardId}/filters`);
        const data = await response.json();

        if (!data.filters || Object.keys(data.filters).length === 0) {
            container.innerHTML = '<p style="color: #888; font-size: 0.9em; padding: 10px;">No filters available</p>';
            return;
        }

        // Initialize filter state for this dashboard
        if (!dashboardFilters[dashboardId]) {
            dashboardFilters[dashboardId] = {};
        }

        // Determine if we're in fullscreen mode
        const isFullscreen = container.id.includes('fullscreen');
        const controlsId = isFullscreen ? `filter-controls-fullscreen-${dashboardId}` : `filter-controls-${dashboardId}`;
        const selectPrefix = isFullscreen ? 'filter-fullscreen' : 'filter';

        container.innerHTML = `<div style="background: #f9fafb; padding: 15px; border-radius: 8px; margin-bottom: 15px;"><h4 style="margin: 0 0 10px 0; font-size: 0.9em; color: #666;">🔍 Filters</h4><div id="${controlsId}" style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center;"></div></div>`;

        const filtersControls = document.getElementById(controlsId);

        // Create filter dropdowns
        for (const [field, filterInfo] of Object.entries(data.filters)) {
            const filterWrapper = document.createElement('div');
            filterWrapper.style.cssText = 'display: flex; flex-direction: column; min-width: 150px;';

            const label = document.createElement('label');
            label.textContent = filterInfo.label;
            label.style.cssText = 'font-size: 0.85em; color: #666; margin-bottom: 4px; font-weight: 500;';

            const select = document.createElement('select');
            select.id = `${selectPrefix}-${dashboardId}-${field}`;
            select.style.cssText = 'padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.9em; background: white;';

            // Add "All" option
            const allOption = document.createElement('option');
            allOption.value = '';
            allOption.textContent = 'All';
            select.appendChild(allOption);

            // Add value options
            filterInfo.values.forEach(value => {
                const option = document.createElement('option');
                option.value = value;
                option.textContent = value;
                select.appendChild(option);
            });

            // Handle cascading filters: when one filter changes, update others
            select.onchange = async () => {
                dashboardFilters[dashboardId][field] = select.value;
                await updateCascadingFilters(dashboardId, field);
                await reloadDashboardCharts(dashboardId);
            };

            filterWrapper.appendChild(label);
            filterWrapper.appendChild(select);
            filtersControls.appendChild(filterWrapper);
        }

        // Add clear filters button
        const clearBtn = document.createElement('button');
        clearBtn.textContent = '🗑️ Clear Filters';
        clearBtn.style.cssText = 'padding: 6px 12px; background: #ef4444; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.85em; margin-top: auto;';
        clearBtn.onclick = () => clearDashboardFilters(dashboardId);
        filtersControls.appendChild(clearBtn);

    } catch (error) {
        console.error('Error loading filters:', error);
        container.innerHTML = '<p style="color: #ef4444; font-size: 0.9em; padding: 10px;">Failed to load filters</p>';
    }
}

async function updateCascadingFilters(dashboardId, changedField) {
    // Get all filter controls for this dashboard - check both modes
    let filtersControls = document.getElementById('filter-controls-fullscreen-' + dashboardId);
    if (!filtersControls) {
        filtersControls = document.getElementById('filter-controls-' + dashboardId);
    }
    if (!filtersControls) return;

    // Get current filter selections
    const currentFilters = dashboardFilters[dashboardId] || {};

    // Re-fetch filter options with current selections applied
    try {
        const response = await fetch(`/api/dashboard/${dashboardId}/filters`);
        const data = await response.json();

        // Check which mode we're in for select IDs
        const isFullscreen = !!document.getElementById('filter-controls-fullscreen-' + dashboardId);
        const prefix = isFullscreen ? 'filter-fullscreen' : 'filter';

        // Update dropdown options for filters that come AFTER the changed one
        // This creates a cascading effect where earlier selections filter later options
        for (const [field, filterInfo] of Object.entries(data.filters)) {
            if (field === changedField) continue;

            const select = document.getElementById(`${prefix}-${dashboardId}-${field}`);
            if (!select) continue;

            const currentValue = select.value;

            // Clear and rebuild options
            select.innerHTML = '<option value="">All</option>';

            filterInfo.values.forEach(value => {
                const option = document.createElement('option');
                option.value = value;
                option.textContent = value;
                if (value === currentValue) {
                    option.selected = true;
                }
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error updating cascading filters:', error);
    }
}

async function reloadDashboardCharts(dashboardId) {
    // Check if we're in fullscreen mode
    let chartsContainer = document.getElementById('charts-fullscreen-' + dashboardId);

    // If not in fullscreen, use regular container
    if (!chartsContainer) {
        chartsContainer = document.getElementById('charts-' + dashboardId);
    }

    if (!chartsContainer) return;

    // Clear and reload charts with current filters
    chartsContainer.innerHTML = '<p style="color: #888; padding: 20px; text-align: center;">⏳ Reloading charts with filters...</p>';

    await loadDashboardCharts(dashboardId, chartsContainer, dashboardFilters[dashboardId]);
}

function clearDashboardFilters(dashboardId) {
    // Reset filter state
    dashboardFilters[dashboardId] = {};

    // Reset all dropdowns - check both regular and fullscreen mode
    let filtersControls = document.getElementById('filter-controls-fullscreen-' + dashboardId);
    if (!filtersControls) {
        filtersControls = document.getElementById('filter-controls-' + dashboardId);
    }

    if (filtersControls) {
        const selects = filtersControls.querySelectorAll('select');
        selects.forEach(select => select.value = '');
    }

    // Reload charts without filters
    reloadDashboardCharts(dashboardId);
}

// ============= Dashboard Export Functions =============

// Store original state for fullscreen mode
let fullscreenState = {
    active: false,
    dashboardId: null,
    originalContent: null
};

async function openDashboardInTab(dashboardId) {
    // Open dashboard in a new browser tab
    const url = `/dashboard/${dashboardId}`;
    window.open(url, '_blank');
}

function enterFullscreenMode(dashboardId) {
    if (fullscreenState.active) return;

    const container = document.querySelector('.container');
    const dashboardCard = document.getElementById('dashboard-' + dashboardId);

    if (!container || !dashboardCard) return;

    // Store original state
    fullscreenState.active = true;
    fullscreenState.dashboardId = dashboardId;
    fullscreenState.originalContent = container.innerHTML;

    // Create fullscreen view
    const dashboardClone = dashboardCard.cloneNode(true);
    dashboardClone.classList.add('expanded', 'fullscreen-dashboard');
    dashboardClone.querySelector('.dashboard-details').style.display = 'grid';

    // Add back arrow at the start of the header
    const headerLeft = dashboardClone.querySelector('.dashboard-header > div:first-child');
    if (headerLeft) {
        const backBtn = document.createElement('button');
        backBtn.className = 'icon-btn';
        backBtn.title = 'Back to Dashboards';
        backBtn.onclick = () => exitFullscreenMode();
        backBtn.innerHTML = '←';
        backBtn.style.cssText = 'margin-right: 12px; font-size: 1.2em;';
        headerLeft.insertBefore(backBtn, headerLeft.firstChild);
    }

    // Replace action buttons with export and exit buttons
    const headerRight = dashboardClone.querySelector('.dashboard-header > div:last-child');
    if (headerRight) {
        headerRight.innerHTML = `
            <button class="icon-btn" onclick="event.stopPropagation(); exportDashboardPDF('${dashboardId}')" title="Export as PDF">
                📄
            </button>
            <button class="icon-btn" onclick="event.stopPropagation(); exportDashboardData('${dashboardId}', 'csv')" title="Export as CSV">
                📊
            </button>
            <button class="icon-btn" onclick="event.stopPropagation(); exportDashboardData('${dashboardId}', 'excel')" title="Export as Excel">
                📈
            </button>
            <button class="icon-btn" onclick="exitFullscreenMode()" title="Exit Fullscreen" style="margin-left: 8px;">
                ✕
            </button>
        `;
    }

    // Clear container and add fullscreen dashboard
    container.innerHTML = '';
    container.appendChild(dashboardClone);

    // Add fullscreen styles
    const style = document.createElement('style');
    style.id = 'fullscreen-styles';
    style.textContent = `
        .container {
            max-width: 100% !important;
            padding: 20px !important;
        }
        .fullscreen-dashboard {
            width: 100%;
            max-width: none !important;
        }
        .fullscreen-dashboard .dashboard-header {
            background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
            color: white;
            padding: 20px;
            border-radius: 12px 12px 0 0;
        }
        .fullscreen-dashboard .dashboard-name {
            color: white !important;
            font-size: 1.5em;
        }
        .fullscreen-dashboard .dashboard-id {
            color: rgba(255,255,255,0.9) !important;
        }
        .fullscreen-dashboard .icon-btn {
            background: rgba(255,255,255,0.2);
            border-color: rgba(255,255,255,0.3);
            color: white;
            font-size: 1.3em;
        }
        .fullscreen-dashboard .icon-btn:hover {
            background: rgba(255,255,255,0.3);
            border-color: rgba(255,255,255,0.5);
            transform: translateY(-1px);
        }
        .fullscreen-dashboard .dashboard-header .dashboard-left {
            display: flex;
            align-items: center;
            gap: 8px;
        }
    `;
    document.head.appendChild(style);

    // Now reload the charts in the cloned dashboard
    const chartsContainer = dashboardClone.querySelector('.dashboard-details');
    const filtersContainer = dashboardClone.querySelector('.dashboard-filters');

    if (chartsContainer) {
        chartsContainer.id = 'charts-fullscreen-' + dashboardId;
        loadDashboardCharts(dashboardId, chartsContainer, dashboardFilters[dashboardId] || {});
    }

    if (filtersContainer) {
        filtersContainer.id = 'filters-fullscreen-' + dashboardId;
        filtersContainer.style.display = 'block';
        loadDashboardFilters(dashboardId, filtersContainer);
    }
}

function exitFullscreenMode() {
    if (!fullscreenState.active) return;

    const container = document.querySelector('.container');
    if (!container) return;

    // Restore original content
    container.innerHTML = fullscreenState.originalContent;

    // Remove fullscreen styles
    const style = document.getElementById('fullscreen-styles');
    if (style) style.remove();

    // Reset state
    fullscreenState = {
        active: false,
        dashboardId: null,
        originalContent: null
    };

    // Reload the dashboards list
    loadDashboards();
}

async function exportDashboardPDF(dashboardId) {
    try {
        // Use browser's print functionality for PDF
        const dashboardCard = document.getElementById('dashboard-' + dashboardId);
        if (!dashboardCard) return;

        // Ensure dashboard is expanded
        if (!dashboardCard.classList.contains('expanded')) {
            await toggleDashboard(dashboardId);
            await new Promise(resolve => setTimeout(resolve, 1000)); // Wait for charts to load
        }

        // Create a temporary container for print
        const printContainer = document.createElement('div');
        printContainer.id = 'print-container';
        printContainer.style.display = 'none';

        // Clone the dashboard
        const clone = dashboardCard.cloneNode(true);
        clone.classList.add('expanded');
        clone.querySelector('.dashboard-details').style.display = 'grid';

        // Remove action buttons
        const headerRight = clone.querySelector('.dashboard-header > div:last-child');
        if (headerRight) headerRight.remove();

        // Convert canvas charts to images
        const originalCanvases = dashboardCard.querySelectorAll('canvas');
        const clonedCanvases = clone.querySelectorAll('canvas');

        originalCanvases.forEach((originalCanvas, index) => {
            if (clonedCanvases[index]) {
                const clonedCanvas = clonedCanvases[index];
                const image = document.createElement('img');
                image.src = originalCanvas.toDataURL('image/png');
                image.style.maxWidth = '100%';
                image.style.height = 'auto';
                clonedCanvas.parentNode.replaceChild(image, clonedCanvas);
            }
        });

        printContainer.appendChild(clone);
        document.body.appendChild(printContainer);

        // Add print-specific styles
        const printStyles = document.createElement('style');
        printStyles.id = 'print-styles';
        printStyles.textContent = `
            @media print {
                body > *:not(#print-container) {
                    display: none !important;
                }
                #print-container {
                    display: block !important;
                }
                .dashboard-card {
                    box-shadow: none !important;
                    page-break-inside: avoid;
                }
                .dashboard-header {
                    cursor: default !important;
                }
                .expand-indicator {
                    display: none !important;
                }
                .icon-btn {
                    display: none !important;
                }
                .dashboard-filters {
                    display: none !important;
                }
                .chart-container img {
                    max-width: 100% !important;
                    height: auto !important;
                    page-break-inside: avoid;
                }
                .chart-card {
                    page-break-inside: avoid;
                    margin-bottom: 20px;
                }
                .metric-card {
                    page-break-inside: avoid;
                }
                .metric-value {
                    color: #000 !important;
                    font-size: 2rem !important;
                    font-weight: bold !important;
                }
                .metric-label {
                    color: #333 !important;
                }
            }
        `;
        document.head.appendChild(printStyles);

        // Wait a moment for styles to apply
        await new Promise(resolve => setTimeout(resolve, 100));

        // Print
        window.print();

        // Cleanup after print dialog closes (small delay)
        setTimeout(() => {
            document.body.removeChild(printContainer);
            document.head.removeChild(printStyles);
        }, 500);

    } catch (error) {
        console.error('Error exporting PDF:', error);
        alert('Failed to export PDF: ' + error.message);
    }
}

async function exportDashboardData(dashboardId, format) {
    try {
        const filters = dashboardFilters[dashboardId] || {};

        const response = await fetch(`/api/dashboard/${dashboardId}/export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                format: format,
                filters: filters
            })
        });

        if (!response.ok) {
            throw new Error('Export failed');
        }

        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${dashboardId}_data.${format === 'excel' ? 'xlsx' : 'csv'}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        alert(`Dashboard data exported as ${format.toUpperCase()} successfully!`);
    } catch (error) {
        console.error('Error exporting data:', error);
        alert('Failed to export data: ' + error.message);
    }
}

// Load models on page load
loadModels();
