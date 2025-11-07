// ============================================================================
// Datasets Management JavaScript
// ============================================================================

let currentDatasetSourceType = 'table'; // 'table' or 'sql'

// Open the dataset builder modal
function openDatasetBuilder() {
    // Reset form
    document.getElementById('datasetName').value = '';
    document.getElementById('datasetDescription').value = '';
    document.getElementById('datasetSchema').value = 'public';
    document.getElementById('datasetTableName').value = '';
    document.getElementById('datasetSQLQuery').value = '';
    document.getElementById('datasetPreview').style.display = 'none';

    // Reset to table mode
    switchDatasetSourceType('table');

    // Show modal
    document.getElementById('datasetBuilderModal').style.display = 'block';
}

// Switch between table and SQL source types
function switchDatasetSourceType(type) {
    currentDatasetSourceType = type;

    // Update button styles
    const tableBtn = document.getElementById('sourceTypeTable');
    const sqlBtn = document.getElementById('sourceTypeSQL');

    if (type === 'table') {
        tableBtn.style.background = '#667eea';
        tableBtn.style.color = 'white';
        sqlBtn.style.background = '';
        sqlBtn.style.color = '';

        document.getElementById('tableModeConfig').style.display = 'block';
        document.getElementById('sqlModeConfig').style.display = 'none';
    } else {
        sqlBtn.style.background = '#667eea';
        sqlBtn.style.color = 'white';
        tableBtn.style.background = '';
        tableBtn.style.color = '';

        document.getElementById('tableModeConfig').style.display = 'none';
        document.getElementById('sqlModeConfig').style.display = 'block';
    }
}

// Preview dataset data
async function previewDataset() {
    try {
        const previewPayload = {
            source_type: currentDatasetSourceType,
            limit: 10
        };

        if (currentDatasetSourceType === 'table') {
            const tableName = document.getElementById('datasetTableName').value.trim();
            const schema = document.getElementById('datasetSchema').value.trim() || 'public';

            if (!tableName) {
                alert('Please enter a table name');
                return;
            }

            previewPayload.table_name = tableName;
            previewPayload.schema_name = schema;
        } else {
            const sqlQuery = document.getElementById('datasetSQLQuery').value.trim();

            if (!sqlQuery) {
                alert('Please enter a SQL query');
                return;
            }

            previewPayload.sql_query = sqlQuery;
        }

        const response = await fetch('/api/datasets/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(previewPayload)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to preview dataset');
        }

        // Show preview
        const previewDiv = document.getElementById('datasetPreview');
        const contentDiv = document.getElementById('datasetPreviewContent');

        if (data.data && data.data.length > 0) {
            let tableHTML = '<table style="width: 100%; border-collapse: collapse; font-size: 0.75rem;"><thead><tr>';

            // Headers
            data.columns.forEach(col => {
                tableHTML += `<th style="padding: 8px; text-align: left; border-bottom: 2px solid #e5e7eb; font-weight: 600; background: white; position: sticky; top: 0;">${col}</th>`;
            });
            tableHTML += '</tr></thead><tbody>';

            // Rows
            data.data.forEach(row => {
                tableHTML += '<tr style="border-bottom: 1px solid #f3f4f6;">';
                data.columns.forEach(col => {
                    const val = row[col];
                    tableHTML += `<td style="padding: 8px;">${val !== null && val !== undefined ? val : ''}</td>`;
                });
                tableHTML += '</tr>';
            });

            tableHTML += '</tbody></table>';
            contentDiv.innerHTML = tableHTML;
        } else {
            contentDiv.innerHTML = '<p style="color: #6b7280; text-align: center;">No data found</p>';
        }

        previewDiv.style.display = 'block';

    } catch (error) {
        console.error('Error previewing dataset:', error);
        alert('Error previewing dataset: ' + error.message);
    }
}

