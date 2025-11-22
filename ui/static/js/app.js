/**
 * TransformDash JavaScript - Modern UI
 * Main application logic for dashboard interactivity with sidebar navigation
 * Last updated: 2025-11-03T13:45:00Z - Improved dashboard table view with structured columns (Name, Description, Charts, Owner, Tags, Actions)
 */

// ============================================
// GLOBAL USER PERMISSIONS
// ============================================

// Store current user's permissions
window.userPermissions = {
    canDeleteCharts: false,
    canEditCharts: false,
    canCreateCharts: false,
    isSuperuser: false,
    loaded: false
};

// Load user permissions on page load
async function loadUserPermissions() {
    try {
        const response = await fetch('/api/auth/me');
        if (response.ok) {
            const data = await response.json();
            const user = data.user;

            window.userPermissions.isSuperuser = user.is_superuser;

            // Check permissions
            if (user.is_superuser) {
                // Superuser has all permissions
                window.userPermissions.canDeleteCharts = true;
                window.userPermissions.canEditCharts = true;
                window.userPermissions.canCreateCharts = true;
            } else if (user.permissions) {
                // Check specific permissions
                const permNames = user.permissions.map(p => p.name);
                window.userPermissions.canDeleteCharts = permNames.includes('delete_charts');
                window.userPermissions.canEditCharts = permNames.includes('edit_charts');
                window.userPermissions.canCreateCharts = permNames.includes('create_charts');
            }

            window.userPermissions.loaded = true;
        }
    } catch (error) {
        console.error('Error loading user permissions:', error);
    }
}

// Load permissions when page loads
loadUserPermissions();

// ============================================
// GLOBAL VIEW MODE SETTINGS
// ============================================

// Track view modes for Charts and Dashboards pages
let chartsViewMode = localStorage.getItem('chartsViewMode') || 'grid'; // 'grid' or 'table'
let dashboardsViewMode = localStorage.getItem('dashboardsViewMode') || 'grid'; // 'grid' or 'table'

// Toggle view mode for Charts page
function toggleChartsView(mode) {
    chartsViewMode = mode;
    localStorage.setItem('chartsViewMode', mode);

    // Update button states
    document.querySelectorAll('.view-toggle-btn-charts').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-view-charts="${mode}"]`)?.classList.add('active');

    // Reload charts with new view
    loadAllCharts();
}

// Toggle view mode for Dashboards page
function toggleDashboardsView(mode) {
    dashboardsViewMode = mode;
    localStorage.setItem('dashboardsViewMode', mode);

    // Update button states
    document.querySelectorAll('.view-toggle-btn-dashboards').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-view-dashboards="${mode}"]`)?.classList.add('active');

    // Reload dashboards with new view
    loadDashboards();
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

// General purpose debounce utility
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Generic search/filter function for lists
function filterListItems(searchTerm, items, searchFields) {
    const term = searchTerm.toLowerCase().trim();
    if (!term) return items;

    return items.filter(item => {
        return searchFields.some(field => {
            const value = item[field];
            if (value === null || value === undefined) return false;
            return String(value).toLowerCase().includes(term);
        });
    });
}

// Helper function to get ALL charts from dashboard (both assigned to tabs and unassigned)
function getDashboardCharts(dashboard) {
    let allCharts = [];
    const seenIds = new Set();

    // Get charts from tabs
    if (dashboard.tabs && dashboard.tabs.length > 0) {
        dashboard.tabs.forEach(tab => {
            (tab.charts || []).forEach(chart => {
                if (!seenIds.has(chart.id)) {
                    allCharts.push(chart);
                    seenIds.add(chart.id);
                }
            });
        });
    }

    // Add unassigned charts (charts array at top level)
    if (dashboard.charts && Array.isArray(dashboard.charts)) {
        dashboard.charts.forEach(chart => {
            if (!seenIds.has(chart.id)) {
                allCharts.push(chart);
                seenIds.add(chart.id);
            }
        });
    }

    return allCharts;
}

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
    // Check if we're leaving the editor - if so, reset editor state
    const editorView = document.getElementById('dashboard-editor-view');
    if (editorView && editorView.classList.contains('active')) {
        // Clear editor state when leaving
        editorState = {
            dashboardId: null,
            dashboardName: null,
            currentCharts: [],
            availableCharts: [],
            draggedIndex: null,
            currentFilters: [],
            availableFields: [],
            tabs: [],
            currentTabId: null,
            dashboardData: null
        };
    }

    // Hide all views
    document.querySelectorAll('.view-content').forEach(view => {
        view.classList.remove('active');
        view.style.display = 'none';  // Explicitly hide
    });

    // Show selected view
    const targetView = document.getElementById(viewName + '-view');
    if (targetView) {
        targetView.classList.add('active');
        targetView.style.display = 'block';  // Explicitly show
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
            // Clear editing state when going back to charts list
            currentEditingChartId = null;
            loadAllCharts();
            break;
        case 'chart-builder':
            // Load available connections for chart builder
            loadChartConnections();
            break;
        case 'ml-models':
            loadMLModels();
            break;
        case 'runs':
            loadRuns();
            break;
        case 'schedules':
            loadSchedules();
            break;
        case 'monitor':
            loadSystemStatus();
            break;
        case 'assets':
            loadAssets();
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
                const charts = getDashboardCharts(dashboard);
                totalCharts += charts.length;
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
        // Use a stats endpoint or calculate from models
        const response = await fetch('/api/models');
        const data = await response.json();
        const totalRowsEl = document.getElementById('total-rows');

        // data is an array directly, not wrapped in an object
        if (Array.isArray(data) && data.length > 0) {
            const modelCount = data.length;
            totalRowsEl.textContent = `${modelCount} models`;
        } else {
            totalRowsEl.textContent = '0 models';
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

async function createNewDashboard() {
    const dashboardName = prompt('Enter a name for your new dashboard:');

    if (!dashboardName || dashboardName.trim() === '') {
        return; // User cancelled or entered empty name
    }

    const dashboardDescription = prompt('Enter a description (optional):', '') || '';

    try {
        const response = await fetch('/api/dashboards', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name: dashboardName.trim(),
                description: dashboardDescription.trim()
            })
        });

        const result = await response.json();

        if (response.ok) {
            showToast(result.message || 'Dashboard created successfully!', 'success');
            // Reload dashboards to show the new one
            await loadDashboards();
            // Open the new dashboard in edit mode
            if (result.dashboard) {
                openDashboardEditor(result.dashboard.id, result.dashboard.name);
            }
        } else {
            showToast(result.detail || 'Failed to create dashboard', 'error');
        }
    } catch (error) {
        console.error('Error creating dashboard:', error);
        showToast('Failed to create dashboard', 'error');
    }
}

