/**
 * TransformDash JavaScript
 * Main application logic for dashboard interactivity
 */

// Global state
let modelsData = [];
let allRuns = [];
let currentFilter = 'all';

// Dark Mode Toggle
function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    document.getElementById('theme-icon').textContent = isDark ? '☀️' : '🌙';
    localStorage.setItem('darkMode', isDark);
}

// Load dark mode preference on page load
if (localStorage.getItem('darkMode') === 'true') {
    document.body.classList.add('dark-mode');
    document.getElementById('theme-icon').textContent = '☀️';
}

// Load Models
async function loadModels() {
    try {
        const response = await fetch('/api/models');
        modelsData = await response.json();

        // Update sync time
        const now = new Date();
        document.getElementById('sync-time').textContent = now.toLocaleTimeString();

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

        if (modelsData.length === 0) {
            modelsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📦</div>
                    <h3>No Models Found</h3>
                    <p>Add SQL or Python transformation models to the models/ directory to get started.</p>
                </div>
            `;
        } else {
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
        }

        // Draw lineage graph
        drawLineage(modelsData);

    } catch (error) {
        console.error('Error loading models:', error);
        const modelsList = document.getElementById('models-list');
        modelsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">❌</div>
                <h3>Failed to Load Models</h3>
                <p>There was an error loading the transformation models. Please check the console for details.</p>
            </div>
        `;
    }
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

// Close Modal
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
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
    document.getElementById(`${tabName}-tab`).classList.add('active');

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
            header.style.cursor = 'pointer';
            header.onclick = () => toggleDashboard(dashboard.id);
            header.innerHTML = `
                <div class="dashboard-left">
                    <span>📊</span>
                    <span class="dashboard-name">${dashboard.name}</span>
                    <span class="dashboard-id">${dashboard.charts?.length || 0} charts</span>
                </div>
                <div>
                    <span class="expand-indicator" id="expand-${dashboard.id}">▼</span>
                </div>
            `;

            // Dashboard description
            const desc = document.createElement('div');
            desc.className = 'dashboard-summary';
            desc.textContent = dashboard.description || 'No description';

            // Charts container (hidden by default, CSS handles styling)
            const chartsContainer = document.createElement('div');
            chartsContainer.id = 'charts-' + dashboard.id;
            chartsContainer.className = 'dashboard-details';

            // Assemble card
            card.appendChild(header);
            card.appendChild(desc);
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
async function loadDashboardCharts(dashboardId, container) {
    console.log('loadDashboardCharts called for:', dashboardId);

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
            await renderDashboardChart(chartConfig, container);
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
async function renderDashboardChart(chartConfig, container) {
    try {
        // Skip charts with unsupported features (but log them properly)
        if (chartConfig.metrics || chartConfig.calculation) {
            console.log('Skipping advanced chart type (requires multi-metric support):', chartConfig.id);
            // Don't return early, show an info card instead
            const infoCard = document.createElement('div');
            infoCard.style.cssText = 'background: #fef3c7; padding: 15px; border-radius: 8px; border-left: 4px solid #f59e0b;';
            infoCard.innerHTML = `
                <div style="font-weight: bold; color: #92400e; margin-bottom: 5px;">⚠️ ${chartConfig.title}</div>
                <div style="font-size: 0.85em; color: #78350f;">Advanced chart type - coming soon!</div>
            `;
            container.appendChild(infoCard);
            return;
        }

        // Validate required fields for standard charts
        if (chartConfig.type !== 'metric' && (!chartConfig.model || !chartConfig.x_axis || !chartConfig.y_axis)) {
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

        // Canvas for chart
        const canvas = document.createElement('canvas');
        canvas.id = 'chart-' + chartConfig.id;
        canvas.style.maxHeight = '300px';
        chartWrapper.appendChild(canvas);

        // Add to container first
        container.appendChild(chartWrapper);

        // Handle metric type
        if (chartConfig.type === 'metric') {
            await renderMetricChart(canvas, chartConfig);
            return;
        }

        // Fetch data from API for other chart types
        const queryResponse = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                table: chartConfig.model,
                x_axis: chartConfig.x_axis,
                y_axis: chartConfig.y_axis,
                aggregation: chartConfig.aggregation || 'sum'
            })
        });

        if (!queryResponse.ok) {
            throw new Error('Failed to fetch chart data');
        }

        const chartData = await queryResponse.json();

        // Validate response
        if (!chartData.labels || !chartData.values) {
            throw new Error('Invalid chart data received');
        }

        // Get colors
        const colors = getChartColors(chartConfig, chartData.labels.length);

        // Create Chart.js chart
        new Chart(canvas, {
            type: chartConfig.type,
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: chartConfig.title,
                    data: chartData.values,
                    backgroundColor: colors.background,
                    borderColor: colors.border,
                    borderWidth: 2,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: ['pie', 'doughnut'].includes(chartConfig.type)
                    }
                },
                scales: ['line', 'bar'].includes(chartConfig.type) ? {
                    y: {
                        beginAtZero: true
                    }
                } : {}
            }
        });

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
async function renderMetricChart(canvas, chartConfig) {
    try {
        // Determine which field to query
        const metricField = chartConfig.metric || chartConfig.y_axis;
        if (!metricField) {
            throw new Error('No metric field specified');
        }

        // For metrics, query the data
        const queryResponse = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                table: chartConfig.model,
                x_axis: metricField,
                y_axis: metricField,
                aggregation: chartConfig.aggregation || 'sum'
            })
        });

        if (!queryResponse.ok) {
            throw new Error('Failed to fetch metric data');
        }

        const chartData = await queryResponse.json();

        // Validate data
        if (!chartData.values || chartData.values.length === 0) {
            throw new Error('No data returned for metric');
        }

        const value = chartData.values.reduce((a, b) => a + b, 0);

        // Hide canvas and show metric value instead
        canvas.style.display = 'none';
        const metricDiv = document.createElement('div');
        metricDiv.style.cssText = 'text-align: center; padding: 30px 0;';
        metricDiv.innerHTML = `
            <div style="font-size: 3em; font-weight: bold; color: #667eea;">${formatMetricValue(value)}</div>
            <div style="font-size: 0.9em; color: #888; margin-top: 5px;">${chartConfig.aggregation?.toUpperCase() || 'TOTAL'}</div>
        `;
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
            card.style.cssText = 'background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;';
            card.onmouseenter = () => {
                card.style.transform = 'translateY(-2px)';
                card.style.boxShadow = '0 4px 8px rgba(0,0,0,0.15)';
            };
            card.onmouseleave = () => {
                card.style.transform = 'translateY(0)';
                card.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
            };

            // Chart type icon
            const typeIcons = {
                line: '📈',
                bar: '📊',
                pie: '🥧',
                doughnut: '🍩',
                metric: '🔢'
            };

            card.innerHTML = `
                <div style="font-size: 1.5em; margin-bottom: 8px;">${typeIcons[chart.type] || '📊'}</div>
                <div style="font-weight: bold; color: #333; margin-bottom: 5px; font-size: 0.95em;">${chart.title}</div>
                <div style="font-size: 0.75em; color: #666; margin-bottom: 8px;">${chart.dashboardName}</div>
                <div style="display: flex; gap: 5px; flex-wrap: wrap;">
                    <span style="background: #e0e7ff; color: #667eea; padding: 3px 8px; border-radius: 4px; font-size: 0.7em;">${chart.type}</span>
                    <span style="background: #e0f2fe; color: #0284c7; padding: 3px 8px; border-radius: 4px; font-size: 0.7em;">${chart.model}</span>
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
        countDiv.style.cssText = 'grid-column: 1 / -1; text-align: center; color: #666; font-size: 0.9em; margin-top: 10px;';
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
    if (!table) return;

    try {
        const response = await fetch(`/api/tables/${table}/columns`);
        const data = await response.json();

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

        // Hide placeholder, show canvas
        document.getElementById('chartPlaceholder').style.display = 'none';
        document.getElementById('chartCanvas').style.display = 'block';

        // Destroy existing chart if any
        if (currentChart) {
            currentChart.destroy();
        }

        // Create new chart
        const ctx = document.getElementById('chartCanvas').getContext('2d');
        currentChart = new Chart(ctx, {
            type: chartType,
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
            options: {
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
                scales: chartType !== 'pie' && chartType !== 'doughnut' ? {
                    y: { beginAtZero: true }
                } : {}
            }
        });

        // Enable save button
        document.getElementById('saveChartBtn').disabled = false;

    } catch (error) {
        console.error('Error creating chart:', error);
        document.getElementById('chartError').style.display = 'block';
        document.getElementById('chartError').textContent = 'Error creating chart: ' + error.message;
    }
}

function saveChart() {
    const title = document.getElementById('chartTitle').value || 'Chart';
    alert(`Chart "${title}" saved!\n\nIn a full implementation, this would save to a charts.yml file that can be loaded into dashboards.`);
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
            <div class="run-item ${status}" onclick="viewRunLogs('${run.run_id}')">
                <div class="run-header">
                    <div style="display: flex; align-items: center; gap: 12px;">
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
            // Skip unsupported chart types
            if (chart.metrics || chart.calculation) {
                throw new Error('This chart type requires additional features not yet implemented');
            }

            // Fetch data
            const queryResponse = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    table: chart.model,
                    x_axis: chart.x_axis,
                    y_axis: chart.y_axis,
                    aggregation: chart.aggregation || 'sum'
                })
            });

            if (!queryResponse.ok) {
                throw new Error('Failed to fetch chart data');
            }

            const chartData = await queryResponse.json();

            if (!chartData.labels || !chartData.values) {
                throw new Error('Invalid chart data received');
            }

            // Get colors
            const colors = getChartColors(chart, chartData.labels.length);

            // Create Chart.js chart
            new Chart(canvas, {
                type: chart.type,
                data: {
                    labels: chartData.labels,
                    datasets: [{
                        label: chart.title,
                        data: chartData.values,
                        backgroundColor: colors.background,
                        borderColor: colors.border,
                        borderWidth: 2,
                        tension: 0.4
                    }]
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

    // Add a lock to prevent toggle while we're navigating
    toggleLock.add(dashboardId);
    console.log('Lock added for:', dashboardId);

    // Close modal
    closeModal('chartModal');
    console.log('Modal closed');

    // Switch to dashboards tab
    switchTab('dashboards');
    console.log('Switched to dashboards tab');

    // Wait for dashboards to load
    await new Promise(resolve => setTimeout(resolve, 300));
    console.log('Waited for dashboards to load');

    // Find and scroll to the specific dashboard
    const dashboardCard = document.getElementById('dashboard-' + dashboardId);
    console.log('Found dashboard card:', dashboardCard ? 'YES' : 'NO');

    if (dashboardCard) {
        dashboardCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        console.log('Scrolling to dashboard');

        // Wait for scroll to complete
        await new Promise(resolve => setTimeout(resolve, 500));
        console.log('Scroll complete');

        // Ensure the dashboard is expanded (don't toggle if already expanded)
        const chartsContainer = document.getElementById('charts-' + dashboardId);
        const expandIndicator = document.getElementById('expand-' + dashboardId);

        console.log('Charts container found:', chartsContainer ? 'YES' : 'NO');
        console.log('Expand indicator found:', expandIndicator ? 'YES' : 'NO');

        if (dashboardCard && chartsContainer) {
            // Only expand if currently collapsed
            const isExpanded = dashboardCard.classList.contains('expanded');
            console.log('Is currently expanded:', isExpanded);
            console.log('Container children count:', chartsContainer.children.length);

            if (!isExpanded) {
                console.log('Expanding dashboard from modal navigation');
                dashboardCard.classList.add('expanded');
                console.log('Added expanded class to dashboard card');

                if (expandIndicator) expandIndicator.textContent = '▲';

                // Load charts if not already loaded
                if (chartsContainer.children.length === 0) {
                    console.log('Container empty, loading charts...');
                    await loadDashboardCharts(dashboardId, chartsContainer);
                    console.log('Charts loaded, container now has', chartsContainer.children.length, 'children');
                } else {
                    console.log('Container already has', chartsContainer.children.length, 'children');
                }

                // Verify state after loading
                console.log('After loading - is expanded:', dashboardCard.classList.contains('expanded'));
                console.log('After loading - container children:', chartsContainer.children.length);
            } else {
                console.log('Dashboard already expanded, keeping it open');
            }
        }

        // Keep lock for a bit longer to prevent accidental toggles
        setTimeout(() => {
            toggleLock.delete(dashboardId);
            const stillExpanded = dashboardCard.classList.contains('expanded');
            console.log('Released lock for dashboard:', dashboardId);
            console.log('Dashboard still expanded after lock release:', stillExpanded);
            console.log('=== goToChartDashboard END ===');
        }, 1000);
    } else {
        // Release lock if dashboard not found
        toggleLock.delete(dashboardId);
        console.log('Dashboard not found, lock released');
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        closeModal(event.target.id);
    }
}

// Load models on page load
loadModels();