// Save dataset
async function saveDataset() {
    try {
        const name = document.getElementById('datasetName').value.trim();
        const description = document.getElementById('datasetDescription').value.trim();

        if (!name) {
            alert('Please enter a dataset name');
            return;
        }

        // Generate ID from name
        const datasetId = name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');

        const payload = {
            id: datasetId,
            name: name,
            description: description,
            source_type: currentDatasetSourceType
        };

        if (currentDatasetSourceType === 'table') {
            const tableName = document.getElementById('datasetTableName').value.trim();
            const schema = document.getElementById('datasetSchema').value.trim() || 'public';

            if (!tableName) {
                alert('Please enter a table name');
                return;
            }

            payload.table_name = tableName;
            payload.schema_name = schema;
        } else {
            const sqlQuery = document.getElementById('datasetSQLQuery').value.trim();

            if (!sqlQuery) {
                alert('Please enter a SQL query');
                return;
            }

            payload.sql_query = sqlQuery;
        }

        const response = await fetch('/api/datasets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to create dataset');
        }

        // Close modal
        closeModal('datasetBuilderModal');

        // Show success message
        showToast('Dataset created successfully!', 'success');

        // Reload datasets list if we're on the datasets view
        if (currentView === 'datasets') {
            await loadDatasets();
        }

    } catch (error) {
        console.error('Error saving dataset:', error);
        alert('Error saving dataset: ' + error.message);
    }
}