// ============================================
// INITIALIZE ON PAGE LOAD
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Check if we need to open dashboard editor from URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    const editDashboardId = urlParams.get('edit');
    const action = urlParams.get('action');

    // Check if we need to edit a chart from dashboard view
    if (action === 'editChart') {
        // Remove the action parameter from URL
        window.history.replaceState({}, document.title, window.location.pathname);

        // Get chart config from sessionStorage
        const chartConfigStr = sessionStorage.getItem('editChart');
        if (chartConfigStr) {
            sessionStorage.removeItem('editChart');
            try {
                const chartConfig = JSON.parse(chartConfigStr);
                // Call editChart after a short delay to ensure DOM is ready
                setTimeout(() => editChart(chartConfig), 100);
            } catch (e) {
                console.error('Error parsing chart config:', e);
                switchView('overview');
            }
        } else {
            switchView('overview');
        }
    } else if (editDashboardId) {
        // Remove the edit parameter from URL
        window.history.replaceState({}, document.title, window.location.pathname);

        // Load dashboards first, then open the editor WITHOUT switching to overview first
        loadDashboards().then(() => {
            // Find the dashboard by ID
            fetch('/api/dashboards')
                .then(res => res.json())
                .then(data => {
                    const dashboard = data.dashboards.find(d => d.id === editDashboardId);
                    if (dashboard) {
                        // Directly open the editor without showing overview
                        openDashboardEditor(dashboard.id, dashboard.name);
                    } else {
                        switchView('overview');
                        showToast('Dashboard not found', 'error');
                    }
                })
                .catch(err => {
                    console.error('Error loading dashboard:', err);
                    switchView('overview');
                });
        });
    } else {
        // Load overview by default
        switchView('overview');
    }

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
                if (getDashboardCharts(dashboard)) {
                    getDashboardCharts(dashboard).forEach(chart => {
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

    // Apply search filter
    let filteredModels = models;
    if (currentModelsSearchTerm) {
        filteredModels = filterListItems(currentModelsSearchTerm, models, ['name', 'description', 'layer']);
    }

    if (filteredModels.length === 0) {
        modelsList.innerHTML = `
            <div style="text-align: center; padding: 60px 20px; background: var(--color-bg); border-radius: 12px; border: 1px solid var(--color-border);">
                <div style="font-size: 4em; margin-bottom: 20px;">📦</div>
                <h3 style="margin-bottom: 10px; color: var(--color-text);">No Models Found</h3>
                <p style="color: var(--color-text-secondary);">${currentModelsSearchTerm ? 'No models match your search criteria.' : 'Add SQL or Python transformation models to the models/ directory to get started.'}</p>
            </div>
        `;
        return;
    }

    // Group models by layer
    const groupedModels = {
        bronze: filteredModels.filter(m => getModelLayer(m.name) === 'bronze'),
        silver: filteredModels.filter(m => getModelLayer(m.name) === 'silver'),
        gold: filteredModels.filter(m => getModelLayer(m.name) === 'gold')
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
                    <div class="model-card-content">
                        <div class="model-info">
                            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
                                <div style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;" onclick="toggleModelCode('${model.name}')">
                                    <span class="expand-icon" id="expand-model-${model.name}">▶</span>
                                    <h4 class="model-name">${model.name}</h4>
                                </div>
                                <div style="display: flex; gap: 0.5rem;">
                                    <button class="btn btn-secondary" style="padding: 0.4rem 0.8rem; font-size: 0.875rem;" onclick="event.stopPropagation(); toggleModelHistory('${model.name}')">
                                        📊 History
                                    </button>
                                    <button class="btn btn-primary" style="padding: 0.4rem 0.8rem; font-size: 0.875rem;" onclick="event.stopPropagation(); runSingleModel('${model.name}')">
                                        ▶ Run
                                    </button>
                                </div>
                            </div>
                            <div class="model-badges" onclick="toggleModelCode('${model.name}')" style="cursor: pointer;">
                                <span class="badge badge-${layer}">${layer.toUpperCase()}</span>
                                <span class="badge badge-type">${model.type.toUpperCase()}</span>
                            </div>
                            <div onclick="toggleModelCode('${model.name}')" style="cursor: pointer;">
                                ${model.depends_on.length > 0 ?
                                    `<div class="model-dependencies"><strong>Depends on:</strong> ${model.depends_on.join(', ')}</div>` :
                                    '<div class="model-dependencies">No dependencies</div>'}
                                <div class="model-usage" id="usage-${model.name}" style="margin-top: 0.5rem;">
                                    <em style="color: #888; font-size: 0.875rem;">Loading usage...</em>
                                </div>
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
                    <div class="model-history-section" id="history-${model.name}" style="display: none; padding: 1rem; background: #f8f9fa; border-top: 1px solid #e0e0e0;">
                        <div class="loading">Loading history...</div>
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

// ============================================
// SEARCH HANDLERS
// ============================================

// Debounce utility
let searchDebounceTimer = null;
function debounceSearch(callback, delay = 300) {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(callback, delay);
}

// 1. Models Search
let currentModelsSearchTerm = '';
function handleModelsSearch(searchTerm) {
    currentModelsSearchTerm = searchTerm;
    const clearBtn = document.getElementById('models-search-clear');
    if (clearBtn) {
        clearBtn.style.display = searchTerm ? 'block' : 'none';
    }
    debounceSearch(() => {
        displayModels(modelsData, currentModelFilter);
    });
}

function clearModelsSearch() {
    document.getElementById('models-search').value = '';
    currentModelsSearchTerm = '';
    document.getElementById('models-search-clear').style.display = 'none';
    displayModels(modelsData, currentModelFilter);
}

// 2. Dashboards Search
let allDashboardsData = [];
let currentDashboardsSearchTerm = '';
function handleDashboardsSearch(searchTerm) {
    currentDashboardsSearchTerm = searchTerm;
    const clearBtn = document.getElementById('dashboards-search-clear');
    if (clearBtn) {
        clearBtn.style.display = searchTerm ? 'block' : 'none';
    }
    debounceSearch(() => {
        loadDashboards();
    });
}

function clearDashboardsSearch() {
    document.getElementById('dashboards-search').value = '';
    currentDashboardsSearchTerm = '';
    document.getElementById('dashboards-search-clear').style.display = 'none';
    loadDashboards();
}

// 3. Charts Search
let allChartsData = [];
let currentChartsSearchTerm = '';
function handleChartsSearch(searchTerm) {
    currentChartsSearchTerm = searchTerm;
    const clearBtn = document.getElementById('charts-search-clear');
    if (clearBtn) {
        clearBtn.style.display = searchTerm ? 'block' : 'none';
    }
    debounceSearch(() => {
        loadAllCharts();
    });
}

function clearChartsSearch() {
    document.getElementById('charts-search').value = '';
    currentChartsSearchTerm = '';
    document.getElementById('charts-search-clear').style.display = 'none';
    loadAllCharts();
}

// 4. SQL Lab Tables Search
let allTablesData = [];
let currentTablesSearchTerm = '';
function handleTablesSearch(searchTerm) {
    currentTablesSearchTerm = searchTerm;
    const clearBtn = document.getElementById('tables-search-clear');
    if (clearBtn) {
        clearBtn.style.display = searchTerm ? 'block' : 'none';
    }
    debounceSearch(() => {
        filterTablesDisplay();
    });
}

function clearTablesSearch() {
    document.getElementById('tables-search').value = '';
    currentTablesSearchTerm = '';
    document.getElementById('tables-search-clear').style.display = 'none';
    filterTablesDisplay();
}

function filterTablesDisplay() {
    const browser = document.getElementById('schema-browser');
    if (!allTablesData || allTablesData.length === 0) return;

    const filteredTables = currentTablesSearchTerm
        ? filterListItems(currentTablesSearchTerm, allTablesData, ['name'])
        : allTablesData;

    if (filteredTables.length === 0) {
        browser.innerHTML = '<p style="color: #888; font-size: 0.85rem;">No tables found matching your search</p>';
        return;
    }

    let html = '<div style="font-size: 0.85rem;">';
    for (const table of filteredTables) {
        const tableName = table.name || table;
        const tableType = table.type || 'table';
        const tableSize = table.size || '';
        const icon = tableType === 'view' ? '👁️' : tableType === 'materialized_view' ? '💾' : '📋';

        html += `
            <div style="margin-bottom: 12px; background: #f8f9fa; border-radius: 6px; overflow: hidden;">
                <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px; cursor: pointer; transition: background 0.2s;"
                     onclick="toggleTableDetails('${tableName}')"
                     onmouseover="this.style.background='#e9ecef'"
                     onmouseout="this.style.background='#f8f9fa'">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #495057; margin-bottom: 4px;">
                            <span id="expand-icon-${tableName}" style="display: inline-block; width: 12px; transition: transform 0.2s;">▶</span>
                            ${icon} ${tableName}
                        </div>
                        <div style="font-size: 0.75rem; color: #6c757d;">${tableType}${tableSize ? ' • ' + tableSize : ''}</div>
                    </div>
                    <div style="position: relative;">
                        <button onclick="event.stopPropagation(); showTableMenu('${tableName}', event)"
                                style="background: none; border: none; color: #667eea; cursor: pointer; font-size: 1.2rem; padding: 4px 8px;">
                            ⋮
                        </button>
                    </div>
                </div>
                <div id="table-details-${tableName}" style="display: none; padding: 0 8px 8px 8px; background: white; border-top: 1px solid #e9ecef;">
                    <div style="font-size: 0.75rem; color: #888; margin: 8px 0 4px 0;">Loading columns...</div>
                </div>
            </div>
        `;
    }
    html += '</div>';
    browser.innerHTML = html;
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

        // Fetch all models to calculate "Used By"
        const allModelsResponse = await fetch('/api/models');
        const allModels = await allModelsResponse.json();

        // Find models that depend on this model
        const usedBy = allModels
            .filter(m => m.depends_on.includes(modelName))
            .map(m => m.name);

        const metaInfo = `
            <div class="model-meta-info">
                <p><strong>Type:</strong> ${data.config.materialized || 'view'}</p>
                <p><strong>Depends on:</strong> ${data.depends_on.length > 0 ? data.depends_on.map(dep => `<span style="background: #e0e7ff; color: #3730a3; padding: 2px 8px; border-radius: 4px; margin: 2px; display: inline-block; font-size: 0.875rem;">${dep}</span>`).join(' ') : '<span style="color: #9ca3af;">None</span>'}</p>
                <p><strong>Used by:</strong> ${usedBy.length > 0 ? usedBy.map(model => `<span style="background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 4px; margin: 2px; display: inline-block; font-size: 0.875rem;">${model}</span>`).join(' ') : '<span style="color: #9ca3af;">None</span>'}</p>
                <p><strong>File:</strong> <code style="background: #f3f4f6; padding: 2px 6px; border-radius: 3px; font-size: 0.875rem;">${data.file_path}</code></p>
            </div>
            <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #e5e7eb;">
                <button onclick="goToModelView('${modelName}')" class="btn btn-primary" style="margin-right: 8px;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 4px;">
                        <path d="M9 18l6-6-6-6"/>
                    </svg>
                    Go to Model
                </button>
                <button onclick="closeModal('codeModal')" class="btn btn-secondary">
                    Close
                </button>
            </div>
        `;

        const code = `
            <h3 style="margin-top: 24px; margin-bottom: 12px; color: #111827; font-size: 1.125rem;">SQL Code:</h3>
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

async function toggleModelHistory(modelName) {
    const historySection = document.getElementById(`history-${modelName}`);

    if (historySection.style.display === 'block') {
        // Collapse
        historySection.style.display = 'none';
    } else {
        // Expand
        historySection.style.display = 'block';

        // Load history if not already loaded
        if (historySection.innerHTML.includes('Loading history')) {
            await loadModelHistory(modelName);
        }
    }
}

function toggleRunLogs(logsId) {
    const logsRow = document.getElementById(logsId);
    const button = event.target;

    if (logsRow.style.display === 'none' || logsRow.style.display === '') {
        logsRow.style.display = 'table-row';
        button.textContent = '▼';
    } else {
        logsRow.style.display = 'none';
        button.textContent = '▶';
    }
}

async function loadModelHistory(modelName) {
    const historySection = document.getElementById(`history-${modelName}`);

    try {
        const response = await fetch(`/api/models/${modelName}/runs?limit=10`);
        const data = await response.json();

        if (!data.runs || data.runs.length === 0) {
            historySection.innerHTML = '<p style="color: #888; font-style: italic;">No run history available</p>';
            return;
        }

        // Build history table
        let html = `
            <h5 style="margin-top: 0; margin-bottom: 0.75rem; color: #333;">Run History</h5>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">
                    <thead>
                        <tr style="background: #e9ecef; border-bottom: 2px solid #dee2e6;">
                            <th style="padding: 0.5rem; text-align: left; width: 30px;"></th>
                            <th style="padding: 0.5rem; text-align: left;">Timestamp</th>
                            <th style="padding: 0.5rem; text-align: left;">Status</th>
                            <th style="padding: 0.5rem; text-align: right;">Execution Time</th>
                            <th style="padding: 0.5rem; text-align: left;">Error</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        data.runs.forEach((run, index) => {
            const timestamp = new Date(run.timestamp).toLocaleString();
            const statusBadge = run.status === 'success'
                ? '<span style="color: #22c55e; font-weight: 600;">✓ Success</span>'
                : '<span style="color: #ef4444; font-weight: 600;">✗ Failed</span>';
            const execTime = run.execution_time.toFixed(3) + 's';
            const errorMsg = run.error
                ? `<span style="color: #ef4444; font-size: 0.8rem;">${run.error.substring(0, 100)}${run.error.length > 100 ? '...' : ''}</span>`
                : '-';

            const hasLogs = run.logs && run.logs.length > 0;
            const logsId = `logs-${modelName}-${index}`;

            html += `
                <tr style="border-bottom: 1px solid #e9ecef;">
                    <td style="padding: 0.5rem;">
                        ${hasLogs ? `<button onclick="toggleRunLogs('${logsId}')" style="background: none; border: none; cursor: pointer; font-size: 1rem; padding: 0;" title="Toggle logs">▶</button>` : ''}
                    </td>
                    <td style="padding: 0.5rem;">${timestamp}</td>
                    <td style="padding: 0.5rem;">${statusBadge}</td>
                    <td style="padding: 0.5rem; text-align: right;">${execTime}</td>
                    <td style="padding: 0.5rem; max-width: 300px; overflow: hidden; text-overflow: ellipsis;">${errorMsg}</td>
                </tr>
            `;

            // Add logs row (initially hidden)
            if (hasLogs) {
                html += `
                    <tr id="${logsId}" style="display: none; background: #f8f9fa;">
                        <td colspan="5" style="padding: 0.75rem;">
                            <div style="background: #1e1e1e; color: #d4d4d4; padding: 12px; border-radius: 6px; font-family: 'Monaco', 'Menlo', 'Courier New', monospace; font-size: 0.75rem; max-height: 300px; overflow-y: auto; white-space: pre-wrap; line-height: 1.4;">
${run.logs.join('\n')}
                            </div>
                        </td>
                    </tr>
                `;
            }
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        historySection.innerHTML = html;

    } catch (error) {
        console.error('Error loading model history:', error);
        historySection.innerHTML = '<p style="color: #ef4444;">Failed to load history</p>';
    }
}

async function runSingleModel(modelName) {
    try {
        // Show loading toast
        showToast(`Running model: ${modelName}...`, 'info');

        // Disable the button to prevent double-clicks
        const runButtons = document.querySelectorAll(`button[onclick*="runSingleModel('${modelName}')"]`);
        runButtons.forEach(btn => {
            btn.disabled = true;
            btn.textContent = '⏳ Running...';
        });

        // Call the API to run the model
        const response = await fetch(`/api/execute/${modelName}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        // Re-enable the button
        runButtons.forEach(btn => {
            btn.disabled = false;
            btn.textContent = '▶ Run';
        });

        if (data.status === 'completed') {
            showToast(
                `Model '${modelName}' executed successfully! ` +
                `(${data.dependencies_run} dependencies also ran)`,
                'success'
            );
        } else {
            showToast(
                `Model '${modelName}' failed: ${data.model.error || 'Unknown error'}`,
                'error'
            );
        }

        // Reload models to update status
        await loadModels();

    } catch (error) {
        console.error('Error running model:', error);
        showToast(`Failed to run model '${modelName}': ${error.message}`, 'error');

        // Re-enable the button on error
        const runButtons = document.querySelectorAll(`button[onclick*="runSingleModel('${modelName}')"]`);
        runButtons.forEach(btn => {
            btn.disabled = false;
            btn.textContent = '▶ Run';
        });
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

        // Show feedback using toast
        showToast('Code copied to clipboard!', 'success');
    } catch (error) {
        console.error('Error copying to clipboard:', error);
        showToast('Failed to copy code to clipboard', 'error');
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

// Dashboard Editor - Full Page Editor with Drag & Drop
let editorState = {
    dashboardId: null,
    dashboardName: null,
    currentCharts: [],
    availableCharts: [],
    draggedIndex: null,
    currentFilters: [],
    availableFields: [],  // Store all available fields from dashboard models
    tabs: [],  // Store tabs with their charts
    currentTabId: null,  // Currently selected tab in editor
    dashboardData: null  // Store full dashboard data
};

async function deleteDashboard(dashboardId, dashboardName) {
    if (!confirm(`Are you sure you want to delete the dashboard "${dashboardName}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/dashboards/${dashboardId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (response.ok) {
            showToast( result.message || 'Dashboard deleted successfully!');
            // Reload the dashboards list
            await loadDashboards();
        } else {
            showToast( result.detail || 'Failed to delete dashboard');
        }
    } catch (error) {
        console.error('Error deleting dashboard:', error);
        showToast( 'An error occurred while deleting the dashboard');
    }
}

async function openDashboardEditor(dashboardId, dashboardName) {
    // Initialize editor state
    editorState.dashboardId = dashboardId;
    editorState.dashboardName = dashboardName;

    // Set dashboard name in header
    document.getElementById('editor-dashboard-name').textContent = `Edit: ${dashboardName}`;

    // Hide all views and show editor
    document.querySelectorAll('.view-content').forEach(view => {
        view.classList.remove('active');
        view.style.display = 'none';
    });

    const editorView = document.getElementById('dashboard-editor-view');
    editorView.style.display = 'block';
    editorView.classList.add('active');

    // Load dashboard and charts data
    await loadEditorData();
}

async function loadEditorData() {
    try {
        // Load current dashboard charts
        const dashboardResponse = await fetch(`/api/dashboards/${editorState.dashboardId}`);
        const dashboardData = await dashboardResponse.json();
        editorState.dashboardData = dashboardData;

        // Handle tab structure
        if (dashboardData.tabs && dashboardData.tabs.length > 0) {
            // Tab-based structure
            editorState.tabs = dashboardData.tabs.map(tab => ({
                id: tab.id,
                name: tab.name,
                charts: tab.charts || []
            }));

            editorState.currentTabId = editorState.tabs[0].id;  // Select first tab
        } else {
            // Legacy flat structure - create a default tab
            editorState.tabs = [{
                id: 'tab_default',
                name: 'All Charts',
                charts: dashboardData.charts || []
            }];
            editorState.currentTabId = 'tab_default';
        }

        editorState.currentCharts = getDashboardCharts(dashboardData);
        editorState.currentFilters = dashboardData.filters || [];

        // Load all available charts
        const chartsResponse = await fetch('/api/charts');
        const chartsData = await chartsResponse.json();
        editorState.availableCharts = chartsData.charts || [];

        // Fetch available fields from all models used in this dashboard
        await fetchAvailableFields();

        // Render the editor
        renderEditorTabs();
        renderDashboardFilters();
        renderEditorCharts();
        renderAvailableCharts();
    } catch (error) {
        console.error('Error loading editor data:', error);
        showToast('Failed to load editor data', 'error');
    }
}

async function fetchAvailableFields() {
    try {
        // Get unique models from dashboard charts
        const models = [...new Set(editorState.currentCharts.map(c => c.model).filter(m => m))];

        if (models.length === 0) {
            editorState.availableFields = [];
            return;
        }

        // Fetch columns for each model and tag them with model name
        const fieldsPromises = models.map(async (model) => {
            try {
                const response = await fetch(`/api/tables/${model}/columns?schema=public`);
                const data = await response.json();
                // Tag each field with its model
                return (data.columns || []).map(field => ({
                    ...field,
                    model: model
                }));
            } catch (error) {
                console.error(`Error fetching columns for ${model}:`, error);
                return [];
            }
        });

        const allFieldsArrays = await Promise.all(fieldsPromises);

        // Flatten all fields (keep duplicates with different models)
        const allFields = allFieldsArrays.flat();

        // Sort by model first, then by field name
        editorState.availableFields = allFields.sort((a, b) => {
            if (a.model !== b.model) {
                return a.model.localeCompare(b.model);
            }
            return a.name.localeCompare(b.name);
        });
    } catch (error) {
        console.error('Error fetching available fields:', error);
        editorState.availableFields = [];
    }
}

// Tab Management Functions
function renderEditorTabs() {
    const tabsContainer = document.getElementById('editor-tabs-container');
    if (!tabsContainer) {
        console.warn('Tabs container not found in editor');
        return;
    }

    tabsContainer.innerHTML = '';

    // Create tab bar with add button
    const tabBar = document.createElement('div');
    tabBar.className = 'editor-tab-bar';
    tabBar.style.cssText = 'display: flex; gap: 8px; align-items: center; margin-bottom: 24px; flex-wrap: wrap;';

    // Render tabs
    editorState.tabs.forEach(tab => {
        const tabBtn = document.createElement('button');
        tabBtn.className = 'editor-tab-btn';
        tabBtn.dataset.tabId = tab.id;
        tabBtn.style.cssText = 'display: flex; align-items: center; gap: 8px; padding: 10px 16px; background: var(--color-bg-secondary); border: 2px solid transparent; border-radius: 8px; cursor: pointer; transition: all 0.2s; position: relative;';

        if (tab.id === editorState.currentTabId) {
            tabBtn.classList.add('active');
            tabBtn.style.background = 'var(--color-primary)';
            tabBtn.style.color = 'white';
            tabBtn.style.borderColor = 'var(--color-primary)';
        }

        const chartCount = tab.charts ? tab.charts.length : 0;

        tabBtn.innerHTML = `
            <span class="tab-name" style="font-weight: 600;">${tab.name}</span>
            <span class="tab-chart-count" style="background: ${tab.id === editorState.currentTabId ? 'rgba(255,255,255,0.3)' : 'var(--color-bg-tertiary)'}; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem;">${chartCount}</span>
            <button class="tab-edit-btn" onclick="event.stopPropagation(); renameEditorTab('${tab.id}')" title="Rename tab" style="background: none; border: none; cursor: pointer; padding: 4px; font-size: 1rem; opacity: 0.7; line-height: 1;">✏️</button>
            ${editorState.tabs.length > 1 ? `<button class="tab-delete-btn" onclick="event.stopPropagation(); deleteEditorTab('${tab.id}')" title="Delete tab" style="background: none; border: none; cursor: pointer; padding: 4px; font-size: 1rem; opacity: 0.7; line-height: 1;">✕</button>` : ''}
        `;

        tabBtn.onclick = (e) => {
            console.log('Tab clicked:', tab.id);
            switchDashboardEditorTab(tab.id);
        };
        tabBar.appendChild(tabBtn);
    });

    // Add "New Tab" button
    const newTabBtn = document.createElement('button');
    newTabBtn.className = 'editor-new-tab-btn';
    newTabBtn.innerHTML = '+ New Tab';
    newTabBtn.style.cssText = 'padding: 10px 16px; background: var(--color-bg-secondary); border: 2px dashed var(--color-border); border-radius: 8px; cursor: pointer; color: var(--color-text-secondary); transition: all 0.2s;';
    newTabBtn.onclick = createNewEditorTab;
    tabBar.appendChild(newTabBtn);

    tabsContainer.appendChild(tabBar);
}

function switchDashboardEditorTab(tabId) {
    console.log('Switching to dashboard tab:', tabId, 'Current:', editorState.currentTabId);
    editorState.currentTabId = tabId;
    renderEditorTabs();
    renderEditorCharts();
}

function createNewEditorTab() {
    const tabName = prompt('Enter name for new tab:', 'New Tab');
    if (!tabName) return;

    const newTabId = `tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const newTab = {
        id: newTabId,
        name: tabName,
        charts: []
    };

    editorState.tabs.push(newTab);
    editorState.currentTabId = newTabId;
    renderEditorTabs();
    renderEditorCharts();
    showToast(`Created tab "${tabName}"`, 'success');
}

function renameEditorTab(tabId) {
    const tab = editorState.tabs.find(t => t.id === tabId);
    if (!tab) return;

    const newName = prompt('Enter new name for tab:', tab.name);
    if (!newName || newName === tab.name) return;

    tab.name = newName;
    renderEditorTabs();
    showToast(`Renamed tab to "${newName}"`, 'success');
}

function deleteEditorTab(tabId) {
    if (editorState.tabs.length <= 1) {
        showToast('Cannot delete the only tab', 'error');
        return;
    }

    const tab = editorState.tabs.find(t => t.id === tabId);
    if (!tab) return;

    const chartCount = tab.charts ? tab.charts.length : 0;
    const confirmMsg = chartCount > 0
        ? `Delete tab "${tab.name}" and its ${chartCount} chart(s)?`
        : `Delete tab "${tab.name}"?`;

    if (!confirm(confirmMsg)) return;

    // Remove the tab
    editorState.tabs = editorState.tabs.filter(t => t.id !== tabId);

    // Switch to first tab if we deleted the current tab
    if (editorState.currentTabId === tabId) {
        editorState.currentTabId = editorState.tabs[0].id;
    }

    renderEditorTabs();
    renderEditorCharts();
    showToast(`Deleted tab "${tab.name}"`, 'success');
}

function renderEditorCharts() {
    const grid = document.getElementById('editor-chart-grid');
    grid.innerHTML = '';

    // Get charts for the current tab
    const currentTab = editorState.tabs.find(tab => tab.id === editorState.currentTabId);
    const tabCharts = currentTab ? currentTab.charts : [];

    if (tabCharts.length === 0) {
        grid.innerHTML = `
            <div class="empty-editor-state">
                <div class="empty-editor-icon">📊</div>
                <div class="empty-editor-text">No charts in this tab yet</div>
                <div style="font-size: 0.875rem; color: var(--color-text-secondary);">Add charts from the sidebar</div>
            </div>
        `;
        return;
    }

    tabCharts.forEach((chart, index) => {
        const chartCard = document.createElement('div');
        chartCard.className = 'editor-chart-card';
        chartCard.draggable = true;
        chartCard.dataset.index = index;

        const canvasId = `editor-chart-preview-${index}`;

        const currentSize = chart.size || 'medium';

        // Apply custom dimensions if saved
        let cardWidth = chart.customWidth ? `${chart.customWidth}px` : '300px';
        let cardHeight = chart.customHeight ? `${chart.customHeight}px` : '350px';

        chartCard.style.cssText = `width: ${cardWidth}; height: ${cardHeight}; min-width: 250px; min-height: 200px; position: relative;`;

        chartCard.innerHTML = `
            <div class="editor-chart-header">
                <div class="editor-chart-title">${chart.title || chart.id}</div>
                <button class="editor-chart-remove" onclick="removeChartFromEditor(${index})" title="Remove chart">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                        <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                </button>
            </div>
            <div class="editor-chart-preview-wrapper" style="flex: 1; background: var(--color-bg-secondary); border-radius: 8px; padding: 12px; margin-bottom: 12px; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden;">
                <canvas id="${canvasId}" style="max-width: 100%; max-height: 100%;"></canvas>
            </div>
            <div class="editor-chart-info">Model: ${chart.model}</div>
            <div class="editor-chart-info">${chart.x_axis} vs ${chart.y_axis} (${chart.aggregation || 'count'})</div>
            <span class="editor-chart-type">${chart.type}</span>
        `;

        // Add drag-to-resize corner handle to the entire chart card
        const resizeHandleCorner = document.createElement('div');
        resizeHandleCorner.style.cssText = 'position: absolute; right: 0; bottom: 0; width: 16px; height: 16px; cursor: nwse-resize; background: linear-gradient(135deg, transparent 50%, rgba(102, 126, 234, 0.5) 50%); opacity: 0; transition: opacity 0.2s; z-index: 10;';
        resizeHandleCorner.title = 'Drag to resize';

        // Prevent drag when clicking resize handle
        resizeHandleCorner.addEventListener('dragstart', (e) => {
            e.preventDefault();
            e.stopPropagation();
            return false;
        });

        // Implement drag-to-resize functionality
        let isResizing = false;
        let startX, startY, startWidth, startHeight;
        let mouseMoveHandler = null;
        let mouseUpHandler = null;
        let animationFrameId = null;

        resizeHandleCorner.addEventListener('mousedown', (e) => {
            e.preventDefault();
            e.stopPropagation();

            // Check global resize state
            if (window.chartResizeState && window.chartResizeState.isResizing) {
                return; // Another chart is already being resized
            }

            isResizing = true;
            startX = e.clientX;
            startY = e.clientY;
            startWidth = chartCard.offsetWidth;
            startHeight = chartCard.offsetHeight;

            // Set global resize state
            if (!window.chartResizeState) {
                window.chartResizeState = {};
            }
            window.chartResizeState.isResizing = true;
            window.chartResizeState.currentChart = chartCard;

            // Temporarily disable draggable during resize
            chartCard.setAttribute('draggable', 'false');
            document.body.style.cursor = 'nwse-resize';
            document.body.style.userSelect = 'none';

            // Define handlers that will be removed later
            mouseMoveHandler = (e) => {
                if (!isResizing) return;

                // Cancel previous animation frame
                if (animationFrameId) {
                    cancelAnimationFrame(animationFrameId);
                }

                // Use requestAnimationFrame for smooth performance
                animationFrameId = requestAnimationFrame(() => {
                    const deltaX = e.clientX - startX;
                    const deltaY = e.clientY - startY;

                    const newWidth = Math.max(250, Math.min(5000, startWidth + deltaX));
                    const newHeight = Math.max(200, Math.min(5000, startHeight + deltaY));

                    chartCard.style.width = newWidth + 'px';
                    chartCard.style.height = newHeight + 'px';
                });
            };

            mouseUpHandler = () => {
                if (isResizing) {
                    isResizing = false;

                    // Clear global resize state
                    if (window.chartResizeState) {
                        window.chartResizeState.isResizing = false;
                        window.chartResizeState.currentChart = null;
                    }

                    // Cancel any pending animation frame
                    if (animationFrameId) {
                        cancelAnimationFrame(animationFrameId);
                        animationFrameId = null;
                    }

                    // Re-enable dragging after a small delay to prevent accidental drags
                    setTimeout(() => {
                        chartCard.setAttribute('draggable', 'true');
                    }, 100);

                    document.body.style.cursor = '';
                    document.body.style.userSelect = '';

                    // Save the new dimensions to chart config
                    const newWidth = chartCard.offsetWidth;
                    const newHeight = chartCard.offsetHeight;
                    chart.customWidth = newWidth;
                    chart.customHeight = newHeight;

                    console.log(`Chart ${chart.id} resized in edit mode: ${newWidth}x${newHeight}`);
                    showToast(`Chart resized. Save dashboard to apply changes.`, 'info');

                    // CRITICAL: Remove event listeners to prevent memory leak
                    document.removeEventListener('mousemove', mouseMoveHandler);
                    document.removeEventListener('mouseup', mouseUpHandler);
                }
            };

            // Add listeners only when needed
            document.addEventListener('mousemove', mouseMoveHandler);
            document.addEventListener('mouseup', mouseUpHandler);
        });

        chartCard.onmouseenter = () => {
            resizeHandleCorner.style.opacity = '1';
        };
        chartCard.onmouseleave = () => {
            if (!isResizing) {
                resizeHandleCorner.style.opacity = '0';
            }
        };

        chartCard.appendChild(resizeHandleCorner);

        // Add drag event listeners
        chartCard.addEventListener('dragstart', handleDragStart);
        chartCard.addEventListener('dragend', handleDragEnd);
        chartCard.addEventListener('dragover', handleDragOver);
        chartCard.addEventListener('drop', handleDrop);
        chartCard.addEventListener('dragenter', handleDragEnter);
        chartCard.addEventListener('dragleave', handleDragLeave);

        grid.appendChild(chartCard);

        // Render the chart preview
        renderChartPreview(canvasId, chart);
    });
}

function renderAvailableCharts() {
    const list = document.getElementById('available-charts-list');
    list.innerHTML = '';

    // Get IDs of charts that are assigned to tabs in THIS dashboard
    const chartsInTabsIds = editorState.tabs.flatMap(tab => tab.charts.map(c => c.id));

    // Filter to show:
    // 1. Charts from currentCharts (this dashboard) that are NOT in any tab (unassigned)
    // 2. Charts from availableCharts that are NOT in currentCharts (from other dashboards or unassigned globally)
    const currentChartIds = editorState.currentCharts.map(c => c.id);
    const unassignedInDashboard = editorState.currentCharts.filter(c => !chartsInTabsIds.includes(c.id));
    const chartsFromOther = editorState.availableCharts.filter(c => !currentChartIds.includes(c.id));
    const availableCharts = [...unassignedInDashboard, ...chartsFromOther];

    if (availableCharts.length === 0) {
        list.innerHTML = '<p style="color: var(--color-text-secondary); font-size: 0.875rem; text-align: center; padding: 1rem;">All charts are in use</p>';
        return;
    }

    availableCharts.forEach((chart, index) => {
        const item = document.createElement('div');
        item.className = 'available-chart-item';
        item.onclick = () => addChartToEditor(chart);

        // Create a unique canvas ID for this chart preview
        const canvasId = `preview-chart-${index}`;

        item.innerHTML = `
            <div class="available-chart-name">${chart.title || chart.id}</div>
            <div class="available-chart-preview" style="height: 120px; margin: 8px 0; position: relative;">
                <canvas id="${canvasId}"></canvas>
            </div>
            <div class="available-chart-type">${chart.type} • ${chart.model}</div>
        `;

        list.appendChild(item);

        // Render mini preview chart after the element is in the DOM
        // Use requestAnimationFrame to ensure DOM is ready and prevent blocking
        requestAnimationFrame(() => {
            renderChartPreview(canvasId, chart).catch(err => {
                console.error(`Failed to render preview for ${chart.id}:`, err);
                // Show a placeholder on error
                const canvas = document.getElementById(canvasId);
                if (canvas) {
                    const ctx = canvas.getContext('2d');
                    ctx.font = '12px sans-serif';
                    ctx.fillStyle = '#999';
                    ctx.textAlign = 'center';
                    ctx.fillText('Preview unavailable', canvas.width / 2, canvas.height / 2);
                }
            });
        });
    });
}

// Render a mini preview of the chart
async function renderChartPreview(canvasId, chartConfig) {
    try {
        // Check if canvas still exists
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`Canvas ${canvasId} not found`);
            return;
        }

        // Skip charts with calculation fields (they don't have x/y axes)
        if (chartConfig.calculation) {
            const ctx = canvas.getContext('2d');
            ctx.font = '11px sans-serif';
            ctx.fillStyle = '#999';
            ctx.textAlign = 'center';
            ctx.fillText('Calculated metric', canvas.width / 2, canvas.height / 2);
            return;
        }

        // Fetch chart data
        const queryPayload = {
            table: chartConfig.model,
            type: chartConfig.type,
            x_axis: chartConfig.x_axis,
            y_axis: chartConfig.y_axis,
            metric: chartConfig.metric,
            metrics: chartConfig.metrics,
            aggregation: chartConfig.aggregation || 'count',
            filters: chartConfig.filters || {}
        };

        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(queryPayload)
        });

        // Check if response is OK
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Validate data
        if (!data || !data.data || data.data.length === 0) {
            console.warn(`No data for chart ${chartConfig.id}`);
            return;
        }

        // Check if canvas still exists after async operation
        const ctx = document.getElementById(canvasId);
        if (!ctx) {
            console.warn(`Canvas ${canvasId} removed during fetch`);
            return;
        }

        // Prepare data for Chart.js
        const labels = data.data.map(row => row.label || row[chartConfig.x_axis]);
        const values = data.data.map(row => row.value || row[chartConfig.y_axis]);

        // Create mini chart
        new Chart(ctx, {
            type: chartConfig.type === 'doughnut' ? 'doughnut' : chartConfig.type,
            data: {
                labels: labels.slice(0, 5), // Show only first 5 items for preview
                datasets: [{
                    data: values.slice(0, 5),
                    backgroundColor: [
                        'rgba(102, 126, 234, 0.8)',
                        'rgba(118, 75, 162, 0.8)',
                        'rgba(237, 100, 166, 0.8)',
                        'rgba(255, 154, 158, 0.8)',
                        'rgba(250, 208, 196, 0.8)'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                },
                scales: chartConfig.type === 'pie' || chartConfig.type === 'doughnut' ? {} : {
                    x: { display: false },
                    y: { display: false }
                },
                animation: false // Disable animation for previews
            }
        });
    } catch (error) {
        console.error(`Error rendering chart preview for ${chartConfig.id}:`, error);
        // Don't throw - just log and continue
    }
}

async function addChartToEditor(chart) {
    // Add chart to the current tab
    const currentTab = editorState.tabs.find(tab => tab.id === editorState.currentTabId);
    if (currentTab) {
        currentTab.charts.push(chart);

        // Only add to currentCharts if it's not already there (e.g., coming from another dashboard)
        const chartExists = editorState.currentCharts.some(c => c.id === chart.id);
        if (!chartExists) {
            editorState.currentCharts.push(chart);
        }

        // Refresh available fields immediately so filters can use them
        await fetchAvailableFields();

        renderEditorTabs();
        renderEditorCharts();
        renderAvailableCharts();
        showToast(`Added "${chart.title || chart.id}" to tab "${currentTab.name}"`, 'success');
    }
}

async function removeChartFromEditor(index) {
    // Remove chart from current tab
    const currentTab = editorState.tabs.find(tab => tab.id === editorState.currentTabId);
    if (!currentTab || index < 0 || index >= currentTab.charts.length) {
        console.error(`Invalid index ${index} for tab charts`, currentTab);
        return;
    }

    const chart = currentTab.charts[index];
    currentTab.charts.splice(index, 1);

    // Check if this chart exists in any other tabs
    const chartExistsInOtherTabs = editorState.tabs.some(tab =>
        tab.id !== editorState.currentTabId && tab.charts.some(c => c.id === chart.id)
    );

    // If chart doesn't exist in any other tabs, remove it from currentCharts
    if (!chartExistsInOtherTabs) {
        const chartIndex = editorState.currentCharts.findIndex(c => c.id === chart.id);
        if (chartIndex !== -1) {
            editorState.currentCharts.splice(chartIndex, 1);
        }

        // Refresh available fields since we removed a chart
        await fetchAvailableFields();

        // Check if any filters reference fields from the removed chart's model
        const removedModel = chart.model;
        if (removedModel) {
            const affectedFilters = editorState.currentFilters.filter(f => f.model === removedModel);

            // Check if any remaining charts use this model
            const modelStillInUse = editorState.currentCharts.some(c => c.model === removedModel);

            if (!modelStillInUse && affectedFilters.length > 0) {
                // Show warning about filters that will lose their fields
                const filterNames = affectedFilters.map(f => f.label || f.field).join(', ');
                showToast(`Warning: Filters (${filterNames}) reference model "${removedModel}" which is no longer in this dashboard`, 'warning');
            }
        }
    }

    renderEditorTabs();
    renderEditorCharts();
    renderAvailableCharts();
    renderDashboardFilters();
    showToast(`Removed "${chart.title || chart.id}" from tab`, 'info');
}

function updateChartSize(index, size) {
    // Update chart size in current tab
    const currentTab = editorState.tabs.find(tab => tab.id === editorState.currentTabId);
    if (!currentTab || index < 0 || index >= currentTab.charts.length) {
        console.error(`Invalid index ${index} for tab charts`, currentTab);
        return;
    }

    const chart = currentTab.charts[index];
    chart.size = size;

    // Update the size in currentCharts as well if it exists there
    const currentChart = editorState.currentCharts.find(c => c.id === chart.id);
    if (currentChart) {
        currentChart.size = size;
    }

    // Re-render to show updated size (dropdown will show new selection)
    renderEditorCharts();

    const sizeLabels = {
        'small': '1/4 width',
        'medium': '1/2 width',
        'large': '3/4 width',
        'full': 'full width'
    };
    showToast(`Updated "${chart.title || chart.id}" to ${sizeLabels[size]}`, 'success');
}

// Save custom chart dimensions to database
async function saveChartDimensions(chartId, dashboardId, width, height) {
    // Client-side validation
    if (width < 250 || width > 5000 || height < 200 || height > 5000) {
        console.error('Invalid dimensions:', width, height);
        showToast('Chart dimensions must be between 250-5000px width and 200-5000px height', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/dashboards/${dashboardId}/charts/${chartId}/dimensions`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                customWidth: width,
                customHeight: height
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Server returned ${response.status}`);
        }

        console.log(`Saved dimensions for chart ${chartId}: ${width}x${height}`);
    } catch (error) {
        console.error('Error saving chart dimensions:', error);
        showToast(`Failed to save chart size: ${error.message}`, 'error', 5000);
    }
}

// Drag and Drop handlers
function handleDragStart(e) {
    editorState.draggedIndex = parseInt(e.target.dataset.index);
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
}

function handleDragEnd(e) {
    e.target.classList.remove('dragging');
    document.querySelectorAll('.editor-chart-card').forEach(card => {
        card.classList.remove('drag-over');
    });
}

function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    e.dataTransfer.dropEffect = 'move';
    return false;
}

function handleDragEnter(e) {
    if (e.target.classList.contains('editor-chart-card')) {
        e.target.classList.add('drag-over');
    }
}

function handleDragLeave(e) {
    if (e.target.classList.contains('editor-chart-card')) {
        e.target.classList.remove('drag-over');
    }
}

function handleDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }

    const targetIndex = parseInt(e.target.closest('.editor-chart-card').dataset.index);

    if (editorState.draggedIndex !== targetIndex) {
        // Reorder charts array
        const draggedChart = editorState.currentCharts[editorState.draggedIndex];
        editorState.currentCharts.splice(editorState.draggedIndex, 1);
        editorState.currentCharts.splice(targetIndex, 0, draggedChart);

        renderEditorCharts();
        showToast('Chart reordered', 'info');
    }

    return false;
}

async function saveDashboardEdit() {
    try {
        // Calculate unassigned charts (in currentCharts but not in any tab)
        const chartsInTabs = editorState.tabs.flatMap(tab => tab.charts.map(c => c.id));
        const unassignedCharts = editorState.currentCharts.filter(c => !chartsInTabs.includes(c.id));

        const response = await fetch(`/api/dashboards/${editorState.dashboardId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                tabs: editorState.tabs,  // Charts assigned to tabs
                charts: unassignedCharts,  // Charts in dashboard but not assigned to any tab
                filters: editorState.currentFilters
            })
        });

        const result = await response.json();

        if (response.ok) {
            showToast('Dashboard saved successfully', 'success');

            // Clear any cached dashboard data to force reload
            const dashboardCard = document.getElementById('dashboard-' + editorState.dashboardId);
            if (dashboardCard) {
                const chartsContainer = dashboardCard.querySelector('.dashboard-details');
                if (chartsContainer) {
                    chartsContainer.innerHTML = '';  // Clear cached charts
                }
            }

            // Return to dashboards view
            setTimeout(() => {
                cancelDashboardEdit();
                // Reload dashboards to show updated sizes
                loadDashboards();
            }, 800);
        } else {
            showToast(result.message || 'Failed to save dashboard', 'error');
        }
    } catch (error) {
        console.error('Error saving dashboard:', error);
        showToast('Failed to save dashboard', 'error');
    }
}

function cancelDashboardEdit() {
    // Clear editor state
    editorState = {
        dashboardId: null,
        dashboardName: null,
        currentCharts: [],
        availableCharts: [],
        draggedIndex: null,
        currentFilters: []
    };

    // Hide editor view and reset inline styles
    const editorView = document.getElementById('dashboard-editor-view');
    if (editorView) {
        editorView.style.display = 'none';
        editorView.classList.remove('active');
    }

    // Reset all view inline styles and use switchView to navigate back
    document.querySelectorAll('.view-content').forEach(view => {
        view.style.display = '';  // Remove inline display style
    });

    switchView('dashboards');
}

// ============= Dashboard Settings Management =============

function openDashboardSettingsModal() {
    // Load current dashboard data into the form
    if (editorState.dashboardData) {
        document.getElementById('dashboardSettingsName').value = editorState.dashboardData.name || '';
        document.getElementById('dashboardSettingsDescription').value = editorState.dashboardData.description || '';
    }

    // Open the modal
    const modal = document.getElementById('dashboardSettingsModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

async function saveDashboardSettings() {
    const name = document.getElementById('dashboardSettingsName').value.trim();
    const description = document.getElementById('dashboardSettingsDescription').value.trim();

    // Validate name is not empty
    if (!name) {
        showToast('Dashboard name is required', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/dashboards/${editorState.dashboardId}/metadata`, {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name: name,
                description: description
            })
        });

        const result = await response.json();

        if (response.ok) {
            // Update local state
            editorState.dashboardName = name;
            if (editorState.dashboardData) {
                editorState.dashboardData.name = name;
                editorState.dashboardData.description = description;
            }

            // Update the header title
            document.getElementById('editor-dashboard-name').textContent = `Edit: ${name}`;

            showToast('Dashboard settings updated successfully', 'success');
            closeModal('dashboardSettingsModal');
        } else {
            showToast(result.detail || 'Failed to update dashboard settings', 'error');
        }
    } catch (error) {
        console.error('Error updating dashboard settings:', error);
        showToast('Failed to update dashboard settings', 'error');
    }
}

// ============= Dashboard Filter Management =============

function renderDashboardFilters() {
    const container = document.getElementById('dashboard-filters-editor');
    if (!container) return;

    if (editorState.currentFilters.length === 0) {
        container.innerHTML = `
            <div style="color: var(--text-tertiary); font-size: 0.875rem; padding: 20px; text-align: center;">
                No filters configured. Click "Add Filter" to create interactive filters for your dashboard.
            </div>
        `;
        return;
    }

    // Generate field options HTML for datalist - showing model and field type
    const generateFieldDatalist = (filterIndex) => {
        const datalistId = `filter-fields-${filterIndex}`;
        const options = editorState.availableFields.map(field =>
            `<option value="${field.name}" data-model="${field.model}" label="${field.model}.${field.name} (${field.type})">`
        ).join('');
        return { datalistId, options };
    };

    // Generate tab checkboxes HTML
    const generateTabCheckboxes = (filter, filterIndex) => {
        const applyToTabs = filter.apply_to_tabs || [];

        return editorState.tabs.map(tab => {
            const isChecked = applyToTabs.length === 0 || applyToTabs.includes(tab.id);
            return `
                <label style="display: inline-flex; align-items: center; margin-right: 16px; cursor: pointer;">
                    <input type="checkbox"
                        ${isChecked ? 'checked' : ''}
                        onchange="updateFilterTabs(${filterIndex}, '${tab.id}', this.checked)"
                        style="margin-right: 6px; cursor: pointer;">
                    <span style="font-size: 0.875rem;">${tab.name}</span>
                </label>
            `;
        }).join('');
    };

    container.innerHTML = editorState.currentFilters.map((filter, index) => {
        const selectedField = filter.field || '';
        const expression = filter.expression || '';
        const applyToTabs = filter.apply_to_tabs || [];
        const appliesTo = applyToTabs.length === 0 ? 'All tabs' : `${applyToTabs.length} tab(s)`;
        const { datalistId, options } = generateFieldDatalist(index);

        return `
            <div style="display: flex; gap: 12px; align-items: flex-start; padding: 12px; background: var(--color-bg-secondary); border-radius: 8px; margin-bottom: 8px;">
                <div style="flex: 1;">
                    <input type="text" placeholder="Filter Label (e.g., 'Year')" value="${filter.label || ''}"
                        onchange="updateFilterLabel(${index}, this.value)"
                        style="width: 100%; padding: 8px; border: 1px solid var(--color-border); border-radius: 6px; margin-bottom: 8px;">
                    <input type="text"
                        list="${datalistId}"
                        placeholder="Type to search field name..."
                        value="${selectedField}"
                        onchange="updateFilterFieldFromInput(${index}, this.value)"
                        oninput="this.setAttribute('data-changed', 'true')"
                        style="width: 100%; padding: 8px; border: 1px solid var(--color-border); border-radius: 6px; margin-bottom: 8px;">
                    <datalist id="${datalistId}">
                        ${options}
                    </datalist>
                    <input type="text" placeholder="SQL Expression (optional, e.g. 'EXTRACT(YEAR FROM order_date)')" value="${expression}"
                        onchange="updateFilterExpression(${index}, this.value)"
                        style="width: 100%; padding: 8px; border: 1px solid var(--color-border); border-radius: 6px; font-family: monospace; font-size: 0.85rem; margin-bottom: 8px;">

                    <div style="margin-top: 12px; padding: 8px; background: white; border-radius: 6px; border: 1px solid var(--color-border);">
                        <div style="font-size: 0.75rem; font-weight: 600; color: var(--color-text-secondary); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em;">
                            Apply to tabs <span style="color: var(--color-primary); font-weight: 500; text-transform: none;">(${appliesTo})</span>
                        </div>
                        <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                            ${generateTabCheckboxes(filter, index)}
                        </div>
                        <div style="font-size: 0.7rem; color: var(--text-tertiary); margin-top: 6px;">
                            Uncheck all to apply to all tabs
                        </div>
                    </div>
                </div>
                <button onclick="removeDashboardFilter(${index})"
                    style="padding: 8px 12px; background: var(--color-error); color: white; border: none; border-radius: 6px; cursor: pointer; align-self: flex-start;">
                    Remove
                </button>
            </div>
        `;
    }).join('');
}

function addDashboardFilter() {
    editorState.currentFilters.push({
        field: '',
        label: '',
        expression: '',
        apply_to_tabs: []  // Empty array means apply to all tabs
    });
    renderDashboardFilters();
}

function updateFilterLabel(index, value) {
    if (editorState.currentFilters[index]) {
        editorState.currentFilters[index].label = value;
    }
}

function updateFilterField(index, selectElement) {
    if (editorState.currentFilters[index]) {
        const selectedOption = selectElement.options[selectElement.selectedIndex];
        editorState.currentFilters[index].field = selectElement.value;
        editorState.currentFilters[index].model = selectedOption.getAttribute('data-model') || '';

        // Auto-populate label if empty
        if (!editorState.currentFilters[index].label && selectElement.value) {
            editorState.currentFilters[index].label = selectElement.value.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            renderDashboardFilters();
        }
    }
}

function updateFilterFieldFromInput(index, fieldName) {
    if (editorState.currentFilters[index]) {
        // Find the matching field from availableFields to get the model
        const matchingField = editorState.availableFields.find(f => f.name === fieldName);

        editorState.currentFilters[index].field = fieldName;
        editorState.currentFilters[index].model = matchingField ? matchingField.model : '';

        console.log(`Updated filter ${index}: field=${fieldName}, model=${matchingField?.model || 'unknown'}`);
    }
}

function updateFilterExpression(index, value) {
    if (editorState.currentFilters[index]) {
        editorState.currentFilters[index].expression = value;
    }
}

function updateFilterTabs(filterIndex, tabId, isChecked) {
    if (!editorState.currentFilters[filterIndex]) return;

    const filter = editorState.currentFilters[filterIndex];

    // Initialize apply_to_tabs if it doesn't exist
    if (!filter.apply_to_tabs) {
        filter.apply_to_tabs = [];
    }

    if (isChecked) {
        // Add tab if not already included
        if (!filter.apply_to_tabs.includes(tabId)) {
            filter.apply_to_tabs.push(tabId);
        }

        // If all tabs are now checked, clear the array (means apply to all)
        if (filter.apply_to_tabs.length === editorState.tabs.length) {
            filter.apply_to_tabs = [];
        }
    } else {
        // Remove tab from the array
        if (filter.apply_to_tabs.length === 0) {
            // Was applying to all tabs, now need to explicitly list all except this one
            filter.apply_to_tabs = editorState.tabs
                .filter(tab => tab.id !== tabId)
                .map(tab => tab.id);
        } else {
            // Remove the specific tab
            filter.apply_to_tabs = filter.apply_to_tabs.filter(id => id !== tabId);
        }
    }

    // Re-render to update the UI
    renderDashboardFilters();
}

function removeDashboardFilter(index) {
    editorState.currentFilters.splice(index, 1);
    renderDashboardFilters();
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
    } else if (tabName === 'chart-builder') {
        loadChartConnections();
        loadChartDashboards();
    }
}

// Load Dashboards with Charts
async function loadDashboards() {
    try {
        const response = await fetch('/api/dashboards');
        const data = await response.json();

        // Store all dashboards for search
        allDashboardsData = data.dashboards;

        // Apply search filter
        let filteredDashboards = allDashboardsData;
        if (currentDashboardsSearchTerm) {
            filteredDashboards = filterListItems(currentDashboardsSearchTerm, allDashboardsData, ['name', 'description', 'created_by']);
        }

        const dashboardsList = document.getElementById('dashboards-list');

        if (filteredDashboards.length === 0) {
            dashboardsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📊</div>
                    <h3>${currentDashboardsSearchTerm ? 'No dashboards found' : 'No dashboards configured'}</h3>
                    <p>${currentDashboardsSearchTerm ? 'No dashboards match your search criteria.' : 'Create a new dashboard to organize your charts. You can also create standalone charts that aren\'t assigned to any dashboard.'}</p>
                </div>
            `;
            return;
        }

        // Clear the list first
        dashboardsList.innerHTML = '';

        // Display based on view mode
        if (dashboardsViewMode === 'table') {
            // Table view - structured data table
            dashboardsList.className = 'dashboards-table-view';

            const table = document.createElement('table');
            table.className = 'view-table';
            table.style.borderCollapse = 'separate';
            table.style.borderSpacing = '0';
            table.innerHTML = `
                <thead>
                    <tr>
                        <th style="width: 28%; padding: 12px 16px; text-align: left;">Dashboard Name</th>
                        <th style="width: 32%; padding: 12px 16px; text-align: left;">Description</th>
                        <th style="width: 8%; padding: 12px 16px; text-align: center;">Charts</th>
                        <th style="width: 12%; padding: 12px 16px; text-align: left;">Created By</th>
                        <th style="width: 12%; padding: 12px 16px; text-align: left;">Tags</th>
                        <th style="width: 8%; padding: 12px 16px; text-align: right;">Actions</th>
                    </tr>
                </thead>
                <tbody></tbody>
            `;

            const tbody = table.querySelector('tbody');

            filteredDashboards.forEach(dashboard => {
                // Format tags
                const tags = dashboard.tags || [];
                const tagsHTML = tags.length > 0
                    ? tags.map(tag => `<span class="tag-badge">${tag}</span>`).join(' ')
                    : '<span style="color: #9ca3af; font-size: 0.75rem;">None</span>';

                const row = document.createElement('tr');
                row.style.borderBottom = '1px solid #e5e7eb';
                row.innerHTML = `
                    <td style="padding: 16px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: middle;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 1.1rem; flex-shrink: 0;">📊</span>
                            <strong style="color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${dashboard.name}</strong>
                        </div>
                    </td>
                    <td style="padding: 16px; max-width: 300px; vertical-align: middle;">
                        <div style="color: #6b7280; font-size: 0.875rem; line-height: 1.5; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">
                            ${dashboard.description || '<span style="color: #9ca3af; font-style: italic;">No description</span>'}
                        </div>
                    </td>
                    <td style="padding: 16px; text-align: center; white-space: nowrap; vertical-align: middle;">
                        <span class="chart-count-badge">${getDashboardCharts(dashboard)?.length || 0}</span>
                    </td>
                    <td style="padding: 16px; white-space: nowrap; vertical-align: middle;">
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <span style="font-size: 0.9rem; flex-shrink: 0;">👤</span>
                            <span style="color: #6b7280; font-size: 0.875rem; overflow: hidden; text-overflow: ellipsis;">${dashboard.owner || dashboard.created_by || 'System'}</span>
                        </div>
                    </td>
                    <td style="padding: 16px; white-space: nowrap; vertical-align: middle;">
                        <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                            ${tagsHTML}
                        </div>
                    </td>
                    <td style="padding: 16px; text-align: right; white-space: nowrap; vertical-align: middle;">
                        <div style="display: flex; gap: 8px; justify-content: flex-end;">
                            <button class="icon-btn-small" onclick="event.stopPropagation(); openDashboardEditor('${dashboard.id}', '${dashboard.name}')" title="Edit Dashboard">✏️</button>
                            <button class="icon-btn-small" onclick="event.stopPropagation(); openDashboardInTab('${dashboard.id}')" title="Open in new tab">🔗</button>
                            <button class="icon-btn-small" onclick="event.stopPropagation(); deleteDashboard('${dashboard.id}', '${dashboard.name}')" title="Delete Dashboard" style="color: #dc2626;">🗑️</button>
                        </div>
                    </td>
                `;

                row.style.cursor = 'pointer';
                row.style.transition = 'background-color 0.2s';
                row.onmouseover = () => row.style.backgroundColor = '#f9fafb';
                row.onmouseout = () => row.style.backgroundColor = 'transparent';
                row.onclick = () => openDashboardInTab(dashboard.id);

                tbody.appendChild(row);
            });

            dashboardsList.appendChild(table);
        } else {
            // Grid view - cards with expandable sections (original)
            dashboardsList.className = '';

            filteredDashboards.forEach(dashboard => {
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
                <span class="dashboard-id">${getDashboardCharts(dashboard)?.length || 0} charts</span>
            `;

            // Right side with action buttons
            const headerRight = document.createElement('div');
            headerRight.style.cssText = 'display: flex; gap: 8px; align-items: center;';
            headerRight.innerHTML = `
                <button class="icon-btn" onclick="event.stopPropagation(); openDashboardEditor('${dashboard.id}', '${dashboard.name}')" title="Edit Dashboard">
                    ✏️
                </button>
                <button class="icon-btn" onclick="event.stopPropagation(); openDashboardInTab('${dashboard.id}')" title="Open in new tab">
                    🔗
                </button>
                <button class="icon-btn" onclick="event.stopPropagation(); deleteDashboard('${dashboard.id}', '${dashboard.name}')" title="Delete Dashboard" style="color: #dc2626;">
                    🗑️
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
        }

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
            chartsContainer.style.display = 'block';
            chartsContainer.style.textAlign = 'left';
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
        if (!dashboard) {
            console.log('Dashboard not found:', dashboardId);
            container.innerHTML = '<p style="color: #888;">Dashboard not found</p>';
            return;
        }

        // Use dashboard.charts from the new database structure
        const dashboardCharts = dashboard.charts || [];
        if (dashboardCharts.length === 0) {
            console.log('No charts found for dashboard:', dashboardId);
            container.innerHTML = '<p style="color: #888;">No charts configured for this dashboard</p>';
            return;
        }

        console.log('Found dashboard with', dashboardCharts.length, 'charts');

        // Show loading state
        container.innerHTML = '<p style="color: #888;">⏳ Loading charts...</p>';

        // Wait a moment for loading state to be visible
        await new Promise(resolve => setTimeout(resolve, 100));

        // Clear container before adding charts
        container.innerHTML = '';

        // Render each chart sequentially to avoid overwhelming the server
        let chartsRendered = 0;
        for (const chartConfig of dashboardCharts) {
            // Add dashboard_id to chart config so edit button knows which dashboard it belongs to
            const chartWithDashboard = { ...chartConfig, dashboard_id: dashboardId };
            // Pass both filters and filter expressions to charts
            const filterExpressions = dashboardFilterExpressions[dashboardId] || {};
            await renderDashboardChart(chartWithDashboard, container, filters, filterExpressions);
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
async function renderDashboardChart(chartConfig, container, filters = {}, filterExpressions = {}) {
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

        // Create chart wrapper with size-based styling
        const size = chartConfig.size || 'medium';
        const sizeStyles = {
            small: 'width: calc(25% - 15px); min-width: 250px;',
            medium: 'width: calc(50% - 15px); min-width: 350px;',
            large: 'width: calc(75% - 15px); min-width: 450px;',
            full: 'width: 100%;'
        };

        const heightStyles = {
            small: '250px',
            medium: '300px',
            large: '400px',
            full: '450px'
        };

        const chartWrapper = document.createElement('div');
        // Apply custom width/height if saved, otherwise use size presets
        let widthStyle = sizeStyles[size];
        let heightStyle = '';

        if (chartConfig.customWidth) {
            widthStyle = `width: ${chartConfig.customWidth}px;`;
        }
        if (chartConfig.customHeight) {
            heightStyle = `height: ${chartConfig.customHeight}px;`;
        }

        chartWrapper.style.cssText = `background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); ${widthStyle} ${heightStyle} display: inline-flex; flex-direction: column; vertical-align: top; margin: 7.5px; position: relative; overflow: hidden;`;
        chartWrapper.style.minWidth = '250px';
        chartWrapper.style.maxWidth = '100%';
        chartWrapper.style.minHeight = '200px';
        chartWrapper.dataset.chartId = chartConfig.id;
        chartWrapper.dataset.dashboardId = chartConfig.dashboard_id;

        // Add resize handle indicators with drag functionality
        const resizeHandleCorner = document.createElement('div');
        resizeHandleCorner.style.cssText = 'position: absolute; right: 0; bottom: 0; width: 16px; height: 16px; cursor: nwse-resize; background: linear-gradient(135deg, transparent 50%, rgba(102, 126, 234, 0.5) 50%); opacity: 0; transition: opacity 0.2s; z-index: 10;';
        resizeHandleCorner.title = 'Drag to resize';

        // Implement drag-to-resize functionality
        let isResizing = false;
        let startX, startY, startWidth, startHeight;
        let mouseMoveHandler = null;
        let mouseUpHandler = null;
        let animationFrameId = null;

        resizeHandleCorner.addEventListener('mousedown', (e) => {
            e.preventDefault();
            e.stopPropagation();

            // Check global resize state
            if (window.chartResizeState && window.chartResizeState.isResizing) {
                return; // Another chart is already being resized
            }

            isResizing = true;
            startX = e.clientX;
            startY = e.clientY;
            startWidth = chartWrapper.offsetWidth;
            startHeight = chartWrapper.offsetHeight;

            // Set global resize state
            if (!window.chartResizeState) {
                window.chartResizeState = {};
            }
            window.chartResizeState.isResizing = true;
            window.chartResizeState.currentChart = chartWrapper;

            document.body.style.cursor = 'nwse-resize';
            document.body.style.userSelect = 'none';

            // Define handlers that will be removed later
            mouseMoveHandler = (e) => {
                if (!isResizing) return;

                // Cancel previous animation frame
                if (animationFrameId) {
                    cancelAnimationFrame(animationFrameId);
                }

                // Use requestAnimationFrame for smooth performance
                animationFrameId = requestAnimationFrame(() => {
                    const deltaX = e.clientX - startX;
                    const deltaY = e.clientY - startY;

                    const newWidth = Math.max(250, Math.min(5000, startWidth + deltaX));
                    const newHeight = Math.max(200, Math.min(5000, startHeight + deltaY));

                    chartWrapper.style.width = newWidth + 'px';
                    chartWrapper.style.height = newHeight + 'px';
                });
            };

            mouseUpHandler = () => {
                if (isResizing) {
                    isResizing = false;

                    // Clear global resize state
                    if (window.chartResizeState) {
                        window.chartResizeState.isResizing = false;
                        window.chartResizeState.currentChart = null;
                    }

                    // Cancel any pending animation frame
                    if (animationFrameId) {
                        cancelAnimationFrame(animationFrameId);
                        animationFrameId = null;
                    }

                    document.body.style.cursor = '';
                    document.body.style.userSelect = '';

                    // Save the new dimensions
                    const newWidth = chartWrapper.offsetWidth;
                    const newHeight = chartWrapper.offsetHeight;
                    chartConfig.customWidth = newWidth;
                    chartConfig.customHeight = newHeight;

                    // Trigger save after resize completes
                    saveChartDimensions(chartConfig.id, chartConfig.dashboard_id, newWidth, newHeight);

                    // CRITICAL: Remove event listeners to prevent memory leak
                    document.removeEventListener('mousemove', mouseMoveHandler);
                    document.removeEventListener('mouseup', mouseUpHandler);
                }
            };

            // Add listeners only when needed
            document.addEventListener('mousemove', mouseMoveHandler);
            document.addEventListener('mouseup', mouseUpHandler);
        });

        chartWrapper.onmouseenter = () => {
            resizeHandleCorner.style.opacity = '1';
        };
        chartWrapper.onmouseleave = () => {
            if (!isResizing) {
                resizeHandleCorner.style.opacity = '0';
            }
        };

        chartWrapper.appendChild(resizeHandleCorner);

        // Chart title with edit button
        const titleContainer = document.createElement('div');
        titleContainer.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;';

        // Left side: title + edit button
        const leftSide = document.createElement('div');
        leftSide.style.cssText = 'display: flex; align-items: center; gap: 8px;';

        const title = document.createElement('h4');
        title.style.cssText = 'margin: 0; color: #333; font-size: 1.1em;';
        title.textContent = chartConfig.title;

        const editBtn = document.createElement('button');
        editBtn.style.cssText = 'background: none; border: none; cursor: pointer; color: #667eea; font-size: 1.2em; padding: 4px 8px; border-radius: 4px; transition: background 0.2s;';
        editBtn.innerHTML = '✏️';
        editBtn.title = 'Edit chart';
        editBtn.onclick = (e) => {
            e.stopPropagation();
            editChart(chartConfig);
        };
        editBtn.onmouseover = function() { this.style.background = '#f0f0f0'; };
        editBtn.onmouseout = function() { this.style.background = 'none'; };

        leftSide.appendChild(title);
        leftSide.appendChild(editBtn);

        // Right side: View Query + Copy Query buttons
        const rightSide = document.createElement('div');
        rightSide.style.cssText = 'display: flex; align-items: center; gap: 4px;';

        const viewQueryBtn = document.createElement('button');
        viewQueryBtn.style.cssText = 'background: none; border: none; cursor: pointer; color: #667eea; font-size: 1em; padding: 4px 8px; border-radius: 4px; transition: background 0.2s;';
        viewQueryBtn.innerHTML = '🔍 Show Query';
        viewQueryBtn.title = 'View SQL Query';
        viewQueryBtn.onclick = (e) => {
            e.stopPropagation();
            showChartQuery(chartConfig);
        };
        viewQueryBtn.onmouseover = function() { this.style.background = '#f0f0f0'; };
        viewQueryBtn.onmouseout = function() { this.style.background = 'none'; };

        const copyQueryBtn = document.createElement('button');
        copyQueryBtn.style.cssText = 'background: none; border: none; cursor: pointer; color: #667eea; font-size: 1.2em; padding: 4px 8px; border-radius: 4px; transition: background 0.2s;';
        copyQueryBtn.innerHTML = '📋';
        copyQueryBtn.title = 'Copy SQL Query';
        copyQueryBtn.onclick = async (e) => {
            e.stopPropagation();
            const query = generateChartQuery(chartConfig);
            try {
                await navigator.clipboard.writeText(query);
                showToast('SQL query copied to clipboard!', 'success');
            } catch (err) {
                console.error('Failed to copy:', err);
                showToast('Failed to copy query', 'error');
            }
        };
        copyQueryBtn.onmouseover = function() { this.style.background = '#f0f0f0'; };
        copyQueryBtn.onmouseout = function() { this.style.background = 'none'; };

        rightSide.appendChild(viewQueryBtn);
        rightSide.appendChild(copyQueryBtn);

        titleContainer.appendChild(leftSide);
        titleContainer.appendChild(rightSide);
        chartWrapper.appendChild(titleContainer);

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
            tableContainer.style.cssText = `flex: 1; overflow: auto;`;
            chartWrapper.appendChild(tableContainer);
            container.appendChild(chartWrapper);

            await renderTableChart(tableContainer, chartConfig, filters, filterExpressions);
            return;
        }

        // Canvas container to properly constrain the chart
        const canvasContainer = document.createElement('div');
        canvasContainer.style.cssText = 'position: relative; flex: 1; min-height: 200px; display: flex; align-items: center; justify-content: center;';

        const canvas = document.createElement('canvas');
        canvas.id = 'chart-' + chartConfig.id;
        canvasContainer.appendChild(canvas);
        chartWrapper.appendChild(canvasContainer);

        // Add to container first
        container.appendChild(chartWrapper);

        // Handle metric type
        if (chartConfig.type === 'metric') {
            await renderMetricChart(canvas, chartConfig, filters, filterExpressions);
            return;
        }

        // Build query payload
        const queryPayload = {
            table: chartConfig.model,
            type: chartConfig.type,
            x_axis: chartConfig.x_axis,
            filters: filters,
            filter_expressions: filterExpressions
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
async function renderMetricChart(canvas, chartConfig, filters = {}, filterExpressions = {}) {
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
                type: 'metric',  // Important: tell backend this is a metric chart
                metric: metricField,
                aggregation: chartConfig.aggregation || 'sum',
                filters: filters,  // Pass filters to backend
                filter_expressions: filterExpressions  // Pass filter expressions to backend
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
async function renderTableChart(container, chartConfig, filters = {}, filterExpressions = {}) {
    try {
        // Fetch data from API
        const queryResponse = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'table',
                table: chartConfig.model,
                columns: chartConfig.columns || [],
                filters: filters,
                filter_expressions: filterExpressions
            })
        });

        if (!queryResponse.ok) {
            const errorText = await queryResponse.text();
            console.error('Table API error:', errorText);
            throw new Error('Failed to fetch table data');
        }

        const chartData = await queryResponse.json();

        // Check if we have data
        const columns = chartData.columns || [];
        const rows = chartData.data || [];
        const hasData = rows.length > 0;

        if (!hasData) {
            container.innerHTML = '<div style="padding: 30px; text-align: center; color: #888;">No data available</div>';
            return;
        }

        // Create HTML table
        let tableHTML = '<table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">';
        tableHTML += '<thead><tr>';

        // Add header for each column
        columns.forEach(col => {
            tableHTML += `<th style="padding: 0.75rem; text-align: left; border-bottom: 2px solid var(--color-border); background: var(--color-bg-secondary); font-weight: 600; color: #000;">${col}</th>`;
        });

        tableHTML += '</tr></thead><tbody>';

        // Add row data
        rows.forEach((row, idx) => {
            const rowStyle = idx % 2 === 0 ? 'background: #f9fafb;' : '';
            tableHTML += `<tr style="${rowStyle}">`;
            columns.forEach(col => {
                const value = row[col] !== null && row[col] !== undefined ? row[col] : '';
                tableHTML += `<td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border); color: #000;">${value}</td>`;
            });
            tableHTML += '</tr>';
        });

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
        const response = await fetch('/api/charts');
        const data = await response.json();

        // Store all charts for search
        allChartsData = data.charts || [];

        const chartsList = document.getElementById('all-charts-list');

        if (allChartsData.length === 0) {
            chartsList.innerHTML = '<p style="color: #888;">No charts available</p>';
            return;
        }

        // Use all charts from the API
        let allCharts = allChartsData.map(chart => {
            // Determine dashboard display name
            let dashboardName = 'Standalone';
            let dashboardId = null;

            if (chart.dashboards && chart.dashboards.length > 0) {
                if (chart.dashboards.length === 1) {
                    // Single dashboard assignment
                    dashboardName = chart.dashboards[0].name;
                    dashboardId = chart.dashboards[0].id;
                } else {
                    // Multiple dashboard assignments
                    dashboardName = chart.dashboards.map(d => d.name).join(', ');
                    dashboardId = 'multiple';
                }
            }

            return {
                ...chart,
                dashboardName: dashboardName,
                dashboardId: dashboardId
            };
        });

        // Apply search filter
        if (currentChartsSearchTerm) {
            allCharts = filterListItems(currentChartsSearchTerm, allCharts, ['title', 'type', 'model', 'dashboardName']);
        }

        if (allCharts.length === 0) {
            chartsList.innerHTML = `<p style="color: #888;">No charts match your search criteria.</p>`;
            return;
        }

        // Clear the list
        chartsList.innerHTML = '';

        // Display based on view mode
        if (chartsViewMode === 'table') {
            // Table view - compact rows
            chartsList.className = 'charts-table-view';

            const table = document.createElement('table');
            table.className = 'view-table';
            table.innerHTML = `
                <thead>
                    <tr>
                        <th>Chart Name</th>
                        <th>Type</th>
                        <th>Dashboard</th>
                        <th>Model</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody></tbody>
            `;

            const tbody = table.querySelector('tbody');

            allCharts.forEach(chart => {
                const typeIcons = {
                    line: '📈',
                    bar: '📊',
                    pie: '🥧',
                    doughnut: '🍩',
                    metric: '🔢',
                    table: '📋'
                };

                const row = document.createElement('tr');

                // Show delete button only if user has permission
                const deleteButtonHtml = window.userPermissions.canDeleteCharts
                    ? '<button class="icon-btn-small delete-btn" title="Delete chart" style="color: #ef4444; margin-right: 4px; font-size: 0.85rem;">🗑️</button>'
                    : '';

                row.innerHTML = `
                    <td><strong>${chart.title}</strong></td>
                    <td>${typeIcons[chart.type] || '📊'} ${chart.type}</td>
                    <td>${chart.dashboardName}</td>
                    <td><code>${chart.model}</code></td>
                    <td>
                        ${deleteButtonHtml}
                        <button class="icon-btn-small edit-btn" title="Edit chart">✏️</button>
                    </td>
                `;

                const deleteBtn = row.querySelector('.delete-btn');
                if (deleteBtn) {
                    deleteBtn.onclick = (e) => {
                        e.stopPropagation();
                        deleteChart(chart);
                    };
                }

                const editBtn = row.querySelector('.edit-btn');
                editBtn.onclick = (e) => {
                    e.stopPropagation();
                    editChart(chart);
                };

                row.style.cursor = 'pointer';
                row.onclick = () => editChart(chart);

                tbody.appendChild(row);
            });

            chartsList.appendChild(table);
        } else {
            // Grid view - cards with previews (original)
            chartsList.className = 'charts-grid';

            allCharts.forEach(async (chart, index) => {
                const card = document.createElement('div');
                card.className = 'chart-item-card';

                // Chart type icon
                const typeIcons = {
                    line: '📈',
                    bar: '📊',
                    pie: '🥧',
                    doughnut: '🍩',
                    metric: '🔢',
                    table: '📋'
                };

                // Create preview canvas with unique ID (include index to avoid duplicates)
                const canvasId = `chart-preview-${chart.dashboardId}-${chart.id}-${index}`;

                // Show delete button only if user has permission
                const deleteButtonHtml = window.userPermissions.canDeleteCharts
                    ? '<button class="chart-item-delete-btn" title="Delete chart">🗑️</button>'
                    : '';

                // Adjust button positions based on whether delete button is shown
                // When delete is shown: Delete (right), Export (right:50px), Edit (right:90px), Query (right:130px)
                // When delete is hidden: Export (right), Edit (right:40px), Query (right:80px)
                const exportBtnStyle = window.userPermissions.canDeleteCharts ? 'right: 50px;' : '';
                const editBtnStyle = window.userPermissions.canDeleteCharts ? 'right: 90px;' : 'right: 40px;';
                const queryBtnStyle = window.userPermissions.canDeleteCharts ? 'right: 130px;' : 'right: 80px;';

                card.innerHTML = `
                    <div class="chart-item-preview" style="height: 120px; margin-bottom: 12px; background: var(--color-bg-secondary); border-radius: 8px; padding: 8px; display: flex; align-items: center; justify-content: center; overflow: hidden;">
                        <canvas id="${canvasId}" style="max-height: 100px; max-width: 100%;"></canvas>
                    </div>
                    <div class="chart-item-title">${chart.title}</div>
                    <div class="chart-item-dashboard">${chart.dashboardName}</div>
                    <div class="chart-item-badges">
                        <span class="chart-badge chart-badge-type">${chart.type}</span>
                        <span class="chart-badge chart-badge-model">${chart.model}</span>
                    </div>
                    ${deleteButtonHtml}
                    <button class="chart-item-export-btn" title="Export chart" style="${exportBtnStyle}">📥</button>
                    <button class="chart-item-edit-btn" title="Edit chart" style="${editBtnStyle}">✏️</button>
                    <button class="chart-item-query-btn" title="View query" style="${queryBtnStyle}">📋</button>
                `;

                // Delete button click handler (only if button exists)
                const deleteBtn = card.querySelector('.chart-item-delete-btn');
                if (deleteBtn) {
                    deleteBtn.onclick = (e) => {
                        e.stopPropagation();
                        deleteChart(chart);
                    };
                }

                // Export button click handler
                const exportBtn = card.querySelector('.chart-item-export-btn');
                exportBtn.onclick = (e) => {
                    e.stopPropagation();
                    showChartExportMenu(e, chart);
                };

                // Edit button click handler
                const editBtn = card.querySelector('.chart-item-edit-btn');
                editBtn.onclick = (e) => {
                    e.stopPropagation();
                    editChart(chart);
                };

                // Query button click handler
                const queryBtn = card.querySelector('.chart-item-query-btn');
                queryBtn.onclick = async (e) => {
                    e.stopPropagation();
                    console.log('📋 QUERY BUTTON CLICKED! Chart:', chart.title);
                    console.log('Chart config:', chart);

                    // Generate SQL directly here
                    let sql = '';
                    if (chart.type === 'table') {
                        if (chart.columns && Array.isArray(chart.columns) && chart.columns.length > 0) {
                            const columnsList = chart.columns.map(col => col.name || col).join(', ');
                            sql = `SELECT ${columnsList}\nFROM public.${chart.model}\nLIMIT 100`;
                        } else {
                            sql = `SELECT *\nFROM public.${chart.model}\nLIMIT 100`;
                        }
                    } else {
                        sql = `SELECT *\nFROM public.${chart.model}\nLIMIT 100`;
                    }

                    // Copy to clipboard
                    try {
                        await navigator.clipboard.writeText(sql);
                        alert('✅ SQL Query copied to clipboard!\n\n' + sql);
                    } catch (err) {
                        alert('SQL Query:\n\n' + sql + '\n\n(Click OK, then manually copy from console)');
                        console.log('SQL Query for copying:', sql);
                    }
                };

                // Click on card to edit chart (opens in chart builder)
                card.onclick = () => {
                    editChart(chart);
                };

                chartsList.appendChild(card);

                // Render preview chart
                renderChartPreview(canvasId, chart);
            });
        }

        // Show total count
        const countDiv = document.createElement('div');
        countDiv.className = 'charts-count';
        countDiv.textContent = `📊 Total: ${allCharts.length} charts in the library`;
        chartsList.appendChild(countDiv);

    } catch (error) {
        console.error('Error loading charts:', error);
        document.getElementById('all-charts-list').innerHTML = '<p style="color: #ef4444;">Failed to load charts</p>';
    }
}

// Store chart instances to prevent canvas reuse errors
const chartInstances = {};

// Render chart preview thumbnail
async function renderChartPreview(canvasId, chartConfig) {
    try {
        console.log(`[${chartConfig.id}] Starting preview for "${chartConfig.title}" (${chartConfig.type})`);

        // Handle metric type differently - no API call needed for correct display
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`[${chartConfig.id}] Canvas not found:`, canvasId);
            return;
        }

        if (chartConfig.type === 'metric') {
            // For metric type, query with the metric field
            const metricField = chartConfig.metric || chartConfig.calculation || chartConfig.y_axis;

            if (!metricField) {
                console.warn(`[${chartConfig.id}] No metric field found, skipping`);
                const parent = canvas.parentElement;
                if (parent) {
                    parent.innerHTML = '<div style="color: #888; font-size: 0.8rem;">Config missing metric field</div>';
                }
                return;
            }

            const payload = {
                table: chartConfig.model,
                type: 'metric',
                metric: metricField,
                aggregation: chartConfig.aggregation || 'sum'
            };

            console.log('Metric preview request:', payload);

            const response = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`[${chartConfig.id}] ❌ Metric API error:`, response.status, errorText);
                throw new Error(`API error: ${response.status}`);
            }

            const data = await response.json();
            console.log(`[${chartConfig.id}] ✅ Metric data loaded:`, data);

            // Don't render metric in canvas, show text instead
            const parent = canvas.parentElement;
            if (!parent) {
                console.warn(`[${chartConfig.id}] Canvas parent not found for`, canvasId);
                return;
            }

            // Get metric value - backend returns 'value' field for metrics
            const metricValue = data.value ?? (data.values && data.values.length > 0 ? data.values.reduce((a, b) => a + b, 0) : 0);

            parent.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;">
                    <div style="font-size: 2rem; font-weight: 700; color: #667eea;">
                        ${typeof metricValue === 'number' ? metricValue.toLocaleString() : metricValue}
                    </div>
                    <div style="font-size: 0.75rem; color: #888; margin-top: 4px;">
                        ${(chartConfig.aggregation || 'sum').toUpperCase()}
                    </div>
                </div>
            `;
            return;
        }

        // For regular charts, query data
        const payload = {
            table: chartConfig.model,
            type: chartConfig.type || 'bar',  // Include chart type
            x_axis: chartConfig.x_axis
        };

        // Handle table charts - need columns instead of x/y axes
        if (chartConfig.type === 'table') {
            payload.columns = chartConfig.columns || [];
            delete payload.x_axis;  // Remove x_axis for table charts
        }
        // Handle multi-metric charts (has metrics array)
        else if (chartConfig.metrics && Array.isArray(chartConfig.metrics)) {
            payload.metrics = chartConfig.metrics;
            console.log('Multi-metric chart preview request:', payload);
        } else {
            // Regular chart with single y_axis
            payload.y_axis = chartConfig.y_axis;
            payload.aggregation = chartConfig.aggregation || 'sum';
        }

        // Only add filters if they exist and are non-empty
        if (chartConfig.filters && Object.keys(chartConfig.filters).length > 0) {
            payload.filters = chartConfig.filters;
        }

        console.log('Chart preview request:', payload);

        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`[${chartConfig.id}] ❌ Chart API error:`, response.status, errorText);
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        console.log(`[${chartConfig.id}] ✅ Chart data loaded:`, data);

        // Handle table charts differently - render as HTML table preview
        if (chartConfig.type === 'table') {
            const parent = canvas.parentElement;
            if (!parent) {
                console.warn(`[${chartConfig.id}] Parent element not found for table`);
                return;
            }

            // Render a mini table preview with first 3 rows
            if (!data.data || data.data.length === 0) {
                parent.innerHTML = '<div style="color: #888; font-size: 0.7rem; text-align: center; padding: 20px;">No data</div>';
                return;
            }

            const columns = data.columns || [];
            const rows = data.data.slice(0, 3); // First 3 rows only

            let tableHTML = '<table style="width: 100%; font-size: 0.65rem; border-collapse: collapse;">';

            // Header
            tableHTML += '<thead><tr>';
            columns.forEach(col => {
                tableHTML += `<th style="padding: 2px 4px; border-bottom: 1px solid #ddd; font-weight: 600; color: #333; text-align: left;">${col}</th>`;
            });
            tableHTML += '</tr></thead>';

            // Rows
            tableHTML += '<tbody>';
            rows.forEach(row => {
                tableHTML += '<tr>';
                columns.forEach(col => {
                    const value = row[col] !== null && row[col] !== undefined ? row[col] : '-';
                    tableHTML += `<td style="padding: 2px 4px; border-bottom: 1px solid #eee; color: #555;">${value}</td>`;
                });
                tableHTML += '</tr>';
            });
            tableHTML += '</tbody></table>';

            // Add row count indicator
            if (data.data.length > 3) {
                tableHTML += `<div style="text-align: center; font-size: 0.6rem; color: #888; margin-top: 4px;">+${data.data.length - 3} more rows</div>`;
            }

            parent.innerHTML = tableHTML;
            return;
        }

        // Destroy existing chart instance if it exists
        if (chartInstances[canvasId]) {
            chartInstances[canvasId].destroy();
            delete chartInstances[canvasId];
        }

        const ctx = canvas.getContext('2d');

        // Handle multi-metric charts (datasets array)
        let datasets;
        if (data.datasets && Array.isArray(data.datasets)) {
            // Multi-metric chart: use the datasets from API
            datasets = data.datasets.map((dataset, i) => ({
                label: dataset.label,
                data: dataset.data,
                backgroundColor: `hsla(${i * 60}, 70%, 60%, 0.8)`,
                borderColor: `hsl(${i * 60}, 70%, 60%)`,
                borderWidth: 1.5,
                tension: 0.4
            }));
        } else {
            // Single metric chart: use values array
            datasets = [{
                label: chartConfig.title,
                data: data.values || [],
                backgroundColor: chartConfig.type === 'pie' || chartConfig.type === 'doughnut'
                    ? ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
                    : 'rgba(102, 126, 234, 0.8)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 1.5,
                tension: 0.4
            }];
        }

        // Handle stacked bar chart type conversion
        let actualChartType = chartConfig.type;
        let chartOptions = {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            },
            scales: chartConfig.type === 'pie' || chartConfig.type === 'doughnut' ? {} : {
                x: { display: false },
                y: { display: false, beginAtZero: true }
            }
        };

        // Convert bar-stacked to bar with stacking configuration
        if (chartConfig.type === 'bar-stacked') {
            actualChartType = 'bar';
            chartOptions.scales = {
                x: { display: false, stacked: true },
                y: { display: false, stacked: true, beginAtZero: true }
            };
        }

        // Create Chart.js preview and store instance
        chartInstances[canvasId] = new Chart(ctx, {
            type: actualChartType,
            data: {
                labels: data.labels || [],
                datasets: datasets
            },
            options: chartOptions
        });

    } catch (error) {
        console.error('Error rendering chart preview:', error);
        const canvas = document.getElementById(canvasId);
        if (canvas) {
            const parent = canvas.parentElement;
            parent.innerHTML = '<div style="color: #888; font-size: 0.8rem;">Preview unavailable</div>';
        }
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

// Load available connections into the chart builder dropdown
async function loadChartConnections() {
    // NOTE: DO NOT clear currentEditingChartId here! It needs to persist when editing charts.
    // Only clear it when explicitly starting a new chart via the "New Chart" button.

    // Reset the chart builder form
    const chartTitle = document.getElementById('chartTitle');
    if (chartTitle) chartTitle.value = '';

    try {
        const response = await fetch('/api/connections/list');
        const data = await response.json();

        const connectionSelect = document.getElementById('chartConnection');
        if (!connectionSelect) return;

        // Clear existing options except the first placeholder
        connectionSelect.innerHTML = '<option value="">Select connection...</option>';

        if (data.connections && data.connections.length > 0) {
            data.connections.forEach(conn => {
                const option = document.createElement('option');
                option.value = conn.id;
                option.textContent = conn.name;
                if (conn.default) {
                    option.selected = true;
                }
                connectionSelect.appendChild(option);
            });

            // Auto-load schemas for default connection
            if (connectionSelect.value) {
                loadChartSchemas();
            }
        }
    } catch (error) {
        console.error('Error loading connections for chart builder:', error);
    }
}

// Load available dashboards into the chart builder dropdown
async function loadChartDashboards() {
    console.log('[DEBUG] loadChartDashboards() called');
    try {
        console.log('[DEBUG] Fetching /api/dashboards...');
        const response = await fetch('/api/dashboards');
        console.log('[DEBUG] Response status:', response.status);
        const data = await response.json();
        console.log('[DEBUG] Dashboards data:', JSON.stringify(data, null, 2));

        const dashboardSelect = document.getElementById('chartDashboard');
        console.log('[DEBUG] Dashboard select element:', dashboardSelect);
        if (!dashboardSelect) {
            console.error('[ERROR] Dashboard select element not found!');
            return;
        }

        // Keep the placeholder and "Create New" option
        dashboardSelect.innerHTML = '<option value="">Select dashboard...</option><option value="__new__">➕ Create New Dashboard</option>';
        console.log('[DEBUG] Reset dropdown with default options');

        if (data.dashboards && data.dashboards.length > 0) {
            console.log(`[DEBUG] Found ${data.dashboards.length} dashboards, adding them now...`);
            data.dashboards.forEach((dashboard, index) => {
                const option = document.createElement('option');
                option.value = dashboard.id;
                option.textContent = dashboard.name;
                dashboardSelect.appendChild(option);
                console.log(`[DEBUG] Added dashboard ${index + 1}: ${dashboard.name} (${dashboard.id})`);
            });
            console.log('[DEBUG] Final dropdown HTML:', dashboardSelect.innerHTML);
        } else {
            console.log('[DEBUG] No dashboards found in response');
        }
    } catch (error) {
        console.error('[ERROR] Error loading dashboards for chart builder:', error);
        console.error('[ERROR] Error stack:', error.stack);
    }
}

// Handle dashboard selection change
function handleDashboardSelection() {
    const dashboardSelect = document.getElementById('chartDashboard');
    const newDashboardFields = document.getElementById('newDashboardFields');

    if (dashboardSelect.value === '__new__') {
        newDashboardFields.style.display = 'block';
    } else {
        newDashboardFields.style.display = 'none';
    }
}

// Load available schemas for selected connection
async function loadChartSchemas() {
    const connectionId = document.getElementById('chartConnection').value;
    const schemaSelect = document.getElementById('chartSchema');
    const tableSelect = document.getElementById('chartTable');

    if (!schemaSelect || !connectionId) return;

    // Clear schema and table dropdowns
    schemaSelect.innerHTML = '<option value="">Select schema...</option>';
    tableSelect.innerHTML = '<option value="">Select table...</option>';

    try {
        const response = await fetch(`/api/schemas/list?connection_id=${connectionId}`);
        const data = await response.json();

        if (data.schemas && data.schemas.length > 0) {
            data.schemas.forEach(schema => {
                const option = document.createElement('option');
                option.value = schema;
                option.textContent = schema;
                schemaSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading schemas for chart builder:', error);
    }
}

// Load available tables for selected schema
async function loadChartTables() {
    const connectionId = document.getElementById('chartConnection').value;
    const schema = document.getElementById('chartSchema').value;
    const tableSelect = document.getElementById('chartTable');

    if (!tableSelect || !connectionId || !schema) return;

    // Clear table dropdown
    tableSelect.innerHTML = '<option value="">Select table...</option>';

    try {
        const response = await fetch(`/api/tables/list?schema=${schema}&connection_id=${connectionId}`);
        const data = await response.json();

        if (data.tables && data.tables.length > 0) {
            data.tables.forEach(table => {
                const option = document.createElement('option');
                // table is an object with {name, type, size}, not a string
                option.value = table.name;
                option.textContent = table.name;
                tableSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading tables for chart builder:', error);
    }
}

async function loadTableColumns() {
    const table = document.getElementById('chartTable').value;
    const chartType = document.getElementById('chartType').value;
    if (!table) {
        // Hide fields panel if no table selected
        const fieldsPanel = document.getElementById('fields-panel');
        if (fieldsPanel) fieldsPanel.style.display = 'none';
        return;
    }

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
        const categoryAxis = document.getElementById('chartCategory');

        // Clear existing options
        xAxis.innerHTML = '<option value="">Select column...</option>';
        yAxis.innerHTML = '<option value="">Select column...</option>';
        if (categoryAxis) {
            categoryAxis.innerHTML = '<option value="">Select column...</option>';
        }

        // Add columns to dropdowns
        data.columns.forEach(col => {
            // Build column label with index indicator
            const indexIndicator = col.index_type ? ` [${col.index_type === 'primary' ? '🔑' : col.index_type === 'unique' ? '⭐' : '📑'}]` : '';
            const columnLabel = `${col.name} (${col.type})${indexIndicator}`;

            const optionX = document.createElement('option');
            optionX.value = col.name;
            optionX.textContent = columnLabel;
            xAxis.appendChild(optionX);

            const optionY = document.createElement('option');
            optionY.value = col.name;
            optionY.textContent = columnLabel;
            yAxis.appendChild(optionY);

            // Also populate category dropdown if it exists (for stacked charts)
            if (categoryAxis) {
                const optionCategory = document.createElement('option');
                optionCategory.value = col.name;
                optionCategory.textContent = columnLabel;
                categoryAxis.appendChild(optionCategory);
            }
        });

        // Populate draggable fields panel
        const fieldsPanel = document.getElementById('fields-panel');
        const fieldsList = document.getElementById('available-fields-list');

        if (fieldsPanel && fieldsList) {
            fieldsPanel.style.display = 'block';
            fieldsList.innerHTML = '';

            data.columns.forEach(col => {
                const fieldItem = document.createElement('div');
                fieldItem.draggable = true;
                fieldItem.dataset.fieldName = col.name;
                fieldItem.dataset.fieldType = col.type;

                // Add index indicator
                const indexIndicator = col.index_type ? ` ${col.index_type === 'primary' ? '🔑' : col.index_type === 'unique' ? '⭐' : '📑'}` : '';
                fieldItem.textContent = `${col.name}${indexIndicator}`;

                fieldItem.style.cssText = `
                    padding: 0.5rem 0.75rem;
                    background: var(--color-bg-primary);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-md);
                    cursor: move;
                    font-size: 0.85rem;
                    transition: all 0.2s;
                `;

                // Update title to show index type
                const indexText = col.index_type ? ` [${col.index_type}]` : '';
                fieldItem.setAttribute('title', `${col.name} (${col.type})${indexText}`);

                // Drag events
                fieldItem.addEventListener('dragstart', (e) => {
                    e.dataTransfer.setData('text/plain', col.name);
                    e.dataTransfer.effectAllowed = 'copy';
                    fieldItem.style.opacity = '0.5';
                });

                fieldItem.addEventListener('dragend', (e) => {
                    fieldItem.style.opacity = '1';
                });

                // Hover effect
                fieldItem.addEventListener('mouseenter', () => {
                    fieldItem.style.background = 'var(--color-primary-light)';
                    fieldItem.style.borderColor = 'var(--color-primary)';
                });

                fieldItem.addEventListener('mouseleave', () => {
                    fieldItem.style.background = 'var(--color-bg-primary)';
                    fieldItem.style.borderColor = 'var(--color-border)';
                });

                fieldsList.appendChild(fieldItem);
            });
        }
    } catch (error) {
        console.error('Error loading columns:', error);
    }
}

// Drag and drop handlers for fields
function handleDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
    event.target.style.borderColor = 'var(--color-primary)';
    event.target.style.background = 'var(--color-primary-light)';
}

function handleDragLeave(event) {
    event.target.style.borderColor = '';
    event.target.style.background = '';
}

function handleFieldDrop(event, axis) {
    event.preventDefault();
    const fieldName = event.dataTransfer.getData('text/plain');

    // Reset styling
    event.target.style.borderColor = '';
    event.target.style.background = '';

    if (fieldName) {
        // Set the value in the appropriate dropdown
        if (axis === 'x') {
            document.getElementById('chartXAxis').value = fieldName;
        } else if (axis === 'y') {
            document.getElementById('chartYAxis').value = fieldName;
        }

        // Show a brief visual feedback
        const target = event.target;
        const originalBg = target.style.background;
        target.style.background = 'var(--color-success-light)';
        setTimeout(() => {
            target.style.background = originalBg;
        }, 300);
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

        // Reset all form fields to create a new chart
        document.getElementById('chartTitle').value = '';
        document.getElementById('chartType').value = 'bar';
        document.getElementById('chartTable').value = '';
        document.getElementById('chartXAxis').value = '';
        document.getElementById('chartYAxis').value = '';
        document.getElementById('chartAggregation').value = 'sum';

        // Clear the preview area
        const previewContainer = document.getElementById('chartPreview');
        if (previewContainer) {
            previewContainer.innerHTML = '<p style="color: var(--color-text-muted); text-align: center; padding: 2rem;">Select options and click "Create Chart" to preview</p>';
        }

        // Reset table columns
        tableColumns = [];
        const tableColumnsContainer = document.getElementById('tableColumnsContainer');
        if (tableColumnsContainer) {
            tableColumnsContainer.innerHTML = '<p style="color: var(--color-text-muted); font-size: 0.875rem; padding: 1rem;">Click "+ Add Column" to add columns to your table</p>';
        }

        // Show/hide appropriate fields based on chart type
        handleChartTypeChange();

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
    const stackedCategoryField = document.getElementById('stackedCategoryField');

    if (chartType === 'table') {
        regularFields.style.display = 'none';
        tableFields.style.display = 'block';
        stackedCategoryField.style.display = 'none';
        // Load table columns if table is selected (but skip if we're editing - restoration will handle it)
        const table = document.getElementById('chartTable').value;
        if (table && !currentEditingChartId) {
            console.log('Loading table columns for new table chart');
            loadTableColumnsForBuilder();
        } else if (currentEditingChartId) {
            console.log('Skipping loadTableColumnsForBuilder - editing existing chart, will restore columns separately');
        }
    } else {
        regularFields.style.display = 'block';
        tableFields.style.display = 'none';

        // Show category field only for stacked bar charts
        if (chartType === 'bar-stacked') {
            stackedCategoryField.style.display = 'block';
        } else {
            stackedCategoryField.style.display = 'none';
        }
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
            console.log('DEBUG: Columns API response:', data);
            console.log('DEBUG: data.columns:', data.columns);

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
            console.error('Error loading columns:', error);
            document.getElementById('chartError').style.display = 'block';
            document.getElementById('chartError').textContent = 'Error loading columns';
        });
}

// Render table columns configuration UI
function renderTableColumns(availableColumns) {
    const container = document.getElementById('tableColumnsContainer');

    // Ensure availableColumns is an array
    if (!availableColumns || !Array.isArray(availableColumns)) {
        console.warn('availableColumns is not an array:', availableColumns);
        availableColumns = [];
    }

    console.log('renderTableColumns called with', tableColumns.length, 'table columns and', availableColumns.length, 'available columns');

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
                        ${availableColumns.map(c => `<option value="${c.name}" ${col.field === c.name ? 'selected' : ''}>${c.name} (${c.type})</option>`).join('')}
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

// ============================================
// FILTER MANAGEMENT
// ============================================

let chartFilters = [];

function addFilter() {
    const table = document.getElementById('chartTable').value;

    if (!table) {
        showToast('Please select a data source first', 'error');
        return;
    }

    // Fetch available columns for the selected table
    fetch(`/api/tables/${table}/columns`)
        .then(response => response.json())
        .then(data => {
            const filterId = `filter-${Date.now()}`;
            const filter = {
                id: filterId,
                field: '',
                operator: '=',
                value: '',
                columns: data.columns || []
            };

            chartFilters.push(filter);
            renderFilters();
        })
        .catch(error => {
            console.error('Error loading columns:', error);
            showToast('Failed to load columns', 'error');
        });
}

function removeFilter(filterId) {
    chartFilters = chartFilters.filter(f => f.id !== filterId);
    renderFilters();
}

function updateFilter(filterId, field, operator, value) {
    const filter = chartFilters.find(f => f.id === filterId);
    if (filter) {
        if (field !== undefined) filter.field = field;
        if (operator !== undefined) filter.operator = operator;
        if (value !== undefined) filter.value = value;
    }
}

function renderFilters() {
    const container = document.getElementById('filtersContainer');

    if (chartFilters.length === 0) {
        container.innerHTML = '<p style="color: var(--color-text-muted); font-size: 0.8rem; margin: 0;">No filters added</p>';
        return;
    }

    container.innerHTML = chartFilters.map(filter => `
        <div style="margin-bottom: 0.75rem; padding: 0.75rem; background: var(--color-bg-primary); border: 1px solid var(--color-border); border-radius: var(--radius-md);">
            <div style="display: grid; grid-template-columns: 1fr 80px 1fr auto; gap: 0.5rem; align-items: center;">
                <select class="input" style="font-size: 0.8rem; padding: 0.4rem;"
                        onchange="updateFilter('${filter.id}', this.value, undefined, undefined); renderFilters();">
                    <option value="">Field...</option>
                    ${filter.columns.map(col => `
                        <option value="${col}" ${filter.field === col ? 'selected' : ''}>${col}</option>
                    `).join('')}
                </select>

                <select class="input" style="font-size: 0.8rem; padding: 0.4rem;"
                        onchange="updateFilter('${filter.id}', undefined, this.value, undefined);">
                    <option value="=" ${filter.operator === '=' ? 'selected' : ''}>=</option>
                    <option value="!=" ${filter.operator === '!=' ? 'selected' : ''}>!=</option>
                    <option value=">" ${filter.operator === '>' ? 'selected' : ''}>&gt;</option>
                    <option value="<" ${filter.operator === '<' ? 'selected' : ''}>&lt;</option>
                    <option value=">=" ${filter.operator === '>=' ? 'selected' : ''}>&gt;=</option>
                    <option value="<=" ${filter.operator === '<=' ? 'selected' : ''}>&lt;=</option>
                    <option value="LIKE" ${filter.operator === 'LIKE' ? 'selected' : ''}>LIKE</option>
                </select>

                <input type="text" class="input" placeholder="Value..."
                       style="font-size: 0.8rem; padding: 0.4rem;"
                       value="${filter.value}"
                       onchange="updateFilter('${filter.id}', undefined, undefined, this.value);">

                <button onclick="removeFilter('${filter.id}')"
                        style="background: none; border: none; color: var(--color-error); cursor: pointer; padding: 0.25rem; font-size: 1.2rem;"
                        title="Remove filter">
                    ×
                </button>
            </div>
        </div>
    `).join('');
}

function getActiveFilters() {
    // Return filters that have all fields filled
    return chartFilters
        .filter(f => f.field && f.operator && f.value)
        .map(f => ({
            field: f.field,
            operator: f.operator,
            value: f.value
        }));
}

// Global variable to track the chart being edited
let currentEditingChartId = null;

// SQL Query Lab Functions
async function loadConnections() {
    try {
        const response = await fetch('/api/connections/list');
        const data = await response.json();
        const connections = data.connections || [];

        const selector = document.getElementById('connection-selector');
        selector.innerHTML = '';

        if (connections.length === 0) {
            selector.innerHTML = '<option value="">No connections found</option>';
            return;
        }

        connections.forEach(conn => {
            const option = document.createElement('option');
            option.value = conn.id;
            option.textContent = conn.name;
            // Select the default connection
            if (conn.default) {
                option.selected = true;
            }
            selector.appendChild(option);
        });

        // Load schemas for the selected connection
        await loadSchemas();
    } catch (error) {
        console.error('Error loading connections:', error);
        const selector = document.getElementById('connection-selector');
        selector.innerHTML = '<option value="">Error loading connections</option>';
    }
}

async function onConnectionChange() {
    // When connection changes, reload schemas
    await loadSchemas();
}

async function loadSchemas() {
    try {
        const connectionId = document.getElementById('connection-selector').value;
        const url = connectionId ? `/api/schemas/list?connection_id=${encodeURIComponent(connectionId)}` : '/api/schemas/list';
        const response = await fetch(url);
        const data = await response.json();
        const schemas = data.schemas || [];

        const selector = document.getElementById('schema-selector');
        selector.innerHTML = '';

        if (schemas.length === 0) {
            selector.innerHTML = '<option value="">No schemas found</option>';
            return;
        }

        schemas.forEach((schema, index) => {
            const option = document.createElement('option');
            option.value = schema;
            option.textContent = schema;
            // Select first schema by default
            if (index === 0) {
                option.selected = true;
            }
            selector.appendChild(option);
        });

        // Load tables for the first schema
        if (schemas.length > 0) {
            await loadDatabaseSchema(schemas[0]);
        }
    } catch (error) {
        console.error('Error loading schemas:', error);
    }
}

async function onSchemaChange() {
    const schema = document.getElementById('schema-selector').value;
    await loadDatabaseSchema(schema);
}

async function loadDatabaseSchema(schema = 'public') {
    try {
        const connectionId = document.getElementById('connection-selector').value;
        const url = connectionId
            ? `/api/tables/list?schema=${encodeURIComponent(schema)}&connection_id=${encodeURIComponent(connectionId)}`
            : `/api/tables/list?schema=${encodeURIComponent(schema)}`;
        const response = await fetch(url);
        const data = await response.json();
        const tables = data.tables || data; // Handle both {tables: [...]} and [...]

        // Store tables data for search - convert to objects if they're strings
        allTablesData = tables.map(t => typeof t === 'string' ? { name: t, type: 'table' } : t);

        const browser = document.getElementById('schema-browser');
        if (!allTablesData || allTablesData.length === 0) {
            browser.innerHTML = '<p style="color: #888; font-size: 0.85rem;">No tables found</p>';
            allTablesData = [];
            return;
        }

        // Use the filter function to display tables (handles search)
        filterTablesDisplay();
    } catch (error) {
        console.error('Error loading schema:', error);
        document.getElementById('schema-browser').innerHTML = '<p style="color: #f44; font-size: 0.85rem;">Error loading tables</p>';
        allTablesData = [];
    }
}


async function toggleTableDetails(tableName) {
    const detailsDiv = document.getElementById(`table-details-${tableName}`);
    const expandIcon = document.getElementById(`expand-icon-${tableName}`);

    if (detailsDiv.style.display === 'none') {
        // Expand and load columns
        detailsDiv.style.display = 'block';
        expandIcon.style.transform = 'rotate(90deg)';

        // Load columns if not already loaded
        if (!detailsDiv.dataset.loaded) {
            try {
                const connectionId = document.getElementById('connection-selector').value;
                const schema = document.getElementById('schema-selector').value;
                const url = connectionId && schema
                    ? `/api/tables/${encodeURIComponent(tableName)}/columns?schema=${encodeURIComponent(schema)}&connection_id=${encodeURIComponent(connectionId)}`
                    : `/api/tables/${encodeURIComponent(tableName)}/columns?schema=${encodeURIComponent(schema || 'public')}`;
                const response = await fetch(url);
                const data = await response.json();
                const columns = data.columns || [];

                if (columns.length === 0) {
                    detailsDiv.innerHTML = '<div style="font-size: 0.75rem; color: #888; padding: 4px 0;">No columns found</div>';
                } else {
                    let html = '<div style="margin-top: 8px;">';
                    columns.forEach(col => {
                        const typeColor = col.type.includes('int') ? '#10b981' :
                                        col.type.includes('char') || col.type.includes('text') ? '#667eea' :
                                        col.type.includes('date') || col.type.includes('time') ? '#f59e0b' :
                                        '#6c757d';
                        // Add index indicator
                        const indexIndicator = col.index_type ? ` ${col.index_type === 'primary' ? '🔑' : col.index_type === 'unique' ? '⭐' : '📑'}` : '';
                        html += `
                            <div style="padding: 4px 8px; margin-bottom: 4px; background: #fafafa; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-size: 0.75rem; color: #495057; font-family: 'Monaco', 'Menlo', monospace;">${col.name}${indexIndicator}</span>
                                <span style="font-size: 0.7rem; color: ${typeColor}; font-weight: 600; padding: 2px 6px; background: white; border-radius: 3px;">${col.type}</span>
                            </div>
                        `;
                    });
                    html += '</div>';
                    detailsDiv.innerHTML = html;
                }
                detailsDiv.dataset.loaded = 'true';
            } catch (error) {
                console.error('Error loading columns:', error);
                detailsDiv.innerHTML = '<div style="font-size: 0.75rem; color: #f44; padding: 4px 0;">Error loading columns</div>';
            }
        }
    } else {
        // Collapse
        detailsDiv.style.display = 'none';
        expandIcon.style.transform = 'rotate(0deg)';
    }
}

function showTableMenu(tableName, event) {
    // Remove any existing menu
    const existingMenu = document.getElementById('table-context-menu');
    if (existingMenu) existingMenu.remove();

    // Create menu
    const menu = document.createElement('div');
    menu.id = 'table-context-menu';
    menu.style.cssText = `
        position: fixed;
        background: white;
        border: 1px solid #ddd;
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        min-width: 150px;
        padding: 4px 0;
    `;

    menu.innerHTML = `
        <div onclick="previewTable('${tableName}'); document.getElementById('table-context-menu').remove();"
             style="padding: 8px 16px; cursor: pointer; font-size: 0.85rem; color: #333;"
             onmouseover="this.style.background='#f0f0f0'"
             onmouseout="this.style.background='white'">
            👁️ Preview (10 rows)
        </div>
        <div onclick="insertTableName('${tableName}'); document.getElementById('table-context-menu').remove();"
             style="padding: 8px 16px; cursor: pointer; font-size: 0.85rem; color: #333;"
             onmouseover="this.style.background='#f0f0f0'"
             onmouseout="this.style.background='white'">
            📝 Insert name
        </div>
    `;

    // Position menu near the button
    const rect = event.target.getBoundingClientRect();
    menu.style.left = `${rect.left - 100}px`;
    menu.style.top = `${rect.bottom + 5}px`;

    document.body.appendChild(menu);

    // Close menu when clicking outside
    setTimeout(() => {
        document.addEventListener('click', function closeMenu(e) {
            if (!menu.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        });
    }, 0);
}

function insertTableName(tableName) {
    const editor = document.getElementById('sql-editor');
    const cursorPos = editor.selectionStart;
    const textBefore = editor.value.substring(0, cursorPos);
    const textAfter = editor.value.substring(cursorPos);
    editor.value = textBefore + tableName + textAfter;
    editor.focus();
    editor.setSelectionRange(cursorPos + tableName.length, cursorPos + tableName.length);
}

async function previewTable(tableName) {
    // Get current schema to qualify the table name
    const schema = document.getElementById('schema-selector')?.value;

    // Set the SQL editor with preview query (schema-qualified if schema is selected)
    const qualifiedTableName = schema ? `${schema}.${tableName}` : tableName;
    const previewQuery = `SELECT * FROM ${qualifiedTableName} LIMIT 10;`;
    document.getElementById('sql-editor').value = previewQuery;

    // Automatically execute the query to show preview
    await executeQuery();
}

function clearQuery() {
    document.getElementById('sql-editor').value = '';
    document.getElementById('query-error').style.display = 'none';
}

async function saveAsView() {
    // Get the current SQL query
    const sql = document.getElementById('sql-editor')?.value.trim();
    if (!sql) {
        alert('No query to save as view');
        return;
    }

    // Prompt for view name
    const viewName = prompt('Enter a name for the view (will be created in the selected schema):');
    if (!viewName) {
        return;
    }

    // Validate view name (alphanumeric and underscores only)
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(viewName)) {
        alert('Invalid view name. Use only letters, numbers, and underscores, and start with a letter or underscore.');
        return;
    }

    // Get selected connection and schema
    const connectionId = document.getElementById('connection-selector')?.value;
    const schema = document.getElementById('schema-selector')?.value;

    if (!connectionId || !schema) {
        alert('Please select a connection and schema first');
        return;
    }

    // Confirm with user
    const fullViewName = `${schema}.${viewName}`;
    if (!confirm(`Create view "${fullViewName}" in database "${connectionId}"?\n\nThis will execute:\nCREATE OR REPLACE VIEW ${fullViewName} AS\n${sql}`)) {
        return;
    }

    try {
        const response = await fetch('/api/views/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                connection_id: connectionId,
                schema: schema,
                view_name: viewName,
                query: sql
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            alert(`✅ View "${fullViewName}" created successfully!`);
            // Refresh the tables list to show the new view
            await loadDatabaseSchema(schema);
        } else {
            alert(`❌ Failed to create view: ${result.detail || result.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error creating view:', error);
        alert(`❌ Network error: ${error.message}`);
    }
}

function exportToCSV() {
    if (!window.currentQueryData || !window.currentQueryData.rows || window.currentQueryData.rows.length === 0) {
        alert('No data to export');
        return;
    }

    const data = window.currentQueryData;
    const columns = window.queryResultColumns || data.columns;

    // Create CSV content
    let csv = columns.join(',') + '\n';

    data.rows.forEach(row => {
        const rowData = columns.map(col => {
            let value = row[col];
            // Handle null
            if (value === null || value === undefined) {
                return '';
            }
            // Convert to string and escape quotes
            value = String(value).replace(/"/g, '""');
            // Wrap in quotes if contains comma, newline, or quote
            if (value.includes(',') || value.includes('\n') || value.includes('"')) {
                return `"${value}"`;
            }
            return value;
        });
        csv += rowData.join(',') + '\n';
    });

    // Create download link
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `query_results_${Date.now()}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function printResults() {
    if (!window.currentQueryData || !window.currentQueryData.rows || window.currentQueryData.rows.length === 0) {
        alert('No data to print');
        return;
    }

    const data = window.currentQueryData;
    const columns = window.queryResultColumns || data.columns;

    // Create a new window for printing
    const printWindow = window.open('', '', 'height=600,width=800');
    printWindow.document.write('<html><head><title>Query Results</title>');
    printWindow.document.write('<style>');
    printWindow.document.write('body { font-family: Arial, sans-serif; margin: 20px; }');
    printWindow.document.write('table { width: 100%; border-collapse: collapse; }');
    printWindow.document.write('th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }');
    printWindow.document.write('th { background-color: #f8f9fa; font-weight: 600; }');
    printWindow.document.write('tr:nth-child(even) { background-color: #fafafa; }');
    printWindow.document.write('@media print { body { margin: 0; } }');
    printWindow.document.write('</style></head><body>');
    printWindow.document.write('<h2>Query Results</h2>');
    printWindow.document.write(`<p>${data.rows.length} rows</p>`);
    printWindow.document.write('<table><thead><tr>');

    columns.forEach(col => {
        printWindow.document.write(`<th>${col}</th>`);
    });

    printWindow.document.write('</tr></thead><tbody>');

    data.rows.forEach(row => {
        printWindow.document.write('<tr>');
        columns.forEach(col => {
            const value = row[col] === null ? '<em>null</em>' : row[col];
            printWindow.document.write(`<td>${value}</td>`);
        });
        printWindow.document.write('</tr>');
    });

    printWindow.document.write('</tbody></table>');
    printWindow.document.write('</body></html>');
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => {
        printWindow.print();
    }, 250);
}

async function executeQuery() {
    const sql = document.getElementById('sql-editor').value.trim();
    if (!sql) {
        alert('Please enter a SQL query');
        return;
    }

    const resultsDiv = document.getElementById('query-results');
    const errorDiv = document.getElementById('query-error');
    const statsDiv = document.getElementById('query-stats');

    // Clear previous results/errors
    errorDiv.style.display = 'none';
    resultsDiv.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #667eea;"><div style="text-align: center;"><div style="font-size: 2rem; margin-bottom: 8px;">⏳</div><div>Executing query...</div></div></div>';

    const startTime = Date.now();

    // Get selected connection and schema
    const connectionId = document.getElementById('connection-selector')?.value;
    const schema = document.getElementById('schema-selector')?.value;

    try {
        const response = await fetch('/api/query/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sql, connection_id: connectionId, schema })
        });

        const executionTime = Date.now() - startTime;

        if (!response.ok) {
            const error = await response.json();
            errorDiv.textContent = error.detail || 'Query execution failed';
            errorDiv.style.display = 'block';
            resultsDiv.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #999;">Query failed</div>';
            return;
        }

        const data = await response.json();

        // Show stats
        statsDiv.textContent = `${data.rows.length} rows returned in ${executionTime}ms`;

        // Show export buttons
        document.getElementById('export-buttons').style.display = 'flex';

        // Render results table
        if (data.rows.length === 0) {
            resultsDiv.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #999;">No rows returned</div>';
            document.getElementById('export-buttons').style.display = 'none';
            return;
        }

        const columns = data.columns || Object.keys(data.rows[0]);

        // Store column order globally for drag-and-drop
        if (!window.queryResultColumns) {
            window.queryResultColumns = columns;
        } else {
            window.queryResultColumns = columns;
        }

        // Initialize column widths if not set
        if (!window.columnWidths) {
            window.columnWidths = {};
        }

        let html = '<table id="results-table" style="width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.85rem;"><thead><tr>';

        // Headers with drag-and-drop and resize
        columns.forEach((col, index) => {
            const width = window.columnWidths[col] || 150;
            html += `<th draggable="true"
                         data-col-index="${index}"
                         data-col-name="${col}"
                         ondragstart="handleColumnDragStart(event)"
                         ondragover="handleColumnDragOver(event)"
                         ondrop="handleColumnDrop(event)"
                         ondragend="handleColumnDragEnd(event)"
                         style="padding: 10px; text-align: left; background: #f8f9fa; border-bottom: 2px solid #dee2e6; font-weight: 600; position: sticky; top: 0; color: #333; cursor: move; user-select: none; min-width: ${width}px; max-width: ${width}px; width: ${width}px; position: relative;">
                         <span style="margin-right: 4px;">⋮⋮</span>${col}
                         <div class="col-resizer" data-col-name="${col}"
                              onmousedown="startColumnResize(event, '${col}')"
                              style="position: absolute; right: 0; top: 0; bottom: 0; width: 5px; cursor: col-resize; z-index: 10;">
                         </div>
                     </th>`;
        });
        html += '</tr></thead><tbody>';

        // Rows
        data.rows.forEach((row, i) => {
            html += `<tr style="border-bottom: 1px solid #eee; ${i % 2 === 0 ? 'background: #fafafa;' : 'background: white;'}">`;
            columns.forEach(col => {
                const width = window.columnWidths[col] || 150;
                let value = row[col];
                // Format the value for display
                if (value === null) {
                    value = '<span style="color: #999; font-style: italic;">null</span>';
                } else if (typeof value === 'object') {
                    // For objects (JSONB, arrays, etc.), stringify them
                    value = JSON.stringify(value);
                }
                html += `<td style="padding: 8px 10px; color: #333; min-width: ${width}px; max-width: ${width}px; width: ${width}px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${value}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        resultsDiv.innerHTML = html;

        // Store the data globally for re-rendering after column reorder
        window.currentQueryData = data;

        // Save to query history
        saveQueryToHistory(sql);

    } catch (error) {
        console.error('Error executing query:', error);
        errorDiv.textContent = 'Network error: ' + error.message;
        errorDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #999;">Query failed</div>';
    }
}

// Query History Management
function saveQueryToHistory(sql) {
    if (!sql || sql.trim().length === 0) return;

    try {
        let history = JSON.parse(localStorage.getItem('sqlQueryHistory') || '[]');

        // Add query with timestamp
        history.unshift({
            query: sql,
            timestamp: new Date().toISOString(),
            database: document.getElementById('database-selector')?.value || 'transformdash',
            schema: document.getElementById('schema-selector')?.value || 'public'
        });

        // Keep only last 20 queries
        history = history.slice(0, 20);

        localStorage.setItem('sqlQueryHistory', JSON.stringify(history));
        renderQueryHistory();
    } catch (error) {
        console.error('Error saving query history:', error);
    }
}

function loadQueryHistory() {
    try {
        return JSON.parse(localStorage.getItem('sqlQueryHistory') || '[]');
    } catch (error) {
        console.error('Error loading query history:', error);
        return [];
    }
}

function renderQueryHistory() {
    const history = loadQueryHistory();
    const historyList = document.getElementById('query-history-list');

    if (!historyList) return;

    if (history.length === 0) {
        historyList.innerHTML = '<div style="padding: 12px; color: #999; font-size: 0.85rem;">No query history yet</div>';
        return;
    }

    let html = '';
    history.forEach((item, index) => {
        const date = new Date(item.timestamp);
        const timeStr = date.toLocaleTimeString();
        const dateStr = date.toLocaleDateString();
        const preview = item.query.length > 60 ? item.query.substring(0, 60) + '...' : item.query;

        html += `
            <div style="padding: 8px 12px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; gap: 8px;">
                <div style="flex: 1; min-width: 0;">
                    <div style="font-size: 0.75rem; color: #888; margin-bottom: 4px;">${dateStr} ${timeStr} • ${item.database}.${item.schema}</div>
                    <div style="font-size: 0.85rem; color: #333; font-family: 'Monaco', 'Menlo', monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${preview}</div>
                </div>
                <div style="display: flex; gap: 4px; flex-shrink: 0;">
                    <button onclick="copyQueryFromHistory(${index})" title="Copy" style="padding: 4px 8px; font-size: 0.75rem; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer;">📋</button>
                    <button onclick="runQueryFromHistory(${index})" title="Run" style="padding: 4px 8px; font-size: 0.75rem; border: 1px solid #667eea; background: #667eea; color: white; border-radius: 4px; cursor: pointer;">▶️</button>
                </div>
            </div>
        `;
    });

    historyList.innerHTML = html;
}

function copyQueryFromHistory(index) {
    const history = loadQueryHistory();
    if (index >= 0 && index < history.length) {
        const query = history[index].query;
        navigator.clipboard.writeText(query).then(() => {
            showToast('Query copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy:', err);
        });
    }
}

async function runQueryFromHistory(index) {
    const history = loadQueryHistory();
    if (index >= 0 && index < history.length) {
        const item = history[index];
        document.getElementById('sql-editor').value = item.query;

        // Optionally switch to the database/schema from history
        // Uncomment if you want to auto-switch context:
        // document.getElementById('database-selector').value = item.database;
        // await onDatabaseChange();
        // document.getElementById('schema-selector').value = item.schema;

        await executeQuery();
    }
}

function toggleQueryHistory() {
    const panel = document.getElementById('query-history-panel');
    const icon = document.getElementById('history-toggle-icon');

    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        icon.textContent = '🔽';
        renderQueryHistory();
    } else {
        panel.style.display = 'none';
        icon.textContent = '🔼';
    }
}

// Column drag-and-drop handlers for SQL results table
let draggedColumnIndex = null;
let isResizingColumn = false;
let resizingColumnName = null;
let startX = 0;
let startWidth = 0;

function startColumnResize(event, colName) {
    event.stopPropagation();
    event.preventDefault();

    isResizingColumn = true;
    resizingColumnName = colName;
    startX = event.clientX;
    startWidth = window.columnWidths[colName] || 150;

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    // Prevent drag-and-drop while resizing
    const th = event.target.closest('th');
    if (th) {
        th.draggable = false;
    }
}

document.addEventListener('mousemove', (event) => {
    if (!isResizingColumn || !resizingColumnName) return;

    const diff = event.clientX - startX;
    const newWidth = Math.max(80, startWidth + diff); // Min width 80px

    window.columnWidths[resizingColumnName] = newWidth;

    // Update all cells in this column
    const table = document.getElementById('results-table');
    if (table) {
        const colIndex = window.queryResultColumns.indexOf(resizingColumnName);
        if (colIndex >= 0) {
            // Update header
            const headers = table.querySelectorAll('thead th');
            if (headers[colIndex]) {
                headers[colIndex].style.minWidth = newWidth + 'px';
                headers[colIndex].style.maxWidth = newWidth + 'px';
                headers[colIndex].style.width = newWidth + 'px';
            }

            // Update all cells in this column
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells[colIndex]) {
                    cells[colIndex].style.minWidth = newWidth + 'px';
                    cells[colIndex].style.maxWidth = newWidth + 'px';
                    cells[colIndex].style.width = newWidth + 'px';
                }
            });
        }
    }
});

document.addEventListener('mouseup', (event) => {
    if (isResizingColumn) {
        isResizingColumn = false;
        resizingColumnName = null;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';

        // Re-enable drag-and-drop
        const headers = document.querySelectorAll('#results-table thead th');
        headers.forEach(th => {
            th.draggable = true;
        });
    }
});

function handleColumnDragStart(event) {
    // Don't start drag if we're resizing
    if (isResizingColumn) {
        event.preventDefault();
        return;
    }

    draggedColumnIndex = parseInt(event.target.dataset.colIndex);
    event.target.style.opacity = '0.5';
    event.dataTransfer.effectAllowed = 'move';
}

function handleColumnDragOver(event) {
    if (event.preventDefault) {
        event.preventDefault();
    }
    event.dataTransfer.dropEffect = 'move';
    event.target.style.borderLeft = '3px solid #667eea';
    return false;
}

function handleColumnDrop(event) {
    if (event.stopPropagation) {
        event.stopPropagation();
    }
    event.preventDefault();

    const targetColumnIndex = parseInt(event.target.dataset.colIndex);

    if (draggedColumnIndex !== null && draggedColumnIndex !== targetColumnIndex) {
        // Reorder columns array
        const columns = [...window.queryResultColumns];
        const draggedColumn = columns[draggedColumnIndex];
        columns.splice(draggedColumnIndex, 1);
        columns.splice(targetColumnIndex, 0, draggedColumn);
        window.queryResultColumns = columns;

        // Re-render table with new column order
        rerenderResultsTable(columns);
    }

    event.target.style.borderLeft = '';
    return false;
}