// Load datasets list
async function loadDatasets() {
    try {
        const response = await fetch('/api/datasets');
        const data = await response.json();

        const grid = document.getElementById('datasets-grid');

        if (!data.datasets || data.datasets.length === 0) {
            grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: #9ca3af;"><p>No datasets yet. Create your first dataset to get started!</p></div>';
            return;
        }

        grid.innerHTML = data.datasets.map(dataset => {
            const sourceIcon = dataset.source_type === 'sql' ? '⚡' : '📊';
            const sourceLabel = dataset.source_type === 'sql' ? 'Custom SQL' : 'Table';

            return `
                <div class="card" style="padding: 1.5rem; border: 1px solid #e5e7eb; border-radius: 12px; background: white; transition: box-shadow 0.2s;" onmouseover="this.style.boxShadow='0 4px 12px rgba(0,0,0,0.1)'" onmouseout="this.style.boxShadow=''">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="font-size: 1.5rem;">${sourceIcon}</span>
                            <h3 style="margin: 0; font-size: 1.125rem; font-weight: 600; color: #1a202c;">${dataset.name}</h3>
                        </div>
                        <div class="dropdown" style="position: relative;">
                            <button onclick="toggleDatasetMenu('${dataset.id}')" style="background: none; border: none; cursor: pointer; font-size: 1.2rem; color: #6b7280; padding: 4px 8px; border-radius: 4px; transition: background 0.2s;" onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background='none'">⋮</button>
                            <div id="dataset-menu-${dataset.id}" class="dropdown-menu" style="display: none; position: absolute; right: 0; top: 100%; background: white; border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); min-width: 150px; z-index: 1000;">
                                <button onclick="editDataset('${dataset.id}')" style="width: 100%; text-align: left; padding: 10px 16px; border: none; background: none; cursor: pointer; font-size: 0.875rem; color: #374151; transition: background 0.2s; border-radius: 8px 8px 0 0;" onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background='none'">✏️ Edit</button>
                                <button onclick="deleteDataset('${dataset.id}', '${dataset.name}')" style="width: 100%; text-align: left; padding: 10px 16px; border: none; background: none; cursor: pointer; font-size: 0.875rem; color: #dc2626; transition: background 0.2s; border-radius: 0 0 8px 8px;" onmouseover="this.style.background='#fef2f2'" onmouseout="this.style.background='none'">🗑️ Delete</button>
                            </div>
                        </div>
                    </div>
                    <div style="display: inline-block; padding: 4px 10px; background: #e0e7ff; color: #667eea; border-radius: 6px; font-size: 0.75rem; font-weight: 500; margin-bottom: 0.75rem;">${sourceLabel}</div>
                    <p style="margin: 0.75rem 0 0 0; color: #6b7280; font-size: 0.875rem; line-height: 1.5;">${dataset.description || 'No description'}</p>
                    ${dataset.source_type === 'table' ?
                        `<p style="margin: 0.5rem 0 0 0; color: #9ca3af; font-size: 0.75rem; font-family: monospace;">${dataset.schema_name || 'public'}.${dataset.table_name}</p>` :
                        `<p style="margin: 0.5rem 0 0 0; color: #9ca3af; font-size: 0.75rem;">Custom SQL Query</p>`
                    }
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading datasets:', error);
        document.getElementById('datasets-grid').innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: #dc2626;"><p>Error loading datasets: ' + error.message + '</p></div>';
    }
}

// Toggle dataset menu
function toggleDatasetMenu(datasetId) {
    const menu = document.getElementById(`dataset-menu-${datasetId}`);

    // Close all other menus
    document.querySelectorAll('.dropdown-menu').forEach(m => {
        if (m.id !== `dataset-menu-${datasetId}`) {
            m.style.display = 'none';
        }
    });

    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
}

// Close menus when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.dropdown')) {
        document.querySelectorAll('.dropdown-menu').forEach(m => {
            m.style.display = 'none';
        });
    }
});

// Edit dataset (placeholder for now)
function editDataset(datasetId) {
    alert('Edit dataset feature coming soon! Dataset ID: ' + datasetId);
}

// Delete dataset
async function deleteDataset(datasetId, datasetName) {
    if (!confirm(`Are you sure you want to delete "${datasetName}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/datasets/${datasetId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to delete dataset');
        }

        showToast('Dataset deleted successfully', 'success');
        await loadDatasets();

    } catch (error) {
        console.error('Error deleting dataset:', error);
        alert('Error deleting dataset: ' + error.message);
    }
}

// Save current SQL query as a dataset
async function saveQueryAsDataset() {
    const sql = document.getElementById('sql-editor')?.value.trim();
    if (!sql) {
        alert('No query to save as dataset');
        return;
    }

    // Prompt for dataset name and description
    const name = prompt('Enter a name for the dataset:');
    if (!name) return;

    const description = prompt('Enter a description (optional):') || '';

    // Generate ID from name
    const datasetId = name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');

    try {
        const response = await fetch('/api/datasets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: datasetId,
                name: name,
                description: description,
                source_type: 'sql',
                sql_query: sql
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to create dataset');
        }

        showToast(`Dataset "${name}" created successfully!`, 'success');

    } catch (error) {
        console.error('Error saving dataset:', error);
        alert('Error saving dataset: ' + error.message);
    }
}

// Export query results to Excel
function exportToExcel() {
    const tableData = window.currentQueryResults;
    if (!tableData || !tableData.data || tableData.data.length === 0) {
        alert('No data to export');
        return;
    }

    // Convert to CSV format first (Excel can open CSV)
    let csv = '';

    // Add headers
    const headers = tableData.columns || Object.keys(tableData.data[0]);
    csv += headers.join(',') + '\n';

    // Add rows
    tableData.data.forEach(row => {
        const values = headers.map(header => {
            let val = row[header];
            // Escape values that contain commas or quotes
            if (val === null || val === undefined) {
                return '';
            }
            val = String(val);
            if (val.includes(',') || val.includes('"') || val.includes('\n')) {
                val = '"' + val.replace(/"/g, '""') + '"';
            }
            return val;
        });
        csv += values.join(',') + '\n';
    });

    // Create blob and download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', 'query_results.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Load datasets when the datasets view is shown
document.addEventListener('DOMContentLoaded', () => {
    // Hook into the view switching to load datasets
    const originalSwitchView = window.switchView;
    window.switchView = function(viewName) {
        originalSwitchView(viewName);
        if (viewName === 'datasets') {
            loadDatasets();
        }
    };
});