function handleColumnDragEnd(event) {
    event.target.style.opacity = '1';
    // Remove all border highlights
    document.querySelectorAll('#results-table th').forEach(th => {
        th.style.borderLeft = '';
    });
}

function rerenderResultsTable(columns) {
    const data = window.currentQueryData;
    if (!data || !data.rows) return;

    const resultsDiv = document.getElementById('query-results');
    let html = '<table id="results-table" style="width: 100%; border-collapse: collapse; font-size: 0.85rem;"><thead><tr>';

    // Headers with new order and widths
    columns.forEach((col, index) => {
        const width = window.columnWidths[col] || 150;
        html += `<th draggable="true"
                     data-col-index="${index}"
                     data-col-name="${col}"
                     ondragstart="handleColumnDragStart(event)"
                     ondragover="handleColumnDragOver(event)"
                     ondrop="handleColumnDrop(event)"
                     ondragend="handleColumnDragEnd(event)"
                     style="padding: 10px; text-align: left; background: #f8f9fa; border-bottom: 2px solid #dee2e6; font-weight: 600; position: sticky; top: 0; color: #333; cursor: move; user-select: none; min-width: ${width}px; max-width: ${width}px; width: ${width}px; position: relative;">
                     <span style="margin-right: 4px;">⋮⋮</span>${col}
                     <div class="col-resizer" data-col-name="${col}"
                          onmousedown="startColumnResize(event, '${col}')"
                          style="position: absolute; right: 0; top: 0; bottom: 0; width: 5px; cursor: col-resize; z-index: 10;">
                     </div>
                 </th>`;
    });
    html += '</tr></thead><tbody>';

    // Rows with new column order and widths
    data.rows.forEach((row, i) => {
        html += `<tr style="border-bottom: 1px solid #eee; ${i % 2 === 0 ? 'background: #fafafa;' : 'background: white;'}">`;
        columns.forEach(col => {
            const width = window.columnWidths[col] || 150;
            let value = row[col];
            // Format the value for display
            if (value === null) {
                value = '<span style="color: #999; font-style: italic;">null</span>';
            } else if (typeof value === 'object') {
                // For objects (JSONB, arrays, etc.), stringify them
                value = JSON.stringify(value);
            }
            html += `<td style="padding: 8px 10px; color: #333; min-width: ${width}px; max-width: ${width}px; width: ${width}px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${value}</td>`;
        });
        html += '</tr>';
    });

    html += '</tbody></table>';
    resultsDiv.innerHTML = html;
}

// Load schema when switching to query lab view
document.addEventListener('DOMContentLoaded', function() {
    const originalSwitchView = window.switchView;
    window.switchView = function(viewName) {
        originalSwitchView(viewName);
        if (viewName === 'query-lab') {
            loadConnections();
            initializeResizers();
        }
    };
});

// Initialize panel resizers
function initializeResizers() {
    // Horizontal resizer (sidebar width)
    const hResizer = document.getElementById('h-resizer');
    const sidebar = document.getElementById('sql-sidebar');

    if (hResizer && sidebar) {
        let isResizing = false;

        hResizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;

            const newWidth = e.clientX - sidebar.getBoundingClientRect().left;
            if (newWidth >= 200 && newWidth <= 500) {
                sidebar.style.width = newWidth + 'px';
            }
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        });
    }

    // Vertical resizer (editor height)
    const vResizer = document.getElementById('v-resizer');
    const editorPanel = document.getElementById('sql-editor-panel');

    if (vResizer && editorPanel) {
        let isResizing = false;

        vResizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            document.body.style.cursor = 'row-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;

            const newHeight = e.clientY - editorPanel.getBoundingClientRect().top;
            if (newHeight >= 150 && newHeight <= 600) {
                editorPanel.style.height = newHeight + 'px';
            }
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        });
    }
}

// Show the SQL query for a chart
// Store current SQL query for copying
let currentSqlQuery = '';

function showChartQuery(chartConfig) {
    try {
        // Validate chart config has necessary fields
        if (!chartConfig || !chartConfig.model) {
            alert('Cannot generate query: Chart is missing required model/table information');
            console.error('Invalid chart config:', chartConfig);
            return;
        }

        // Build the SQL query based on chart configuration
        let sql = '';

        if (chartConfig.type === 'table') {
            // Table query - simple SELECT with columns
            if (chartConfig.columns && Array.isArray(chartConfig.columns) && chartConfig.columns.length > 0) {
                const columnsList = chartConfig.columns.map(col => col.name || col).join(', ');
                sql = `SELECT ${columnsList}\nFROM public.${chartConfig.model}`;
            } else {
                sql = `SELECT *\nFROM public.${chartConfig.model}`;
            }

            // Add filters if any
            if (chartConfig.filters && Array.isArray(chartConfig.filters) && chartConfig.filters.length > 0) {
                const whereClauses = chartConfig.filters.map(f => {
                    if (f.value === 'CURRENT_YEAR') {
                        return `${f.field} = EXTRACT(YEAR FROM CURRENT_DATE)`;
                    } else if (f.value === 'CURRENT_MONTH') {
                        return `${f.field} = EXTRACT(MONTH FROM CURRENT_DATE)`;
                    } else {
                        return `${f.field} ${f.operator} '${f.value}'`;
                    }
                });
                sql += `\nWHERE ` + whereClauses.join(' AND ');
            }

            sql += `\nLIMIT 100`;
        } else if (chartConfig.type === 'metric') {
            // Metric query
            const metricField = chartConfig.metric || chartConfig.y_axis;
            if (!metricField) {
                alert('Cannot generate query: Metric field is missing');
                return;
            }
            const agg = (chartConfig.aggregation || 'sum').toUpperCase();
            sql = `SELECT ${agg}(${metricField}) as value\nFROM public.${chartConfig.model}`;

            // Add filters
            if (chartConfig.filters && Array.isArray(chartConfig.filters) && chartConfig.filters.length > 0) {
                const whereClauses = chartConfig.filters.map(f => {
                    if (f.value === 'CURRENT_YEAR') {
                        return `${f.field} = EXTRACT(YEAR FROM CURRENT_DATE)`;
                    } else if (f.value === 'CURRENT_MONTH') {
                        return `${f.field} = EXTRACT(MONTH FROM CURRENT_DATE)`;
                    } else {
                        return `${f.field} ${f.operator} '${f.value}'`;
                    }
                });
                sql += `\nWHERE ` + whereClauses.join(' AND ');
            }
        } else if (chartConfig.metrics && Array.isArray(chartConfig.metrics)) {
            // Multi-metric query
            const metricSelects = chartConfig.metrics.map(m => {
                const agg = (m.aggregation || 'sum').toUpperCase();
                return `${agg}(${m.field}) as ${m.field}`;
            }).join(',\n      ');

            sql = `SELECT\n    ${chartConfig.x_axis} as label,\n      ${metricSelects}\nFROM public.${chartConfig.model}`;
            sql += `\nWHERE ${chartConfig.x_axis} IS NOT NULL`;

            // Add filters
            if (chartConfig.filters && Array.isArray(chartConfig.filters) && chartConfig.filters.length > 0) {
                const whereClauses = chartConfig.filters.map(f => `${f.field} ${f.operator} '${f.value}'`);
                sql += ' AND ' + whereClauses.join(' AND ');
            }

            sql += `\nGROUP BY ${chartConfig.x_axis}\nORDER BY ${chartConfig.x_axis}\nLIMIT 50`;
        } else {
            // Regular chart query
            if (!chartConfig.x_axis || !chartConfig.y_axis) {
                alert('Cannot generate query: Chart is missing x_axis or y_axis configuration');
                return;
            }
            const agg = (chartConfig.aggregation || 'sum').toUpperCase();
            sql = `SELECT\n    ${chartConfig.x_axis} as label,\n    ${agg}(${chartConfig.y_axis}) as value\nFROM public.${chartConfig.model}`;
            sql += `\nWHERE ${chartConfig.x_axis} IS NOT NULL`;

            // Add filters
            if (chartConfig.filters && Array.isArray(chartConfig.filters) && chartConfig.filters.length > 0) {
                const whereClauses = chartConfig.filters.map(f => {
                    if (f.value === 'CURRENT_YEAR') {
                        return `${f.field} = EXTRACT(YEAR FROM CURRENT_DATE)`;
                    } else if (f.value === 'CURRENT_MONTH') {
                        return `${f.field} = EXTRACT(MONTH FROM CURRENT_DATE)`;
                    } else {
                        return `${f.field} ${f.operator} '${f.value}'`;
                    }
                });
                sql += ' AND ' + whereClauses.join(' AND ');
            }

            sql += `\nGROUP BY ${chartConfig.x_axis}\nORDER BY ${chartConfig.x_axis}\nLIMIT 50`;
        }

        // Store SQL for copying
        currentSqlQuery = sql;

        // Update modal content
        console.log('🔍 Looking for modal elements...');
        const modalTitle = document.getElementById('sqlQueryModalTitle');
        const modalCode = document.getElementById('sqlQueryCode');
        const modal = document.getElementById('sqlQueryModal');
        const copyButton = document.getElementById('copySqlButton');

        console.log('Modal elements found:', {
            modalTitle: !!modalTitle,
            modalCode: !!modalCode,
            modal: !!modal,
            copyButton: !!copyButton
        });

        if (!modalTitle || !modalCode || !modal || !copyButton) {
            // Fallback to alert if modal elements don't exist
            console.error('❌ Modal elements missing! Check HTML for sqlQueryModal');
            alert('SQL Query:\n\n' + sql + '\n\n(Modal not found - check console for query)');
            console.log('SQL Query:', sql);
            return;
        }

        console.log('✅ All modal elements found, showing modal...');

        modalTitle.textContent = `SQL Query: ${chartConfig.title}`;
        modalCode.textContent = sql;

        // Reset button text
        copyButton.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 0.5rem;">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
            Copy SQL
        `;

        // Show modal
        modal.style.display = 'flex';

        // Also log to console for easy copying
        console.log('SQL Query:', sql);
    } catch (error) {
        console.error('Error generating SQL query:', error);
        alert('Error generating SQL query: ' + error.message + '\n\nCheck console for details');
    }
}

function copySqlQuery() {
    navigator.clipboard.writeText(currentSqlQuery).then(() => {
        // Update button to show success
        const copyButton = document.getElementById('copySqlButton');
        copyButton.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 0.5rem;">
                <polyline points="20 6 9 17 4 12"/>
            </svg>
            Copied!
        `;

        // Reset button after 2 seconds
        setTimeout(() => {
            copyButton.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 0.5rem;">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
                Copy SQL
            `;
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy SQL:', err);
        alert('Failed to copy to clipboard');
    });
}

// Edit an existing chart
async function editChart(chartConfig) {
    console.log('editChart called with:', chartConfig);

    // Store the chart ID for saving later
    currentEditingChartId = chartConfig.id;

    // Switch to chart builder view first
    switchView('chart-builder');

    // Wait for view to render and load dashboards
    await new Promise(resolve => setTimeout(resolve, 100));

    // Ensure dashboards are loaded before trying to set the value
    await loadChartDashboards();

    // Set default connection and schema for old charts that don't have them
    const connectionEl = document.getElementById('chartConnection');
    const schemaEl = document.getElementById('chartSchema');
    const dashboardEl = document.getElementById('chartDashboard');

    if (connectionEl && !chartConfig.connection_id) {
        // Set to default connection (first option after placeholder)
        if (connectionEl.options.length > 1) {
            connectionEl.selectedIndex = 1;
            await loadChartSchemas();
        }
    }

    if (schemaEl && !chartConfig.schema) {
        // Set to 'public' schema if available
        const publicOption = Array.from(schemaEl.options).find(opt => opt.value === 'public');
        if (publicOption) {
            schemaEl.value = 'public';
            await loadChartTables();
        } else if (schemaEl.options.length > 1) {
            schemaEl.selectedIndex = 1;
            await loadChartTables();
        }
    }

    // Set dashboard to the chart's dashboard or leave as standalone
    if (dashboardEl) {
        // Check for both dashboard_id and dashboardId (different sources use different naming)
        const dashboardId = chartConfig.dashboard_id || chartConfig.dashboardId;
        if (dashboardId) {
            console.log(`Setting dashboard to: ${dashboardId}`);
            dashboardEl.value = dashboardId;
            console.log(`Dashboard field value after setting: ${dashboardEl.value}`);
        } else {
            // Chart is standalone (no dashboard assignment), leave dropdown at placeholder
            console.log('No dashboard_id in chart config, leaving as standalone chart');
            dashboardEl.selectedIndex = 0; // Select the placeholder/standalone option
        }
    }

    // Immediately clear any existing chart preview to avoid showing old content
    const chartPlaceholder = document.getElementById('chartPlaceholder');
    const chartCanvas = document.getElementById('chartCanvas');
    const chartTableContainer = document.getElementById('chartTableContainer');

    if (chartPlaceholder) chartPlaceholder.style.display = 'block';
    if (chartCanvas) chartCanvas.style.display = 'none';
    if (chartTableContainer) {
        chartTableContainer.style.display = 'none';
        chartTableContainer.innerHTML = '';
    }

    // Destroy any existing chart on the canvas
    if (chartCanvas) {
        const existingChart = Chart.getChart(chartCanvas);
        if (existingChart) {
            existingChart.destroy();
        }
    }

    // Pre-fill the form with chart data
    const titleEl = document.getElementById('chartTitle');
    const descriptionEl = document.getElementById('chartDescription');
    const tableEl = document.getElementById('chartTable');

    if (!titleEl || !tableEl) {
        console.error('Form elements not found!');
        return;
    }

    titleEl.value = chartConfig.title || '';
    if (descriptionEl) {
        descriptionEl.value = chartConfig.description || '';
    }

    // Add the table option if it doesn't exist in the select
    const tableName = chartConfig.model;
    if (tableName) {
        const existingOption = Array.from(tableEl.options).find(opt => opt.value === tableName);
        if (!existingOption) {
            console.log(`Adding missing table option: ${tableName}`);
            const newOption = document.createElement('option');
            newOption.value = tableName;
            newOption.textContent = tableName;
            tableEl.appendChild(newOption);
        }
    }

    tableEl.value = tableName || '';

    console.log('Set title to:', chartConfig.title);
    console.log('Set table to:', tableName);

    // Verify the values were actually set
    console.log('Verification - Title field value:', titleEl.value);
    console.log('Verification - Table field value:', tableEl.value);

    // Load table columns to populate the dropdowns (but not for table charts - they handle it separately)
    if (chartConfig.type !== 'table') {
        await loadTableColumns();
        // Verify table value after loadTableColumns
        console.log('After loadTableColumns - Table field value:', document.getElementById('chartTable')?.value);
    } else {
        console.log('Skipping loadTableColumns for table chart - will be handled in table restoration code');
    }

    // Wait for columns to load, then set everything including chart type
    setTimeout(async () => {
        const xAxisEl = document.getElementById('chartXAxis');
        const yAxisEl = document.getElementById('chartYAxis');
        const aggregationEl = document.getElementById('chartAggregation');
        const chartTypeEl = document.getElementById('chartType');

        console.log('Form elements found:', {
            xAxis: !!xAxisEl,
            yAxis: !!yAxisEl,
            aggregation: !!aggregationEl,
            chartType: !!chartTypeEl
        });

        // Set chart type in the timeout to ensure it's after all DOM updates
        if (chartTypeEl) {
            const chartType = chartConfig.type || 'bar';

            // Add the chart type option if it doesn't exist (e.g., 'metric')
            const existingOption = Array.from(chartTypeEl.options).find(opt => opt.value === chartType);
            if (!existingOption) {
                console.log(`Adding missing chart type option: ${chartType}`);
                const newOption = document.createElement('option');
                newOption.value = chartType;
                newOption.textContent = chartType === 'metric' ? '🔢 Metric' : chartType;
                chartTypeEl.appendChild(newOption);
            }

            chartTypeEl.value = chartType;
            console.log('Set chart type to:', chartType);
            console.log('Verification - Chart type field value:', chartTypeEl.value);

            // Trigger chart type change to show/hide appropriate fields
            handleChartTypeChange();

            // For table charts, restore the columns AFTER handleChartTypeChange (which skipped loadTableColumnsForBuilder)
            if (chartType === 'table' && chartConfig.columns && chartConfig.columns.length > 0) {
                console.log('Restoring table columns:', chartConfig.columns);

                // Get the table name from the form element
                const currentTable = document.getElementById('chartTable')?.value || chartConfig.model;
                console.log('Fetching columns for table:', currentTable);

                // First, fetch the available columns for this table
                const response = await fetch(`/api/tables/${currentTable}/columns`);
                const data = await response.json();
                const availableColumns = data.columns || [];
                console.log('Available columns fetched for rendering:', availableColumns);

                // Clear and populate tableColumns array
                tableColumns = [];
                chartConfig.columns.forEach(col => {
                    tableColumns.push({
                        id: 'col_' + Date.now() + '_' + Math.random(),
                        field: col,
                        function: 'none',
                        label: col
                    });
                });

                // Render the columns in the UI
                renderTableColumns(availableColumns);
                console.log('Table columns restored:', tableColumns);
            }
        } else {
            console.error('Chart type element not found!');
        }

        // For metric charts, use the metric field for both x and y axis
        if (chartConfig.type === 'metric') {
            const metricField = chartConfig.metric || chartConfig.y_axis;
            if (metricField && xAxisEl && yAxisEl) {
                xAxisEl.value = metricField;
                yAxisEl.value = metricField;
                console.log('Set metric chart axes to:', metricField);
            }
        } else {
            // For regular charts, use x_axis and y_axis
            if (chartConfig.x_axis && xAxisEl) {
                xAxisEl.value = chartConfig.x_axis;
                console.log('Set X axis to:', chartConfig.x_axis);
            }
            if (chartConfig.y_axis && yAxisEl) {
                yAxisEl.value = chartConfig.y_axis;
                console.log('Set Y axis to:', chartConfig.y_axis);
            }
        }

        if (chartConfig.aggregation && aggregationEl) {
            aggregationEl.value = chartConfig.aggregation;
            console.log('Set aggregation to:', chartConfig.aggregation);
        }

        // For stacked bar charts, restore the category field (after handleChartTypeChange has shown the field)
        if (chartConfig.type === 'bar-stacked' && chartConfig.category) {
            const categoryEl = document.getElementById('chartCategory');
            if (categoryEl) {
                categoryEl.value = chartConfig.category;
                console.log('Restored category field to:', chartConfig.category);
            }
        }

        // Clear filters when editing a chart (don't inherit dashboard filters)
        chartFilters = [];
        renderFilters();

        // Automatically preview the chart with existing data
        // Wait a bit more to ensure dropdowns are populated
        setTimeout(async () => {
            console.log('Auto-previewing chart...');

            // Verify form values before creating chart
            const currentTable = document.getElementById('chartTable')?.value;
            const currentChartType = document.getElementById('chartType')?.value;
            const currentXAxis = document.getElementById('chartXAxis')?.value;
            const currentYAxis = document.getElementById('chartYAxis')?.value;

            console.log('Current form values:', {
                table: currentTable,
                chartType: currentChartType,
                xAxis: currentXAxis,
                yAxis: currentYAxis,
                tableColumns: tableColumns
            });

            // For table charts, check if we have table and columns
            if (currentChartType === 'table') {
                console.log('DEBUG Auto-preview: currentTable =', currentTable);
                console.log('DEBUG Auto-preview: tableColumns =', tableColumns);
                console.log('DEBUG Auto-preview: tableColumns.length =', tableColumns ? tableColumns.length : 'undefined');
                if (currentTable && tableColumns && tableColumns.length > 0) {
                    await createChart();
                } else {
                    console.warn('Table chart not ready yet (need table and columns)', {currentTable, tableColumns});
                }
            } else {
                // For other chart types, check for table, xAxis, and yAxis
                if (currentTable && currentXAxis && currentYAxis) {
                    await createChart();
                } else {
                    console.warn('Form not fully populated yet, skipping auto-preview');
                }
            }
        }, 200);
    }, 600);

    showToast('Chart loaded for editing', 'info');
}

// Delete a chart with confirmation
function showChartQuery(chart) {
    // Build the SQL query based on chart configuration
    let query = '';

    if (chart.type === 'table') {
        // Table chart query
        const columns = chart.columns && chart.columns.length > 0
            ? chart.columns.join(', ')
            : '*';
        query = `SELECT ${columns}\nFROM ${chart.model}\nLIMIT 1000;`;
    } else if (chart.type === 'metric') {
        // Metric chart query
        query = `SELECT ${chart.aggregation}(${chart.y_axis}) as value\nFROM ${chart.model};`;
    } else {
        // Regular chart query (bar, line, pie, etc.)
        let selectClause = `${chart.x_axis}`;
        if (chart.y_axis) {
            selectClause += `, ${chart.aggregation}(${chart.y_axis}) as value`;
        }
        if (chart.category) {
            selectClause += `, ${chart.category}`;
        }

        query = `SELECT ${selectClause}\nFROM ${chart.model}`;

        if (chart.x_axis) {
            query += `\nGROUP BY ${chart.x_axis}`;
            if (chart.category) {
                query += `, ${chart.category}`;
            }
        }

        if (chart.y_axis) {
            query += `\nORDER BY value DESC`;
        }

        query += ';';
    }

    // Show query in a modal/alert
    const message = `SQL Query for "${chart.title}":\n\n${query}`;
    alert(message);
}

async function deleteChart(chartConfig) {
    if (!confirm(`Are you sure you want to delete "${chartConfig.title}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/charts/${chartConfig.id}`, {
            method: 'DELETE'
        });

        // Check for permission error
        if (response.status === 403) {
            showToast('⛔ Access Denied: You do not have permission to delete charts', 'error');
            return;
        }

        if (!response.ok) {
            const error = await response.json();
            showToast(`Failed to delete chart: ${error.detail || 'Unknown error'}`, 'error');
            return;
        }

        const result = await response.json();

        if (result.success) {
            showToast(result.message, 'success');
            loadAllCharts(); // Reload the charts list
        } else {
            showToast('Failed to delete chart', 'error');
        }
    } catch (error) {
        console.error('Error deleting chart:', error);
        showToast('Error deleting chart', 'error');
    }
}

async function createChart() {
    const title = document.getElementById('chartTitle').value || 'Chart';
    const connection = document.getElementById('chartConnection').value;
    const schema = document.getElementById('chartSchema').value;
    const table = document.getElementById('chartTable').value;
    const chartType = document.getElementById('chartType').value;
    const xAxis = document.getElementById('chartXAxis').value;
    const yAxis = document.getElementById('chartYAxis').value;
    const aggregation = document.getElementById('chartAggregation').value;

    // For table charts, get columns from the global variable or initialize it
    let selectedTableColumns = (typeof tableColumns !== 'undefined') ? tableColumns : [];

    console.log('createChart called with:', { connection, schema, table, chartType, xAxis, yAxis, aggregation, tableColumns: selectedTableColumns });

    // Validation - different for table charts vs regular charts
    if (chartType === 'table') {
        // Table charts only need connection, schema, table, and at least one column
        if (!connection || !schema || !table) {
            const errorEl = document.getElementById('chartError');
            if (errorEl) {
                errorEl.style.display = 'block';
                errorEl.textContent = 'Please select connection, schema, and table';
            }
            console.warn('Validation failed:', { connection, schema, table });
            return;
        }
        if (!selectedTableColumns || selectedTableColumns.length === 0) {
            const errorEl = document.getElementById('chartError');
            if (errorEl) {
                errorEl.style.display = 'block';
                errorEl.textContent = 'Please add at least one column to your table';
            }
            console.warn('Validation failed: no columns added');
            return;
        }
    } else {
        // Regular charts need xAxis and yAxis
        if (!connection || !schema || !table || !xAxis || !yAxis) {
            const errorEl = document.getElementById('chartError');
            if (errorEl) {
                errorEl.style.display = 'block';
                errorEl.textContent = 'Please select connection, schema, table, X-axis, and Y-axis';
            }
            console.warn('Validation failed:', { connection, schema, table, xAxis, yAxis });
            return;
        }
    }

    const errorEl = document.getElementById('chartError');
    if (errorEl) {
        errorEl.style.display = 'none';
    }

    try {
        // Get active filters
        const filters = getActiveFilters();

        // Build query payload with connection and schema
        // Note: Don't prefix table with schema - backend adds it
        const payload = {
            table: table,
            connection_id: connection,
            schema: schema,
            type: chartType,
            x_axis: xAxis,
            y_axis: yAxis,
            aggregation
        };

        // For table charts, add columns array
        if (chartType === 'table') {
            if (!selectedTableColumns || selectedTableColumns.length === 0) {
                throw new Error('No columns selected for table chart');
            }
            payload.columns = selectedTableColumns.map(col => col.field);
        }

        // For metric charts, add metric field
        if (chartType === 'metric') {
            payload.metric = xAxis; // For metrics, x and y are the same
        }

        // For stacked bar charts, add category field
        if (chartType === 'bar-stacked') {
            const category = document.getElementById('chartCategory')?.value;
            if (category) {
                payload.category = category;
            }
        }

        // Add filters if present - convert array to dict format
        if (filters.length > 0) {
            const filterDict = {};
            filters.forEach(f => {
                if (f.operator === '=') {
                    filterDict[f.field] = f.value;
                }
                // TODO: Handle other operators (>, <, LIKE, etc.)
            });
            if (Object.keys(filterDict).length > 0) {
                payload.filters = filterDict;
            }
        }

        console.log('Chart builder query payload:', payload);

        // Query data
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Chart builder API error:', response.status, errorText);
            throw new Error(`API returned ${response.status}: ${errorText}`);
        }

        const data = await response.json();

        // Hide all preview containers
        document.getElementById('chartPlaceholder').style.display = 'none';
        document.getElementById('chartCanvas').style.display = 'none';
        document.getElementById('chartTableContainer').style.display = 'none';

        // Handle metric chart type
        if (chartType === 'metric') {
            const metricContainer = document.getElementById('chartTableContainer');
            metricContainer.style.display = 'block';

            // Get metric value - backend returns 'value' field for metrics
            const metricValue = data.value ?? (data.values && data.values.length > 0 ? data.values.reduce((a, b) => a + b, 0) : 0);

            console.log('Metric value for chart builder:', metricValue);

            metricContainer.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px; background: var(--color-bg-secondary); border-radius: 12px;">
                    <div style="font-size: 4rem; font-weight: 700; color: #667eea; margin-bottom: 16px;">
                        ${metricValue.toLocaleString()}
                    </div>
                    <div style="font-size: 1.2rem; color: #888; text-transform: uppercase; letter-spacing: 1px;">
                        ${aggregation} ${title}
                    </div>
                </div>
            `;
        } else if (chartType === 'table') {
            const tableContainer = document.getElementById('chartTableContainer');
            tableContainer.style.display = 'block';

            // For table charts, backend returns columns and data arrays
            const columns = data.columns || [];
            const rows = data.data || [];

            // Create HTML table
            let tableHTML = '<table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">';
            tableHTML += '<thead><tr>';

            // Add header for each column
            columns.forEach(col => {
                tableHTML += `<th style="padding: 0.75rem; text-align: left; border-bottom: 2px solid var(--color-border); background: var(--color-bg-secondary); font-weight: 600;">${col}</th>`;
            });

            tableHTML += '</tr></thead><tbody>';

            // Add row data
            rows.forEach(row => {
                tableHTML += '<tr>';
                columns.forEach(col => {
                    const value = row[col] !== null && row[col] !== undefined ? row[col] : '';
                    tableHTML += `<td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">${value}</td>`;
                });
                tableHTML += '</tr>';
            });

            tableHTML += '</tbody></table>';
            tableContainer.innerHTML = tableHTML;
        } else {
            // Show canvas for chart types
            const canvasEl = document.getElementById('chartCanvas');
            canvasEl.style.display = 'block';

            // Destroy existing chart if any
            if (currentChart) {
                currentChart.destroy();
                currentChart = null;
            }

            // Also destroy any chart attached to this canvas by Chart.js
            const existingChart = Chart.getChart(canvasEl);
            if (existingChart) {
                console.log('Destroying existing chart on canvas');
                existingChart.destroy();
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
                chartOptions.plugins.legend = { display: true };
            } else if (chartType !== 'pie' && chartType !== 'doughnut') {
                chartOptions.scales = {
                    y: { beginAtZero: true }
                };
            }

            // Prepare datasets
            let datasets;
            const colors = [
                { bg: 'rgba(102, 126, 234, 0.8)', border: 'rgba(102, 126, 234, 1)' },
                { bg: 'rgba(16, 185, 129, 0.8)', border: 'rgba(16, 185, 129, 1)' },
                { bg: 'rgba(245, 158, 11, 0.8)', border: 'rgba(245, 158, 11, 1)' },
                { bg: 'rgba(239, 68, 68, 0.8)', border: 'rgba(239, 68, 68, 1)' },
                { bg: 'rgba(139, 92, 246, 0.8)', border: 'rgba(139, 92, 246, 1)' },
                { bg: 'rgba(236, 72, 153, 0.8)', border: 'rgba(236, 72, 153, 1)' },
            ];

            if (data.datasets && Array.isArray(data.datasets)) {
                // Stacked chart with multiple datasets from backend
                datasets = data.datasets.map((ds, idx) => ({
                    label: ds.label,
                    data: ds.data,
                    backgroundColor: colors[idx % colors.length].bg,
                    borderColor: colors[idx % colors.length].border,
                    borderWidth: 2
                }));
            } else {
                // Regular chart with single dataset
                datasets = [{
                    label: `${aggregation.toUpperCase()}(${yAxis})`,
                    data: data.values,
                    backgroundColor: colors.map(c => c.bg),
                    borderColor: colors[0].border,
                    borderWidth: 2
                }];
            }

            // Create new chart
            const ctx = document.getElementById('chartCanvas').getContext('2d');
            currentChart = new Chart(ctx, {
                type: actualChartType,
                data: {
                    labels: data.labels,
                    datasets: datasets
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
    const description = document.getElementById('chartDescription').value || '';
    const table = document.getElementById('chartTable').value;
    let chartType = document.getElementById('chartType').value;
    const xAxis = document.getElementById('chartXAxis').value;
    const yAxis = document.getElementById('chartYAxis').value;
    const aggregation = document.getElementById('chartAggregation').value;
    const dashboardSelect = document.getElementById('chartDashboard');
    let dashboardId = dashboardSelect.value || null;  // null means standalone chart

    // No validation for dashboard - it's optional now (standalone charts allowed)

    // For table charts, only table is required
    if (chartType === 'table') {
        if (!table) {
            alert('Please select a data source');
            return;
        }
        // Get columns from the global variable
        let selectedTableColumns = (typeof tableColumns !== 'undefined') ? tableColumns : [];
        if (!selectedTableColumns || selectedTableColumns.length === 0) {
            alert('Please add at least one column to your table');
            return;
        }
    } else {
        // For other chart types, xAxis and yAxis are required
        if (!table) {
            alert('Please select a data source');
            return;
        }
        if (!xAxis || !yAxis) {
            alert('Please select both X-Axis and Y-Axis fields');
            return;
        }
    }

    // Handle "Create New Dashboard" option
    const isCreatingNewDashboard = (dashboardId === '__new__');
    if (isCreatingNewDashboard) {
        const newDashboardName = document.getElementById('newDashboardName').value;
        const newDashboardDescription = document.getElementById('newDashboardDescription').value;

        if (!newDashboardName) {
            alert('Please enter a name for the new dashboard');
            return;
        }

        // Keep dashboard_id as '__new__' for backend to recognize
        // Don't change it here
    }

    const saveBtn = document.getElementById('saveChartBtn');
    const originalText = saveBtn.textContent;
    saveBtn.textContent = '💾 Saving...';
    saveBtn.disabled = true;

    try {
        // Use existing chart ID if editing, otherwise generate new one
        const chartId = currentEditingChartId || `chart_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const isEditing = !!currentEditingChartId;

        console.log(isEditing ? `Updating existing chart: ${chartId}` : `Creating new chart: ${chartId}`);

        // Convert bar-stacked to bar for storage (with metadata to indicate stacking)
        let actualType = chartType;
        if (chartType === 'bar-stacked') {
            actualType = 'bar';
        }

        // Get active filters
        const filters = getActiveFilters();

        // Save chart configuration
        const chartConfig = {
            id: chartId,
            title: title,
            description: description,
            type: chartType,  // Save the original type
            model: table,
            x_axis: xAxis,
            y_axis: yAxis,
            aggregation: aggregation,
            dashboard_id: dashboardId
        };

        // For metric charts, add the metric field
        if (chartType === 'metric') {
            chartConfig.metric = xAxis; // For metrics, x and y are the same
        }

        // For table charts, add columns array
        if (chartType === 'table') {
            console.log('DEBUG: tableColumns at save time:', tableColumns);
            let selectedTableColumns = (typeof tableColumns !== 'undefined' && tableColumns.length > 0) ? tableColumns : [];
            console.log('DEBUG: selectedTableColumns:', selectedTableColumns);

            if (selectedTableColumns.length > 0) {
                const columnFields = selectedTableColumns
                    .filter(col => col.field && col.field !== '')
                    .map(col => col.field);
                console.log('DEBUG: columnFields to save:', columnFields);
                chartConfig.columns = columnFields;
            }
        }

        // For stacked bar charts, add category field
        if (chartType === 'bar-stacked') {
            const category = document.getElementById('chartCategory')?.value;
            console.log('DEBUG: Saving stacked chart with category:', category);
            if (category) {
                chartConfig.category = category;
            }
        }

        // Only add filters if there are any
        if (filters.length > 0) {
            chartConfig.filters = filters;
        }

        // If creating a new dashboard, include dashboard details
        if (dashboardSelect.value === '__new__') {
            chartConfig.dashboard_name = document.getElementById('newDashboardName').value;
            chartConfig.dashboard_description = document.getElementById('newDashboardDescription').value;
        }

        console.log('DEBUG: Final chartConfig being sent to backend:', chartConfig);

        const response = await fetch('/api/charts/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(chartConfig)
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
            await showChartSavedModal(result.dashboard_id, chartId, title);

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

async function showChartSavedModal(dashboardId, chartId, title) {
    // Handle standalone charts (no dashboard)
    const isStandalone = !dashboardId || dashboardId === 'null';

    let dashboardName = null;
    if (!isStandalone) {
        // Fetch dashboard name from API
        try {
            const response = await fetch('/api/dashboards');
            const data = await response.json();
            const dashboard = data.dashboards?.find(d => d.id === dashboardId);
            if (dashboard) {
                dashboardName = dashboard.name;
            }
        } catch (error) {
            console.error('Error fetching dashboard name:', error);
        }
    }

    const modal = document.createElement('div');
    modal.className = 'modal active';
    modal.id = 'chart-saved-modal';

    // Different message for standalone vs dashboard charts
    const messageHtml = isStandalone
        ? `Your chart "<strong>${title}</strong>" has been saved as a standalone chart in the global chart library.`
        : `Your chart "<strong>${title}</strong>" has been saved to the "<strong>${dashboardName}</strong>" dashboard.`;

    // Different buttons for standalone vs dashboard charts
    const buttonsHtml = isStandalone
        ? `<button class="btn btn-primary" style="width: 100%;" onclick="closeChartSavedModal();">
               Continue Creating Charts
           </button>`
        : `<button class="btn btn-primary" style="width: 100%;" onclick="viewChartInDashboard('${dashboardId}'); closeChartSavedModal();">
               📊 View in Dashboard
           </button>
           <button class="btn btn-secondary" style="width: 100%;" onclick="closeChartSavedModal();">
               Continue Creating Charts
           </button>`;

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
                    ${messageHtml}
                </p>
                <div style="display: flex; gap: 0.75rem; flex-direction: column;">
                    ${buttonsHtml}
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

async function closeChartSavedModal() {
    const modal = document.getElementById('chart-saved-modal');
    if (modal) {
        modal.remove();
    }

    // Reload dashboards to show the newly created chart
    await loadDashboards();

    // Also refresh the charts list if currently viewing charts
    const chartsView = document.getElementById('charts-view');
    if (chartsView && chartsView.classList.contains('active')) {
        await loadAllCharts();
    }
}

async function viewChartInDashboard(dashboardId) {
    // Switch to dashboards view
    switchView('dashboards');

    // Reload dashboards to get the latest data
    await loadDashboards();

    // Wait a bit for rendering
    await new Promise(resolve => setTimeout(resolve, 100));

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

            // Build failed models list if any
            let failedModelsHtml = '';
            if (data.summary.failures > 0 && data.summary.model_results) {
                const failedModels = data.summary.model_results.filter(m => m.status === 'failed');
                failedModelsHtml = `
                    <div style="margin-top: 12px; padding: 12px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px;">
                        <strong style="color: #dc2626;">Failed Models:</strong>
                        <ul style="margin: 8px 0 0 0; padding-left: 20px;">
                            ${failedModels.map(m => `
                                <li style="margin: 4px 0;">
                                    <a href="#" onclick="scrollToModel('${m.name}'); return false;"
                                       style="color: #dc2626; text-decoration: underline; cursor: pointer;">
                                        ${m.name}
                                    </a>
                                    ${m.error ? `<br><span style="font-size: 0.85em; color: #991b1b;">Error: ${m.error}</span>` : ''}
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                `;
            }

            statusDiv.innerHTML = `
                <strong>✅ Transformations completed successfully!</strong><br>
                <p>Total Models: ${data.summary.total_models}</p>
                <p>✓ Successes: ${data.summary.successes}</p>
                <p>✗ Failures: ${data.summary.failures}</p>
                <p>⏱️ Total Time: ${data.summary.total_execution_time.toFixed(3)}s</p>
                ${failedModelsHtml}
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
// Store filter expressions (SQL transformations) per dashboard
let dashboardFilterExpressions = {};

async function loadDashboardFilters(dashboardId, container) {
    try {
        // Fetch dashboard configuration from /api/dashboards
        const response = await fetch('/api/dashboards');
        const data = await response.json();

        // Find the specific dashboard
        const dashboard = data.dashboards.find(d => d.id === dashboardId);

        if (!dashboard || !dashboard.filters || dashboard.filters.length === 0) {
            container.innerHTML = '<p style="color: #888; font-size: 0.9em; padding: 10px;">No filters available</p>';
            container.style.display = 'none';
            return;
        }

        // Initialize filter state for this dashboard
        if (!dashboardFilters[dashboardId]) {
            dashboardFilters[dashboardId] = {};
        }
        if (!dashboardFilterExpressions[dashboardId]) {
            dashboardFilterExpressions[dashboardId] = {};
        }

        // Store filter expressions from dashboard config
        dashboard.filters.forEach(filter => {
            if (filter.expression) {
                dashboardFilterExpressions[dashboardId][filter.field] = filter.expression;
            }
        });

        // Determine if we're in fullscreen mode
        const isFullscreen = container.id.includes('fullscreen');
        const controlsId = isFullscreen ? `filter-controls-fullscreen-${dashboardId}` : `filter-controls-${dashboardId}`;
        const inputPrefix = isFullscreen ? 'filter-fullscreen' : 'filter';

        container.innerHTML = `<div style="background: #f9fafb; padding: 15px; border-radius: 8px; margin-bottom: 15px;"><h4 style="margin: 0 0 10px 0; font-size: 0.9em; color: #666;">🔍 Filters</h4><div id="${controlsId}" style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center;"></div></div>`;

        const filtersControls = document.getElementById(controlsId);

        // Create filter dropdowns
        for (const filter of dashboard.filters) {
            // Get model from filter config, fallback to first chart's model
            const model = filter.model || (getDashboardCharts(dashboard) && getDashboardCharts(dashboard).length > 0 ? getDashboardCharts(dashboard)[0].model : null);

            if (!model) {
                console.warn(`No model found for filter ${filter.field}`);
                continue;
            }
            const filterWrapper = document.createElement('div');
            filterWrapper.style.cssText = 'display: flex; flex-direction: column; min-width: 150px;';

            const label = document.createElement('label');
            label.textContent = filter.label;
            label.style.cssText = 'font-size: 0.85em; color: #666; margin-bottom: 4px; font-weight: 500;';

            const select = document.createElement('select');
            select.id = `${inputPrefix}-${dashboardId}-${filter.field}`;
            select.style.cssText = 'padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.9em; cursor: pointer;';

            // Add default "All" option
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.textContent = `All ${filter.label}`;
            select.appendChild(defaultOption);

            // Store expression in data attribute for later use
            if (filter.expression) {
                select.dataset.expression = filter.expression;
            }

            // Fetch distinct values for this filter
            try {
                const valuesResponse = await fetch('/api/filter/values', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        table: model,
                        field: filter.field,
                        expression: filter.expression || null,
                        schema: 'public'
                    })
                });

                if (valuesResponse.ok) {
                    const valuesData = await valuesResponse.json();
                    const values = valuesData.values || [];

                    values.forEach(value => {
                        const option = document.createElement('option');
                        option.value = value;
                        option.textContent = value;
                        select.appendChild(option);
                    });
                } else {
                    console.error(`Failed to fetch filter values: ${valuesResponse.status}`);
                }
            } catch (error) {
                console.error(`Error fetching filter values for ${filter.field}:`, error);
            }

            // Handle filter changes
            select.onchange = async () => {
                if (select.value) {
                    dashboardFilters[dashboardId][filter.field] = select.value;
                } else {
                    delete dashboardFilters[dashboardId][filter.field];
                }
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
                // Convert objects to JSON strings for display
                option.textContent = typeof value === 'object' && value !== null ? JSON.stringify(value) : value;
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

    // Reset all inputs - check both regular and fullscreen mode
    let filtersControls = document.getElementById('filter-controls-fullscreen-' + dashboardId);
    if (!filtersControls) {
        filtersControls = document.getElementById('filter-controls-' + dashboardId);
    }

    if (filtersControls) {
        const selects = filtersControls.querySelectorAll('select');
        selects.forEach(select => select.selectedIndex = 0);
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
    dashboardClone.querySelector('.dashboard-details').style.display = 'block';
    dashboardClone.querySelector('.dashboard-details').style.textAlign = 'left';

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
        clone.querySelector('.dashboard-details').style.display = 'block';
        clone.querySelector('.dashboard-details').style.textAlign = 'left';

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

// =============================================================================
// SCHEDULE MANAGEMENT
// =============================================================================

async function loadSchedules() {
    try {
        const response = await fetch('/api/schedules');
        const data = await response.json();
        displaySchedules(data.schedules);
    } catch (error) {
        console.error('Error loading schedules:', error);
        const schedulesList = document.getElementById('schedules-list');
        if (schedulesList) {
            schedulesList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">❌</div>
                    <h3>Failed to Load Schedules</h3>
                    <p>There was an error loading the schedules. Please try refreshing.</p>
                </div>
            `;
        }
    }
}

function displaySchedules(schedules) {
    const schedulesList = document.getElementById('schedules-list');
    if (!schedulesList) return;

    if (schedules.length === 0) {
        schedulesList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⏰</div>
                <h3>No Schedules Yet</h3>
                <p>Create your first schedule to automate model execution.</p>
                <div class="empty-state-action">
                    <button class="btn btn-primary" onclick="showCreateScheduleModal()">
                        Create Schedule
                    </button>
                </div>
            </div>
        `;
        return;
    }

    schedulesList.innerHTML = schedules.map(schedule => {
        const isActive = schedule.is_active;
        const statusBadge = isActive
            ? '<span class="badge" style="background: #10b981; color: white;">Active</span>'
            : '<span class="badge" style="background: #6b7280; color: white;">Inactive</span>';

        const lastRunStatus = schedule.last_run_status
            ? `<span class="badge badge-${schedule.last_run_status === 'completed' ? 'success' : 'error'}">${schedule.last_run_status}</span>`
            : '<span style="color: #888;">Never run</span>';

        const nextRun = schedule.next_run_at
            ? new Date(schedule.next_run_at).toLocaleString()
            : 'Not scheduled';

        const lastRun = schedule.last_run_at
            ? new Date(schedule.last_run_at).toLocaleString()
            : 'Never';

        return `
            <div class="model-card" style="margin-bottom: 1rem;">
                <div class="model-card-content">
                    <div class="model-info">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                <h4 class="model-name">${schedule.schedule_name}</h4>
                                ${statusBadge}
                            </div>
                            <div style="display: flex; gap: 0.5rem;">
                                <button class="btn btn-secondary" style="padding: 0.4rem 0.8rem; font-size: 0.875rem;" onclick="event.stopPropagation(); toggleScheduleStatus(${schedule.id}, ${isActive})">
                                    ${isActive ? '⏸ Pause' : '▶ Activate'}
                                </button>
                                <button class="btn btn-secondary" style="padding: 0.4rem 0.8rem; font-size: 0.875rem;" onclick="event.stopPropagation(); editSchedule(${schedule.id})">
                                    ✏️ Edit
                                </button>
                                <button class="btn btn-secondary" style="padding: 0.4rem 0.8rem; font-size: 0.875rem; background: #ef4444; color: white;" onclick="event.stopPropagation(); deleteSchedule(${schedule.id}, '${schedule.schedule_name}')">
                                    🗑️ Delete
                                </button>
                            </div>
                        </div>

                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 0.75rem;">
                            <div>
                                <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">Model</div>
                                <div style="color: #6b7280;">${schedule.model_name}</div>
                            </div>
                            <div>
                                <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">Schedule</div>
                                <div style="color: #6b7280; font-family: 'JetBrains Mono', monospace; font-size: 0.875rem;">${schedule.cron_expression}</div>
                            </div>
                            <div>
                                <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">Timezone</div>
                                <div style="color: #6b7280;">${schedule.timezone}</div>
                            </div>
                        </div>

                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 0.75rem;">
                            <div>
                                <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">Next Run</div>
                                <div style="color: ${isActive ? '#667eea' : '#888'}; font-weight: 500;">${nextRun}</div>
                            </div>
                            <div>
                                <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">Last Run</div>
                                <div style="color: #6b7280;">${lastRun}</div>
                            </div>
                            <div>
                                <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">Last Status</div>
                                <div>${lastRunStatus}</div>
                            </div>
                        </div>

                        ${schedule.description ? `
                            <div style="margin-top: 0.75rem; padding: 0.75rem; background: #f9fafb; border-radius: 6px;">
                                <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">Description</div>
                                <div style="color: #6b7280; font-size: 0.875rem;">${schedule.description}</div>
                            </div>
                        ` : ''}

                        <div style="margin-top: 0.75rem; font-size: 0.875rem; color: #888;">
                            <strong>Statistics:</strong>
                            ${schedule.total_runs || 0} total runs,
                            ${schedule.successful_runs || 0} successful,
                            ${schedule.failed_runs || 0} failed
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

async function showCreateScheduleModal() {
    document.getElementById('scheduleModalTitle').textContent = 'Create Schedule';
    document.getElementById('schedule-id').value = '';
    document.getElementById('schedule-name').value = '';
    document.getElementById('schedule-cron').value = '0 9 * * *';
    document.getElementById('schedule-timezone').value = 'UTC';
    document.getElementById('schedule-description').value = '';

    // Load available models as checkboxes
    try {
        const models = modelsData; // Use globally loaded models
        const modelsContainer = document.getElementById('schedule-models-container');
        modelsContainer.innerHTML = models.map(m => `
            <div style="margin-bottom: 0.5rem;">
                <label style="display: flex; align-items: center; cursor: pointer;">
                    <input type="checkbox" name="schedule-models" value="${m.name}"
                           style="margin-right: 0.5rem; cursor: pointer;">
                    <span>${m.name}</span>
                </label>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading models for schedule:', error);
    }

    document.getElementById('scheduleModal').style.display = 'block';
}

async function editSchedule(scheduleId) {
    try {
        const response = await fetch(`/api/schedules/${scheduleId}`);
        const data = await response.json();
        const schedule = data.schedule;

        document.getElementById('scheduleModalTitle').textContent = 'Edit Schedule';
        document.getElementById('schedule-id').value = schedule.id;
        document.getElementById('schedule-name').value = schedule.schedule_name;
        document.getElementById('schedule-cron').value = schedule.cron_expression;
        document.getElementById('schedule-timezone').value = schedule.timezone;
        document.getElementById('schedule-description').value = schedule.description || '';

        // Load models as checkboxes with selected models checked
        const models = modelsData;
        const modelsContainer = document.getElementById('schedule-models-container');
        const selectedModels = schedule.models || (schedule.model_name ? [schedule.model_name] : []);

        modelsContainer.innerHTML = models.map(m => {
            const isChecked = selectedModels.includes(m.name);
            return `
                <div style="margin-bottom: 0.5rem;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" name="schedule-models" value="${m.name}"
                               ${isChecked ? 'checked' : ''}
                               style="margin-right: 0.5rem; cursor: pointer;">
                        <span>${m.name}</span>
                    </label>
                </div>
            `;
        }).join('');

        document.getElementById('scheduleModal').style.display = 'block';
    } catch (error) {
        console.error('Error loading schedule for edit:', error);
        showToast('Failed to load schedule details', 'error');
    }
}

async function saveSchedule() {
    const scheduleId = document.getElementById('schedule-id').value;
    const scheduleName = document.getElementById('schedule-name').value;
    const cronExpression = document.getElementById('schedule-cron').value;
    const timezone = document.getElementById('schedule-timezone').value;
    const description = document.getElementById('schedule-description').value;

    // Get selected models from checkboxes
    const selectedModels = Array.from(document.querySelectorAll('input[name="schedule-models"]:checked'))
        .map(cb => cb.value);

    if (!scheduleName || selectedModels.length === 0 || !cronExpression) {
        showToast('Please fill in all required fields and select at least one model', 'error');
        return;
    }

    try {
        const url = scheduleId ? `/api/schedules/${scheduleId}` : '/api/schedules';
        const method = scheduleId ? 'PUT' : 'POST';

        const payload = scheduleId
            ? { schedule_name: scheduleName, cron_expression: cronExpression, timezone, description, model_names: selectedModels }
            : { schedule_name: scheduleName, model_names: selectedModels, cron_expression: cronExpression, timezone, description };

        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save schedule');
        }

        closeModal('scheduleModal');
        showToast(scheduleId ? 'Schedule updated successfully' : 'Schedule created successfully', 'success');
        await loadSchedules();

    } catch (error) {
        console.error('Error saving schedule:', error);
        showToast('Failed to save schedule: ' + error.message, 'error');
    }
}

async function toggleScheduleStatus(scheduleId, isActive) {
    try {
        const response = await fetch(`/api/schedules/${scheduleId}/toggle`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Failed to toggle schedule status');
        }

        const data = await response.json();
        showToast(data.message, 'success');
        await loadSchedules();

    } catch (error) {
        console.error('Error toggling schedule:', error);
        showToast('Failed to toggle schedule: ' + error.message, 'error');
    }
}

async function deleteSchedule(scheduleId, scheduleName) {
    if (!confirm(`Are you sure you want to delete the schedule "${scheduleName}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/schedules/${scheduleId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete schedule');
        }

        showToast('Schedule deleted successfully', 'success');
        await loadSchedules();

    } catch (error) {
        console.error('Error deleting schedule:', error);
        showToast('Failed to delete schedule: ' + error.message, 'error');
    }
}

// Load models on page load
loadModels();

// === Assets Management ===

let assetsData = [];
let filteredAssets = [];

async function loadAssets() {
    try {
        const response = await fetch('/api/assets');
        const data = await response.json();
        assetsData = data.assets || [];
        filteredAssets = [...assetsData];
        renderAssets();
    } catch (error) {
        console.error('Error loading assets:', error);
        document.getElementById('assets-list').innerHTML = '<div style="text-align: center; padding: 60px 20px; color: #f44;">Error loading assets</div>';
    }
}

function renderAssets() {
    const container = document.getElementById('assets-list');
    
    if (filteredAssets.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 60px 20px; color: #999;"><p>No assets found</p></div>';
        return;
    }
    
    const html = filteredAssets.map(asset => {
        const typeIcons = {
            csv: '📊', excel: '📗', sql: '🗄️', python: '🐍',
            json: '📋', yaml: '⚙️', markdown: '📝', image: '🖼️', pdf: '📄', other: '📁'
        };
        const icon = typeIcons[asset.asset_type] || '📁';
        const date = new Date(asset.created_at).toLocaleDateString();
        const size = asset.file_size ? (asset.file_size / 1024).toFixed(1) + ' KB' : '—';
        
        return '<div style="background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 12px;">' +
            '<div style="display: flex; justify-content: space-between; align-items: start;">' +
            '<div style="flex: 1;">' +
            '<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">' +
            '<span style="font-size: 24px;">' + icon + '</span>' +
            '<h3 style="margin: 0; font-size: 1rem; font-weight: 600;">' + asset.name + '</h3>' +
            '<span style="font-size: 0.75rem; padding: 2px 8px; background: #e0e7ff; color: #4338ca; border-radius: 12px;">' + asset.asset_type + '</span>' +
            '</div>' +
            (asset.description ? '<p style="margin: 8px 0; color: #6b7280; font-size: 0.875rem;">' + asset.description + '</p>' : '') +
            '<div style="display: flex; gap: 16px; margin-top: 8px; font-size: 0.75rem; color: #9ca3af;">' +
            '<span>📅 ' + date + '</span>' +
            '<span>💾 ' + size + '</span>' +
            (asset.tags && asset.tags.length > 0 ? '<span>🏷️ ' + asset.tags.join(', ') + '</span>' : '') +
            '</div>' +
            '</div>' +
            '<div style="display: flex; gap: 8px;">' +
            '<button onclick="downloadAsset(' + asset.id + ')" class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.875rem;">Download</button>' +
            '<button onclick="deleteAsset(' + asset.id + ')" class="btn" style="padding: 6px 12px; font-size: 0.875rem; color: #dc2626;">Delete</button>' +
            '</div>' +
            '</div>' +
            '</div>';
    }).join('');
    
    container.innerHTML = html;
}

function showUploadAssetModal() {
    document.getElementById('uploadAssetModal').style.display = 'block';
    document.getElementById('uploadAssetForm').reset();
}

async function uploadAsset(event) {
    event.preventDefault();
    
    const formData = new FormData();
    formData.append('file', document.getElementById('assetFile').files[0]);
    formData.append('name', document.getElementById('assetName').value);
    formData.append('description', document.getElementById('assetDescription').value);
    formData.append('asset_type', document.getElementById('assetType').value);
    formData.append('tags', document.getElementById('assetTags').value);
    formData.append('created_by', 'admin');
    
    try {
        const response = await fetch('/api/assets/upload', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            showToast('Asset uploaded successfully', 'success');
            closeModal('uploadAssetModal');
            loadAssets();
        } else {
            const error = await response.json();
            showToast('Upload failed: ' + error.detail, 'error');
        }
    } catch (error) {
        console.error('Error uploading asset:', error);
        showToast('Upload failed', 'error');
    }
}

function downloadAsset(assetId) {
    window.open('/api/assets/' + assetId + '/download', '_blank');
}

async function deleteAsset(assetId) {
    if (!confirm('Are you sure you want to delete this asset?')) return;
    
    try {
        const response = await fetch('/api/assets/' + assetId, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast('Asset deleted successfully', 'success');
            loadAssets();
        } else {
            showToast('Delete failed', 'error');
        }
    } catch (error) {
        console.error('Error deleting asset:', error);
        showToast('Delete failed', 'error');
    }
}

function searchAssets(query) {
    const term = query.toLowerCase().trim();
    if (!term) {
        filteredAssets = [...assetsData];
    } else {
        filteredAssets = assetsData.filter(function(asset) {
            return asset.name.toLowerCase().includes(term) ||
                (asset.description && asset.description.toLowerCase().includes(term)) ||
                asset.asset_type.toLowerCase().includes(term) ||
                (asset.tags && asset.tags.some(function(tag) { return tag.toLowerCase().includes(term); }));
        });
    }
    renderAssets();
}

function filterAssets() {
    const typeFilter = document.getElementById('assets-type-filter').value;
    if (!typeFilter) {
        filteredAssets = [...assetsData];
    } else {
        filteredAssets = assetsData.filter(function(asset) { return asset.asset_type === typeFilter; });
    }
    renderAssets();
}

// Scroll to a specific model in the models list
function scrollToModel(modelName) {
    // Find the model card
    const modelCards = document.querySelectorAll('.model-card');
    let targetCard = null;
    
    for (const card of modelCards) {
        const nameElement = card.querySelector('.model-name, .model-title, h3');
        if (nameElement && nameElement.textContent.trim() === modelName) {
            targetCard = card;
            break;
        }
    }
    
    if (targetCard) {
        // Scroll to the card
        targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // Highlight the card temporarily
        const originalBg = targetCard.style.background;
        targetCard.style.background = '#fef2f2';
        targetCard.style.border = '2px solid #dc2626';
        targetCard.style.transition = 'all 0.3s';

        setTimeout(() => {
            targetCard.style.background = originalBg;
            targetCard.style.border = '';
        }, 3000);
    } else {
        console.warn('Model not found:', modelName);
        showToast(`Model ${modelName} not found in current view`, 'error');
    }
}

// =============================================================================
// System Monitor Functions
// =============================================================================

async function loadSystemStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        if (data.status === 'healthy') {
            // Update status cards
            document.getElementById('server-status').textContent = '● HEALTHY';
            const uptimeMinutes = Math.floor(data.process.uptime_seconds / 60);
            const uptimeHours = Math.floor(uptimeMinutes / 60);
            const uptimeDays = Math.floor(uptimeHours / 24);
            let uptimeText = '';
            if (uptimeDays > 0) {
                uptimeText = `${uptimeDays}d ${uptimeHours % 24}h uptime`;
            } else if (uptimeHours > 0) {
                uptimeText = `${uptimeHours}h ${uptimeMinutes % 60}m uptime`;
            } else {
                uptimeText = `${uptimeMinutes}m uptime`;
            }
            document.getElementById('server-uptime').textContent = uptimeText;

            document.getElementById('memory-usage').textContent = data.process.memory_mb.toFixed(1);
            document.getElementById('cpu-usage').textContent = data.process.cpu_percent.toFixed(1) + '%';
            document.getElementById('active-jobs-count').textContent = data.scheduler.jobs_count;

            // Update process info
            document.getElementById('process-pid').textContent = data.process.pid;
            document.getElementById('process-threads').textContent = data.process.threads;

            // Database status
            const dbStatus = data.database.error ? '⚠️ Check Needed' : '✅ Connected';
            document.getElementById('db-status').textContent = dbStatus;

            // Scheduler status
            const schedulerStatus = data.scheduler.active ? '✅ Active' : '❌ Inactive';
            document.getElementById('scheduler-status').textContent = schedulerStatus;

            // Render jobs table
            renderJobsTable(data.scheduler.jobs);

        } else {
            document.getElementById('server-status').textContent = '❌ ERROR';
            document.getElementById('server-uptime').textContent = data.error || 'Unknown error';
        }
    } catch (error) {
        console.error('Error loading system status:', error);
        document.getElementById('server-status').textContent = '❌ OFFLINE';
        document.getElementById('server-uptime').textContent = 'Cannot connect to server';
        showToast('Failed to load system status', 'error');
    }
}

function renderJobsTable(jobs) {
    const container = document.getElementById('jobs-table-container');

    if (!jobs || jobs.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #9ca3af;">
                <div style="font-size: 3rem; margin-bottom: 16px;">📭</div>
                <div style="font-size: 1.125rem; margin-bottom: 8px;">No scheduled jobs</div>
                <div style="font-size: 0.875rem;">Create a schedule in the Schedules tab</div>
            </div>
        `;
        return;
    }

    const table = document.createElement('table');
    table.style.cssText = 'width: 100%; border-collapse: separate; border-spacing: 0;';
    table.innerHTML = `
        <thead>
            <tr style="background: #f9fafb; border-bottom: 2px solid #e5e7eb;">
                <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Job ID</th>
                <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Name</th>
                <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Schedule</th>
                <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151;">Next Run</th>
                <th style="padding: 12px; text-align: center; font-weight: 600; color: #374151;">Actions</th>
            </tr>
        </thead>
        <tbody></tbody>
    `;

    const tbody = table.querySelector('tbody');

    jobs.forEach((job, index) => {
        const row = document.createElement('tr');
        row.style.cssText = 'border-bottom: 1px solid #e5e7eb; transition: background 0.2s;';
        row.onmouseover = () => row.style.background = '#f9fafb';
        row.onmouseout = () => row.style.background = 'transparent';

        // Format next run time
        let nextRunDisplay = 'Not scheduled';
        if (job.next_run_time) {
            const nextRun = new Date(job.next_run_time);
            const now = new Date();
            const diffMs = nextRun - now;
            const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

            if (diffHours > 24) {
                const diffDays = Math.floor(diffHours / 24);
                nextRunDisplay = `in ${diffDays}d ${diffHours % 24}h`;
            } else if (diffHours > 0) {
                nextRunDisplay = `in ${diffHours}h ${diffMinutes}m`;
            } else if (diffMinutes > 0) {
                nextRunDisplay = `in ${diffMinutes}m`;
            } else {
                nextRunDisplay = 'Soon';
            }
            nextRunDisplay += `<br><span style="font-size: 0.75rem; color: #9ca3af;">${nextRun.toLocaleString()}</span>`;
        }

        row.innerHTML = `
            <td style="padding: 12px; font-family: monospace; font-size: 0.875rem; color: #6b7280;">${job.id}</td>
            <td style="padding: 12px; color: #111827;">${job.name}</td>
            <td style="padding: 12px; font-family: monospace; font-size: 0.875rem; color: #6b7280;">${job.trigger}</td>
            <td style="padding: 12px;">${nextRunDisplay}</td>
            <td style="padding: 12px; text-align: center;">
                <button onclick="pauseJob('${job.id}')" class="btn-small" style="background: #fbbf24; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; margin-right: 4px; font-size: 0.875rem;" title="Pause job">
                    ⏸
                </button>
                <button onclick="resumeJob('${job.id}')" class="btn-small" style="background: #10b981; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.875rem;" title="Resume job">
                    ▶️
                </button>
            </td>
        `;

        tbody.appendChild(row);
    });

    container.innerHTML = '';
    container.appendChild(table);
}

async function pauseJob(jobId) {
    if (!confirm(`Pause job ${jobId}?`)) return;

    try {
        const response = await fetch(`/api/jobs/${jobId}/pause`, { method: 'POST' });
        const data = await response.json();

        if (response.ok) {
            showToast(`Job ${jobId} paused`, 'success');
            loadSystemStatus();
        } else {
            showToast(`Failed to pause job: ${data.detail || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Error pausing job:', error);
        showToast('Failed to pause job', 'error');
    }
}

async function resumeJob(jobId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/resume`, { method: 'POST' });
        const data = await response.json();

        if (response.ok) {
            showToast(`Job ${jobId} resumed`, 'success');
            loadSystemStatus();
        } else {
            showToast(`Failed to resume job: ${data.detail || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Error resuming job:', error);
        showToast('Failed to resume job', 'error');
    }
}

// =============================================================================
// Authentication Functions
// =============================================================================

async function logout() {
    if (!confirm('Are you sure you want to log out?')) {
        return;
    }

    try {
        await fetch('/api/auth/logout', {
            method: 'POST'
        });

        // Redirect to login page
        window.location.href = '/login';
    } catch (error) {
        console.error('Logout error:', error);
        showToast('Failed to logout', 'error');
    }
}

// Navigate to Models view and scroll to specific model
function goToModelView(modelName) {
    // Close the modal
    closeModal('codeModal');
    
    // Switch to models view
    switchView('models');
    
    // Wait for view to load, then scroll to the model card
    setTimeout(() => {
        const modelCard = document.getElementById(`model-card-${modelName}`);
        if (modelCard) {
            modelCard.scrollIntoView({ behavior: 'smooth', block: 'center' });

            // Highlight the model card briefly
            modelCard.style.transition = 'all 0.3s';
            modelCard.style.boxShadow = '0 0 0 3px #667eea';
            modelCard.style.transform = 'scale(1.02)';

            setTimeout(() => {
                modelCard.style.boxShadow = '';
                modelCard.style.transform = '';
            }, 2000);
        }
    }, 300);
}

// =============================================================================
// CHART EXPORT FUNCTIONS
// =============================================================================

function showChartExportMenu(event, chart) {
    // Remove any existing export menus
    const existingMenu = document.querySelector('.chart-export-menu');
    if (existingMenu) {
        existingMenu.remove();
    }

    // Create export menu
    const menu = document.createElement('div');
    menu.className = 'chart-export-menu';
    menu.style.cssText = `
        position: fixed;
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 8px 0;
        z-index: 10000;
        min-width: 150px;
    `;

    menu.innerHTML = `
        <div class="export-menu-item" data-format="csv" style="padding: 8px 16px; cursor: pointer; transition: background 0.2s;">
            📊 Export as CSV
        </div>
        <div class="export-menu-item" data-format="excel" style="padding: 8px 16px; cursor: pointer; transition: background 0.2s;">
            📈 Export as Excel
        </div>
        <div class="export-menu-item" data-format="image" style="padding: 8px 16px; cursor: pointer; transition: background 0.2s;">
            🖼️ Export as Image
        </div>
        <div class="export-menu-item" data-format="pdf" style="padding: 8px 16px; cursor: pointer; transition: background 0.2s;">
            📄 Export as PDF
        </div>
    `;

    // Position menu near the button
    const rect = event.target.getBoundingClientRect();
    menu.style.left = `${rect.left}px`;
    menu.style.top = `${rect.bottom + 5}px`;

    // Add hover effect
    menu.querySelectorAll('.export-menu-item').forEach(item => {
        item.addEventListener('mouseenter', () => {
            item.style.background = '#f3f4f6';
        });
        item.addEventListener('mouseleave', () => {
            item.style.background = 'transparent';
        });
        item.addEventListener('click', () => {
            const format = item.getAttribute('data-format');
            exportChart(chart, format);
            menu.remove();
        });
    });

    document.body.appendChild(menu);

    // Close menu when clicking outside
    setTimeout(() => {
        document.addEventListener('click', function closeMenu(e) {
            if (!menu.contains(e.target) && e.target !== event.target) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        });
    }, 100);
}

async function exportChart(chart, format) {
    try {
        if (format === 'image') {
            await exportChartAsImage(chart);
        } else if (format === 'pdf') {
            await exportChartAsPDF(chart);
        } else {
            await exportChartAsData(chart, format);
        }
    } catch (error) {
        console.error('Export error:', error);
        showToast(`Failed to export chart: ${error.message}`, 'error');
    }
}

async function exportChartAsData(chart, format) {
    try {
        const response = await fetch(`/api/charts/${chart.id}/export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                format: format,
                filters: {}
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Export failed');
        }

        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${chart.id}_data.${format === 'excel' ? 'xlsx' : 'csv'}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showToast(`Chart exported as ${format.toUpperCase()} successfully!`, 'success');
    } catch (error) {
        console.error('Error exporting chart data:', error);
        throw error;
    }
}

async function exportChartAsImage(chart) {
    try {
        // Find the chart canvas
        const canvasElement = document.querySelector(`canvas[id*="${chart.id}"]`);
        if (!canvasElement) {
            throw new Error('Chart canvas not found');
        }

        // Convert canvas to blob
        canvasElement.toBlob((blob) => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${chart.title || chart.id}.png`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            showToast('Chart exported as PNG successfully!', 'success');
        });
    } catch (error) {
        console.error('Error exporting chart as image:', error);
        throw error;
    }
}

async function exportChartAsPDF(chart) {
    try {
        // Find the chart canvas
        const canvasElement = document.querySelector(`canvas[id*="${chart.id}"]`);
        if (!canvasElement) {
            throw new Error('Chart canvas not found');
        }

        // Create a temporary container for printing
        const printWindow = window.open('', '', 'width=800,height=600');
        printWindow.document.write(`
            <html>
                <head>
                    <title>${chart.title || 'Chart'}</title>
                    <style>
                        body { margin: 0; padding: 20px; }
                        h1 { text-align: center; }
                        img { max-width: 100%; height: auto; }
                    </style>
                </head>
                <body>
                    <h1>${chart.title || 'Chart'}</h1>
                    <img src="${canvasElement.toDataURL()}" />
                </body>
            </html>
        `);
        printWindow.document.close();

        printWindow.onload = () => {
            printWindow.print();
            printWindow.close();
        };

        showToast('Opening print dialog for PDF export...', 'success');
    } catch (error) {
        console.error('Error exporting chart as PDF:', error);
        throw error;
    }
}

// ============================================================================
// ML MODELS FUNCTIONS
// ============================================================================

async function loadMLModels() {
    try {
        const response = await fetch('/api/ml/models');
        const data = await response.json();

        const modelsGrid = document.getElementById('ml-models-grid');

        if (!data.models || data.models.length === 0) {
            modelsGrid.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🤖</div>
                    <h3 style="color: #374151; margin-bottom: 0.5rem;">No ML Models Yet</h3>
                    <p style="color: #6b7280; margin-bottom: 1.5rem;">Train your first machine learning model to get started</p>
                    <button onclick="openMLTrainingDialog()" class="btn btn-primary">
                        Train Your First Model
                    </button>
                </div>
            `;
            return;
        }

        modelsGrid.innerHTML = '';

        data.models.forEach(model => {
            const card = document.createElement('div');
            card.className = 'model-card';
            card.style.cssText = `
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 20px;
                cursor: pointer;
                transition: all 0.2s;
            `;

            card.onmouseover = () => card.style.borderColor = '#3b82f6';
            card.onmouseout = () => card.style.borderColor = '#e5e7eb';

            const typeColor = {
                'classification': '#10b981',
                'regression': '#3b82f6',
                'clustering': '#8b5cf6',
                'other': '#6b7280'
            }[model.model_type] || '#6b7280';

            const metricsHTML = Object.keys(model.metrics || {}).length > 0
                ? Object.entries(model.metrics).slice(0, 3).map(([key, value]) =>
                    `<div style="display: flex; justify-content: space-between; padding: 4px 0;">
                        <span style="color: #6b7280; font-size: 0.875rem;">${key}:</span>
                        <span style="font-weight: 600; font-size: 0.875rem;">${typeof value === 'number' ? value.toFixed(4) : value}</span>
                    </div>`
                  ).join('')
                : '<div style="color: #9ca3af; font-size: 0.875rem; font-style: italic;">No metrics available</div>';

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                    <div>
                        <h3 style="margin: 0 0 4px 0; font-size: 1.125rem; color: #111827;">${model.model_name}</h3>
                        <span style="display: inline-block; padding: 2px 8px; background: ${typeColor}20; color: ${typeColor}; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">
                            ${model.model_type.toUpperCase()}
                        </span>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button onclick="event.stopPropagation(); openPredictionDialog('${model.model_name}')" class="icon-btn-small" title="Make Prediction">
                            <span title="Make Prediction">🎯</span>
                        </button>
                        <button onclick="event.stopPropagation(); viewModelVersions('${model.model_name}')" class="icon-btn-small" title="View Versions">
                            <span title="View Versions">🔢</span>
                        </button>
                        <button onclick="event.stopPropagation(); deleteMLModel('${model.model_name}')" class="icon-btn-small" title="Delete Model" style="color: #dc2626;">
                            <span title="Delete Model">🗑️</span>
                        </button>
                    </div>
                </div>

                <p style="color: #6b7280; font-size: 0.875rem; margin-bottom: 12px; line-height: 1.5;">
                    ${model.description || 'No description available'}
                </p>

                <div style="margin-bottom: 12px; padding: 12px; background: #f9fafb; border-radius: 6px;">
                    <div style="font-size: 0.75rem; font-weight: 600; color: #6b7280; margin-bottom: 8px;">METRICS</div>
                    ${metricsHTML}
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 12px; border-top: 1px solid #e5e7eb; font-size: 0.875rem; color: #6b7280;">
                    <div>
                        <span style="font-weight: 600;">${model.feature_columns?.length || 0}</span> features
                    </div>
                    <div>
                        v${model.latest_version} • ${model.total_versions} version(s)
                    </div>
                </div>
            `;

            card.onclick = () => viewModelDetails(model.model_name);

            modelsGrid.appendChild(card);
        });

    } catch (error) {
        console.error('Error loading ML models:', error);
        document.getElementById('ml-models-grid').innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #ef4444;">
                <h3>Error Loading Models</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

async function viewModelDetails(modelName) {
    try {
        const response = await fetch(`/api/ml/models/${modelName}`);
        const model = await response.json();

        const featuresHTML = model.features?.feature_columns?.length > 0
            ? model.features.feature_columns.map(feat => `<li style="padding: 4px 0;">${feat}</li>`).join('')
            : '<li style="color: #9ca3af;">No features defined</li>';

        const metricsHTML = Object.keys(model.metrics || {}).length > 0
            ? Object.entries(model.metrics).map(([key, value]) =>
                `<tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">${key}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; font-weight: 600;">${typeof value === 'number' ? value.toFixed(4) : value}</td>
                </tr>`
              ).join('')
            : '<tr><td colspan="2" style="padding: 8px; color: #9ca3af; text-align: center;">No metrics available</td></tr>';

        const tagsHTML = model.tags?.length > 0
            ? model.tags.map(tag => `<span style="display: inline-block; padding: 4px 12px; background: #e5e7eb; border-radius: 12px; font-size: 0.875rem; margin-right: 8px;">${tag}</span>`).join('')
            : '<span style="color: #9ca3af;">No tags</span>';

        // Hyperparameters HTML
        const hyperparamsHTML = Object.keys(model.hyperparameters || {}).length > 0
            ? Object.entries(model.hyperparameters).map(([key, value]) => {
                const displayValue = typeof value === 'object' ? JSON.stringify(value) : value;
                return `<tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; font-family: monospace; color: #6b7280;">${key}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; font-weight: 600; font-family: monospace;">${displayValue}</td>
                </tr>`;
              }).join('')
            : '<tr><td colspan="2" style="padding: 8px; color: #9ca3af; text-align: center;">No hyperparameters recorded</td></tr>';

        // Training Config HTML
        const trainingConfigHTML = Object.keys(model.training_config || {}).length > 0
            ? Object.entries(model.training_config).map(([key, value]) => {
                let displayValue = value;
                if (typeof value === 'number') {
                    displayValue = value % 1 === 0 ? value : value.toFixed(4);
                } else if (typeof value === 'boolean') {
                    displayValue = value ? 'Yes' : 'No';
                }
                return `<tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; color: #6b7280;">${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; font-weight: 600;">${displayValue}</td>
                </tr>`;
              }).join('')
            : '<tr><td colspan="2" style="padding: 8px; color: #9ca3af; text-align: center;">No training configuration recorded</td></tr>';

        const modalHTML = `
            <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;" onclick="this.remove()">
                <div style="background: white; border-radius: 12px; padding: 32px; max-width: 800px; width: 90%; max-height: 85vh; overflow-y: auto;" onclick="event.stopPropagation()">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 24px;">
                        <div>
                            <h2 style="margin: 0 0 8px 0; font-size: 1.5rem;">${model.model_name}</h2>
                            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                <span style="display: inline-block; padding: 4px 12px; background: #3b82f620; color: #3b82f6; border-radius: 4px; font-size: 0.875rem; font-weight: 600;">
                                    ${model.model_type.toUpperCase()}
                                </span>
                                ${model.model_class ? `<span style="display: inline-block; padding: 4px 12px; background: #f3f4f6; color: #374151; border-radius: 4px; font-size: 0.875rem; font-family: monospace;">
                                    ${model.model_class}
                                </span>` : ''}
                                ${model.model_size_mb ? `<span style="display: inline-block; padding: 4px 12px; background: #fef3c7; color: #92400e; border-radius: 4px; font-size: 0.875rem;">
                                    ${model.model_size_mb} MB
                                </span>` : ''}
                            </div>
                        </div>
                        <button onclick="this.closest('div[style*=fixed]').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #6b7280; padding: 0; width: 32px; height: 32px;">×</button>
                    </div>

                    <!-- Tabs -->
                    <div style="border-bottom: 2px solid #e5e7eb; margin-bottom: 20px;">
                        <div style="display: flex; gap: 8px;">
                            <button class="model-tab-btn" data-tab="overview" onclick="switchModelTab(this, 'overview')" style="padding: 12px 20px; border: none; background: none; font-weight: 600; color: #3b82f6; border-bottom: 2px solid #3b82f6; margin-bottom: -2px; cursor: pointer;">
                                Overview
                            </button>
                            <button class="model-tab-btn" data-tab="hyperparams" onclick="switchModelTab(this, 'hyperparams')" style="padding: 12px 20px; border: none; background: none; font-weight: 600; color: #6b7280; cursor: pointer;">
                                Hyperparameters
                            </button>
                            <button class="model-tab-btn" data-tab="training" onclick="switchModelTab(this, 'training')" style="padding: 12px 20px; border: none; background: none; font-weight: 600; color: #6b7280; cursor: pointer;">
                                Training Config
                            </button>
                        </div>
                    </div>

                    <!-- Overview Tab -->
                    <div id="tab-overview" class="model-tab-content" style="display: block;">
                        <div style="margin-bottom: 20px;">
                            <h3 style="font-size: 0.875rem; font-weight: 600; color: #6b7280; margin-bottom: 8px;">DESCRIPTION</h3>
                            <p style="color: #374151; line-height: 1.6;">${model.description}</p>
                        </div>

                        <div style="margin-bottom: 20px;">
                            <h3 style="font-size: 0.875rem; font-weight: 600; color: #6b7280; margin-bottom: 8px;">TAGS</h3>
                            <div>${tagsHTML}</div>
                        </div>

                        <div style="margin-bottom: 20px;">
                            <h3 style="font-size: 0.875rem; font-weight: 600; color: #6b7280; margin-bottom: 8px;">METRICS</h3>
                            <table style="width: 100%; border-collapse: collapse;">
                                ${metricsHTML}
                            </table>
                        </div>

                        <div style="margin-bottom: 20px;">
                            <h3 style="font-size: 0.875rem; font-weight: 600; color: #6b7280; margin-bottom: 8px;">FEATURES (${model.features?.num_features || 0})</h3>
                            <ul style="max-height: 200px; overflow-y: auto; padding-left: 20px; margin: 0; color: #374151;">
                                ${featuresHTML}
                            </ul>
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 16px; background: #f9fafb; border-radius: 8px;">
                            <div>
                                <div style="font-size: 0.75rem; color: #6b7280; margin-bottom: 4px;">VERSION</div>
                                <div style="font-weight: 600; color: #111827;">v${model.version}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.75rem; color: #6b7280; margin-bottom: 4px;">STATUS</div>
                                <div style="font-weight: 600; color: #10b981;">${model.status.toUpperCase()}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.75rem; color: #6b7280; margin-bottom: 4px;">TARGET</div>
                                <div style="font-weight: 600; color: #111827;">${model.features?.target_column || 'N/A'}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.75rem; color: #6b7280; margin-bottom: 4px;">REGISTERED</div>
                                <div style="font-weight: 600; color: #111827;">${new Date(model.registered_at).toLocaleDateString()}</div>
                            </div>
                        </div>
                    </div>

                    <!-- Hyperparameters Tab -->
                    <div id="tab-hyperparams" class="model-tab-content" style="display: none;">
                        <div style="padding: 16px; background: #eff6ff; border-left: 4px solid #3b82f6; margin-bottom: 16px;">
                            <div style="font-weight: 600; color: #1e40af; margin-bottom: 4px;">Model Architecture</div>
                            <div style="color: #1e40af; font-size: 0.875rem;">
                                ${model.model_class || 'Not specified'} with ${Object.keys(model.hyperparameters || {}).length} hyperparameters
                            </div>
                        </div>
                        <table style="width: 100%; border-collapse: collapse;">
                            ${hyperparamsHTML}
                        </table>
                    </div>

                    <!-- Training Config Tab -->
                    <div id="tab-training" class="model-tab-content" style="display: none;">
                        <div style="padding: 16px; background: #f0fdf4; border-left: 4px solid #10b981; margin-bottom: 16px;">
                            <div style="font-weight: 600; color: #065f46; margin-bottom: 4px;">Training Configuration</div>
                            <div style="color: #065f46; font-size: 0.875rem;">
                                Details about how this model was trained
                            </div>
                        </div>
                        <table style="width: 100%; border-collapse: collapse;">
                            ${trainingConfigHTML}
                        </table>
                    </div>

                    <div style="display: flex; gap: 12px; margin-top: 24px;">
                        <button onclick="openPredictionDialog('${model.model_name}')" class="btn btn-primary" style="flex: 1;">
                            Make Prediction
                        </button>
                        <button onclick="viewModelVersions('${model.model_name}')" class="btn btn-secondary" style="flex: 1;">
                            View All Versions
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);

    } catch (error) {
        console.error('Error loading model details:', error);
        showToast( 'Failed to load model details');
    }
}

function switchModelTab(button, tabName) {
    // Hide all tabs
    document.querySelectorAll('.model-tab-content').forEach(tab => {
        tab.style.display = 'none';
    });

    // Remove active styling from all buttons
    document.querySelectorAll('.model-tab-btn').forEach(btn => {
        btn.style.color = '#6b7280';
        btn.style.borderBottom = 'none';
        btn.style.marginBottom = '0';
    });

    // Show selected tab
    document.getElementById(`tab-${tabName}`).style.display = 'block';

    // Add active styling to clicked button
    button.style.color = '#3b82f6';
    button.style.borderBottom = '2px solid #3b82f6';
    button.style.marginBottom = '-2px';
}

async function viewModelVersions(modelName) {
    try {
        const response = await fetch(`/api/ml/models/${modelName}/versions`);
        const data = await response.json();

        const versionsHTML = data.versions.map(version => `
            <div style="padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                    <div>
                        <h4 style="margin: 0 0 4px 0;">Version ${version.version}</h4>
                        <span style="display: inline-block; padding: 2px 8px; background: ${version.status === 'active' ? '#10b98120' : '#6b728020'}; color: ${version.status === 'active' ? '#10b981' : '#6b7280'}; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">
                            ${version.status.toUpperCase()}
                        </span>
                    </div>
                    <div style="font-size: 0.875rem; color: #6b7280;">
                        ${new Date(version.registered_at).toLocaleDateString()}
                    </div>
                </div>
                <p style="color: #6b7280; font-size: 0.875rem; margin: 8px 0;">
                    ${version.description || 'No description'}
                </p>
                <div style="font-size: 0.875rem; color: #6b7280;">
                    <strong>${Object.keys(version.metrics || {}).length}</strong> metrics •
                    <strong>${version.feature_columns?.length || 0}</strong> features
                </div>
            </div>
        `).join('');

        const modalHTML = `
            <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;" onclick="this.remove()">
                <div style="background: white; border-radius: 12px; padding: 32px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto;" onclick="event.stopPropagation()">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                        <h2 style="margin: 0;">Versions: ${modelName}</h2>
                        <button onclick="this.closest('div[style*=fixed]').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #6b7280; padding: 0;">×</button>
                    </div>

                    <div style="margin-bottom: 16px; padding: 12px; background: #f9fafb; border-radius: 6px;">
                        <strong>${data.versions.length}</strong> version(s) registered
                    </div>

                    ${versionsHTML}
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);

    } catch (error) {
        console.error('Error loading model versions:', error);
        showToast( 'Failed to load model versions');
    }
}

function openMLTrainingDialog() {
    const modalHTML = `
        <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;" onclick="this.remove()">
            <div style="background: white; border-radius: 12px; padding: 32px; max-width: 500px; width: 90%;" onclick="event.stopPropagation()">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                    <h2 style="margin: 0;">Train ML Model</h2>
                    <button onclick="this.closest('div[style*=fixed]').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #6b7280; padding: 0;">×</button>
                </div>

                <div style="padding: 20px; background: #fef3c7; border: 1px solid #fbbf24; border-radius: 8px; margin-bottom: 20px;">
                    <div style="font-weight: 600; color: #92400e; margin-bottom: 8px;">Training via Python Script</div>
                    <p style="margin: 0; color: #92400e; font-size: 0.875rem; line-height: 1.5;">
                        ML models are currently trained via Python scripts. Use the command line to train models:
                    </p>
                </div>

                <div style="margin-bottom: 20px;">
                    <h3 style="font-size: 0.875rem; font-weight: 600; color: #6b7280; margin-bottom: 12px;">AVAILABLE TRAINING SCRIPTS</h3>

                    <div style="margin-bottom: 16px; padding: 16px; background: #f9fafb; border-radius: 6px;">
                        <div style="font-weight: 600; margin-bottom: 8px;">Customer Segmentation</div>
                        <code style="display: block; padding: 12px; background: #1f2937; color: #10b981; border-radius: 4px; font-size: 0.875rem; margin-bottom: 8px; overflow-x: auto;">
                            python ml/train_customer_segmentation.py
                        </code>
                        <div style="font-size: 0.875rem; color: #6b7280;">
                            Creates customer segments using KMeans clustering on RFM metrics
                        </div>
                    </div>

                    <div style="padding: 16px; background: #f9fafb; border-radius: 6px;">
                        <div style="font-weight: 600; margin-bottom: 8px;">Custom Model Training</div>
                        <code style="display: block; padding: 12px; background: #1f2937; color: #10b981; border-radius: 4px; font-size: 0.875rem; margin-bottom: 8px; overflow-x: auto;">
                            python ml/examples/train_example_model.py
                        </code>
                        <div style="font-size: 0.875rem; color: #6b7280;">
                            Example template for training custom models
                        </div>
                    </div>
                </div>

                <div style="padding: 16px; background: #eff6ff; border: 1px solid #3b82f6; border-radius: 8px; margin-bottom: 20px;">
                    <div style="font-weight: 600; color: #1e40af; margin-bottom: 4px;">Tip</div>
                    <div style="color: #1e40af; font-size: 0.875rem;">
                        After training, refresh this page to see your new models
                    </div>
                </div>

                <button onclick="this.closest('div[style*=fixed]').remove()" class="btn btn-secondary" style="width: 100%;">
                    Close
                </button>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function openPredictionDialog(modelName) {
    showToast('Prediction UI coming soon! Use POST /api/ml/predict endpoint for now.', 'info');
}

async function deleteMLModel(modelName) {
    if (!confirm(`Are you sure you want to delete the model "${modelName}"? This will remove all versions. This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/ml/models/${modelName}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            showToast(`Model "${modelName}" deleted successfully!`, 'success');
            // Reload the models list
            await loadMLModels();
        } else {
            const error = await response.json();
            showToast(error.detail || 'Failed to delete model', 'error');
        }
    } catch (error) {
        console.error('Error deleting model:', error);
        showToast('An error occurred while deleting the model', 'error');
    }
}
