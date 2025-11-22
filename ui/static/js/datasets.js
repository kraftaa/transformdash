// ============================================================================
// Datasets Management JavaScript
// ============================================================================

let currentDatasetSourceType = 'table'; // 'table' or 'sql'
let allDatasetsData = [];
let currentDatasetsSearchTerm = '';

// Debounce utility for datasets search
let datasetsSearchDebounceTimer = null;
function debounceDatasetSearch(callback, delay = 300) {
    clearTimeout(datasetsSearchDebounceTimer);
    datasetsSearchDebounceTimer = setTimeout(callback, delay);
}

// Datasets Search Handler
function handleDatasetsSearch(searchTerm) {
    currentDatasetsSearchTerm = searchTerm;
    const clearBtn = document.getElementById('datasets-search-clear');
    if (clearBtn) {
        clearBtn.style.display = searchTerm ? 'block' : 'none';
    }
    debounceDatasetSearch(() => {
        renderFilteredDatasets();
    });
}

function clearDatasetsSearch() {
    document.getElementById('datasets-search').value = '';
    currentDatasetsSearchTerm = '';
    document.getElementById('datasets-search-clear').style.display = 'none';
    renderFilteredDatasets();
}

function renderFilteredDatasets() {
    const grid = document.getElementById('datasets-grid');
    const viewMode = window.currentDatasetsView || 'grid';

    if (!allDatasetsData || allDatasetsData.length === 0) {
        grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: #9ca3af;"><p>No datasets yet. Create your first dataset to get started!</p></div>';
        return;
    }

    // Apply search filter using the global filterListItems function from app.js
    let filteredDatasets = allDatasetsData;
    if (currentDatasetsSearchTerm && typeof filterListItems === 'function') {
        filteredDatasets = filterListItems(currentDatasetsSearchTerm, allDatasetsData, ['name', 'source_type', 'description']);
    }

    if (filteredDatasets.length === 0) {
        grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: #9ca3af;"><p>No datasets match your search criteria.</p></div>';
        return;
    }

    // Update grid style based on view mode
    if (viewMode === 'list') {
        grid.style.display = 'flex';
        grid.style.flexDirection = 'column';
        grid.style.gap = '12px';
    } else {
        grid.style.display = 'grid';
        grid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(300px, 1fr))';
        grid.style.gap = '20px';
    }

    grid.innerHTML = filteredDatasets.map(dataset => {
        const sourceLabel = dataset.source_type === 'sql' ? 'Custom SQL' : 'Table';

        if (viewMode === 'list') {
            return `
                <div class="card" style="display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.5rem; border: 1px solid #e5e7eb; border-radius: 8px; background: white; transition: box-shadow 0.2s;" onmouseover="this.style.boxShadow='0 2px 8px rgba(0,0,0,0.08)'" onmouseout="this.style.boxShadow=''">
                    <div style="flex: 1; min-width: 0;">
                        <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 0.25rem;">
                            <h3 style="margin: 0; font-size: 1rem; font-weight: 600; color: #1a202c;">${dataset.name}</h3>
                            <span style="padding: 2px 8px; background: #e0e7ff; color: #667eea; border-radius: 4px; font-size: 0.75rem; font-weight: 500;">${sourceLabel}</span>
                        </div>
                        <p style="margin: 0; color: #6b7280; font-size: 0.875rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${dataset.description || 'No description'}</p>
                    </div>
                    <div class="dropdown" style="position: relative; flex-shrink: 0;">
                        <button onclick="toggleDatasetMenu('${dataset.id}')" style="background: none; border: none; cursor: pointer; font-size: 1.2rem; color: #6b7280; padding: 4px 8px; border-radius: 4px; transition: background 0.2s;" onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background='none'">⋮</button>
                        <div id="dataset-menu-${dataset.id}" class="dropdown-menu" style="display: none; position: absolute; right: 0; top: 100%; background: white; border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); min-width: 150px; z-index: 1000;">
                            <button onclick="editDataset('${dataset.id}')" style="width: 100%; text-align: left; padding: 10px 16px; border: none; background: none; cursor: pointer; font-size: 0.875rem; color: #374151; transition: background 0.2s; border-radius: 8px 8px 0 0;" onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background='none'">Edit</button>
                            <button onclick="deleteDataset('${dataset.id}', '${dataset.name}')" style="width: 100%; text-align: left; padding: 10px 16px; border: none; background: none; cursor: pointer; font-size: 0.875rem; color: #dc2626; transition: background 0.2s; border-radius: 0 0 8px 8px;" onmouseover="this.style.background='#fef2f2'" onmouseout="this.style.background='none'">Delete</button>
                        </div>
                    </div>
                </div>
            `;
        } else {
            return `
                <div class="card" style="padding: 1.5rem; border: 1px solid #e5e7eb; border-radius: 12px; background: white; transition: box-shadow 0.2s;" onmouseover="this.style.boxShadow='0 4px 12px rgba(0,0,0,0.1)'" onmouseout="this.style.boxShadow=''">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                        <div>
                            <h3 style="margin: 0; font-size: 1.125rem; font-weight: 600; color: #1a202c;">${dataset.name}</h3>
                        </div>
                        <div class="dropdown" style="position: relative;">
                            <button onclick="toggleDatasetMenu('${dataset.id}')" style="background: none; border: none; cursor: pointer; font-size: 1.2rem; color: #6b7280; padding: 4px 8px; border-radius: 4px; transition: background 0.2s;" onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background='none'">⋮</button>
                            <div id="dataset-menu-${dataset.id}" class="dropdown-menu" style="display: none; position: absolute; right: 0; top: 100%; background: white; border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); min-width: 150px; z-index: 1000;">
                                <button onclick="editDataset('${dataset.id}')" style="width: 100%; text-align: left; padding: 10px 16px; border: none; background: none; cursor: pointer; font-size: 0.875rem; color: #374151; transition: background 0.2s; border-radius: 8px 8px 0 0;" onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background='none'">Edit</button>
                                <button onclick="deleteDataset('${dataset.id}', '${dataset.name}')" style="width: 100%; text-align: left; padding: 10px 16px; border: none; background: none; cursor: pointer; font-size: 0.875rem; color: #dc2626; transition: background 0.2s; border-radius: 0 0 8px 8px;" onmouseover="this.style.background='#fef2f2'" onmouseout="this.style.background='none'">Delete</button>
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
        }
    }).join('');
}

// Open the dataset builder modal
function openDatasetBuilder() {
    // Reset form
    document.getElementById('datasetName').value = '';
    document.getElementById('datasetDescription').value = '';
    document.getElementById('datasetSchema').value = 'public';
    document.getElementById('datasetTableName').value = '';
    document.getElementById('datasetSQLQuery').value = '';
    document.getElementById('datasetPreview').style.display = 'none';

    // Reset CSV file input
    const csvFileInput = document.getElementById('datasetCSVFile');
    if (csvFileInput) {
        csvFileInput.value = '';
        document.getElementById('csvFileInfo').style.display = 'none';
    }

    // Reset to table mode
    switchDatasetSourceType('table');

    // Show modal
    document.getElementById('datasetBuilderModal').style.display = 'block';

    // Add file input change listener
    if (csvFileInput && !csvFileInput.dataset.listenerAttached) {
        csvFileInput.addEventListener('change', handleCSVFileSelection);
        csvFileInput.dataset.listenerAttached = 'true';
    }
}

// Handle CSV file selection
function handleCSVFileSelection(event) {
    const file = event.target.files[0];
    if (file) {
        const fileSizeKB = (file.size / 1024).toFixed(2);
        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
        const sizeStr = file.size > 1024 * 1024 ? `${fileSizeMB} MB` : `${fileSizeKB} KB`;

        document.getElementById('csvFileName').textContent = file.name;
        document.getElementById('csvFileSize').textContent = sizeStr;
        document.getElementById('csvFileInfo').style.display = 'block';

        // Auto-fill dataset name if empty
        const nameInput = document.getElementById('datasetName');
        if (!nameInput.value) {
            const baseName = file.name.replace(/\.csv$/i, '').replace(/[^a-z0-9_]/gi, '_');
            nameInput.value = baseName;
        }
    }
}

// Switch between table, SQL, and CSV source types
function switchDatasetSourceType(type) {
    currentDatasetSourceType = type;

    // Update button styles
    const tableBtn = document.getElementById('sourceTypeTable');
    const sqlBtn = document.getElementById('sourceTypeSQL');
    const csvBtn = document.getElementById('sourceTypeCSV');

    // Reset all buttons
    tableBtn.style.background = '';
    tableBtn.style.color = '';
    sqlBtn.style.background = '';
    sqlBtn.style.color = '';
    csvBtn.style.background = '';
    csvBtn.style.color = '';

    // Hide all config sections
    document.getElementById('tableModeConfig').style.display = 'none';
    document.getElementById('sqlModeConfig').style.display = 'none';
    document.getElementById('csvModeConfig').style.display = 'none';

    // Show selected mode
    if (type === 'table') {
        tableBtn.style.background = '#667eea';
        tableBtn.style.color = 'white';
        document.getElementById('tableModeConfig').style.display = 'block';
    } else if (type === 'sql') {
        sqlBtn.style.background = '#667eea';
        sqlBtn.style.color = 'white';
        document.getElementById('sqlModeConfig').style.display = 'block';
    } else if (type === 'csv') {
        csvBtn.style.background = '#667eea';
        csvBtn.style.color = 'white';
        document.getElementById('csvModeConfig').style.display = 'block';
    }
}

// Preview dataset data
async function previewDataset() {
    try {
        let response;

        if (currentDatasetSourceType === 'csv') {
            // Handle CSV file preview
            const fileInput = document.getElementById('datasetCSVFile');
            const file = fileInput.files[0];

            if (!file) {
                alert('Please select a CSV file');
                return;
            }

            // Upload file and get preview
            const formData = new FormData();
            formData.append('file', file);
            formData.append('preview_only', 'true');

            response = await fetch('/api/datasets/upload-csv', {
                method: 'POST',
                body: formData
            });
        } else {
            // Handle table or SQL preview
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

            response = await fetch('/api/datasets/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(previewPayload)
            });
        }

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to preview dataset');
        }

        // Show preview
        const previewDiv = document.getElementById('datasetPreview');
        const contentDiv = document.getElementById('datasetPreviewContent');

        if (data.data && data.data.length > 0) {
            let tableHTML = '<table style="width: 100%; border-collapse: collapse; font-size: 0.75rem;"><thead><tr>';

            // Extract column names - handle both string arrays and object arrays
            const columnNames = data.columns.map(col => typeof col === 'string' ? col : col.name);

            // Headers
            columnNames.forEach(colName => {
                tableHTML += `<th style="padding: 8px; text-align: left; border-bottom: 2px solid #e5e7eb; font-weight: 600; background: white; position: sticky; top: 0;">${colName}</th>`;
            });
            tableHTML += '</tr></thead><tbody>';

            // Rows
            data.data.forEach(row => {
                tableHTML += '<tr style="border-bottom: 1px solid #f3f4f6;">';
                columnNames.forEach(colName => {
                    const val = row[colName];
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
        } else if (currentDatasetSourceType === 'sql') {
            const sqlQuery = document.getElementById('datasetSQLQuery').value.trim();

            if (!sqlQuery) {
                alert('Please enter a SQL query');
                return;
            }

            payload.sql_query = sqlQuery;
        } else if (currentDatasetSourceType === 'csv') {
            const fileInput = document.getElementById('datasetCSVFile');
            const file = fileInput.files[0];

            if (!file) {
                alert('Please select a CSV file');
                return;
            }

            // Upload CSV file first
            const formData = new FormData();
            formData.append('file', file);
            formData.append('dataset_id', datasetId);
            formData.append('dataset_name', name);
            formData.append('dataset_description', description);

            const uploadResponse = await fetch('/api/datasets/upload-csv', {
                method: 'POST',
                body: formData
            });

            const uploadData = await uploadResponse.json();

            if (!uploadResponse.ok) {
                throw new Error(uploadData.detail || 'Failed to upload CSV file');
            }

            // Close modal and refresh
            document.getElementById('datasetBuilderModal').style.display = 'none';
            alert('Dataset created successfully!');
            await loadDatasets();
            return;
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

        // Store datasets globally for search
        allDatasetsData = data.datasets || [];

        // Use the rendering function that handles search
        renderFilteredDatasets();

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

// Global variable to store current dataset being edited
let currentEditingDataset = null;

// Edit dataset - opens full editor view
async function editDataset(datasetId) {
    try {
        // Fetch dataset details
        const response = await fetch(`/api/datasets/${datasetId}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to load dataset');
        }

        const dataset = data.dataset;
        currentEditingDataset = dataset;

        // Populate editor fields
        document.getElementById('dataset-editor-title').textContent = dataset.name;
        document.getElementById('dataset-editor-subtitle').textContent = dataset.description || 'No description';

        document.getElementById('edit-dataset-name').value = dataset.name;
        document.getElementById('edit-dataset-description').value = dataset.description || '';
        document.getElementById('edit-dataset-connection').textContent = dataset.connection_id || 'Default Connection';

        // Source type
        const sourceLabel = dataset.source_type === 'sql' ? 'Custom SQL' : 'Table';
        document.getElementById('edit-dataset-source-type').textContent = sourceLabel;

        // Show table info if applicable
        if (dataset.source_type === 'table') {
            document.getElementById('edit-dataset-table-info').style.display = 'block';
            const schema = dataset.schema_name || 'public';
            document.getElementById('edit-dataset-table-ref').textContent = `${schema}.${dataset.table_name}`;
        } else {
            document.getElementById('edit-dataset-table-info').style.display = 'none';
        }

        // Load columns
        await loadDatasetColumns(dataset);

        // Load query
        loadDatasetQuery(dataset);

        // Switch to editor view
        document.getElementById('datasets-view').style.display = 'none';
        document.getElementById('dataset-editor-view').style.display = 'block';

        // Reset to overview tab
        switchEditorTab('overview');

    } catch (error) {
        console.error('Error loading dataset:', error);
        alert('Error loading dataset: ' + error.message);
    }
}

// Close dataset editor and return to list
function closeDatasetEditor() {
    document.getElementById('dataset-editor-view').style.display = 'none';
    document.getElementById('datasets-view').style.display = 'block';
    currentEditingDataset = null;
}

// Switch between editor tabs
function switchEditorTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.editor-tab').forEach(tab => {
        const tabId = tab.id.replace('editor-tab-', '');
        if (tabId === tabName) {
            tab.style.color = '#667eea';
            tab.style.fontWeight = '600';
            tab.style.borderBottom = '2px solid #667eea';
            tab.style.marginBottom = '-2px';
        } else {
            tab.style.color = '#6b7280';
            tab.style.fontWeight = '500';
            tab.style.borderBottom = 'none';
            tab.style.marginBottom = '0';
        }
    });

    // Update content visibility
    document.querySelectorAll('.editor-tab-content').forEach(content => {
        content.style.display = 'none';
    });
    document.getElementById(`editor-content-${tabName}`).style.display = 'block';
}

// Load dataset columns
async function loadDatasetColumns(dataset) {
    try {
        const tbody = document.getElementById('dataset-columns-tbody');
        tbody.innerHTML = '<tr><td colspan="3" style="padding: 2rem; text-align: center; color: #9ca3af;">Loading columns...</td></tr>';

        // For CSV datasets, columns are already stored in the dataset object
        if (dataset.source_type === 'csv') {
            if (dataset.columns && dataset.columns.length > 0) {
                tbody.innerHTML = dataset.columns.map(col => {
                    const colName = typeof col === 'string' ? col : col.name;
                    const colType = typeof col === 'string' ? 'text' : (col.type || 'text').toLowerCase();

                    return `
                        <tr style="border-bottom: 1px solid #f3f4f6;">
                            <td style="padding: 12px; font-family: monospace; color: #1f2937;">${colName}</td>
                            <td style="padding: 12px; color: #6b7280;">${colType}</td>
                            <td style="padding: 12px; color: #6b7280;">Yes</td>
                        </tr>
                    `;
                }).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="3" style="padding: 2rem; text-align: center; color: #9ca3af;">No columns found</td></tr>';
            }
            return;
        }

        // For table and SQL datasets, preview the dataset to get columns
        const previewPayload = {
            source_type: dataset.source_type,
            limit: 1
        };

        if (dataset.source_type === 'table') {
            previewPayload.table_name = dataset.table_name;
            previewPayload.schema_name = dataset.schema_name || 'public';
        } else {
            previewPayload.sql_query = dataset.sql_query;
        }

        const response = await fetch('/api/datasets/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(previewPayload)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to load columns');
        }

        if (data.columns && data.columns.length > 0) {
            tbody.innerHTML = data.columns.map(col => {
                // Try to infer type from data
                let dataType = 'unknown';
                if (data.data && data.data.length > 0) {
                    const val = data.data[0][col];
                    if (typeof val === 'number') {
                        dataType = Number.isInteger(val) ? 'integer' : 'numeric';
                    } else if (typeof val === 'boolean') {
                        dataType = 'boolean';
                    } else if (typeof val === 'string') {
                        dataType = 'text';
                    }
                }

                return `
                    <tr style="border-bottom: 1px solid #f3f4f6;">
                        <td style="padding: 12px; font-family: monospace; color: #1f2937;">${col}</td>
                        <td style="padding: 12px; color: #6b7280;">${dataType}</td>
                        <td style="padding: 12px; color: #6b7280;">Yes</td>
                    </tr>
                `;
            }).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="3" style="padding: 2rem; text-align: center; color: #9ca3af;">No columns found</td></tr>';
        }

    } catch (error) {
        console.error('Error loading columns:', error);
        const tbody = document.getElementById('dataset-columns-tbody');
        tbody.innerHTML = `<tr><td colspan="3" style="padding: 2rem; text-align: center; color: #dc2626;">Error: ${error.message}</td></tr>`;
    }
}

// Refresh dataset columns
async function refreshDatasetColumns() {
    if (currentEditingDataset) {
        await loadDatasetColumns(currentEditingDataset);
        showToast('Columns refreshed', 'success');
    }
}

// Load dataset query for display
function loadDatasetQuery(dataset) {
    const queryDisplay = document.getElementById('dataset-query-display');

    if (dataset.source_type === 'csv') {
        queryDisplay.textContent = `-- CSV File: ${dataset.original_filename || 'uploaded file'}\n-- File path: ${dataset.file_path || 'N/A'}\n-- Rows: Data loaded from CSV file`;
    } else if (dataset.source_type === 'sql') {
        queryDisplay.textContent = dataset.sql_query;
    } else {
        const schema = dataset.schema_name || 'public';
        queryDisplay.textContent = `SELECT *\nFROM ${schema}.${dataset.table_name};`;
    }
}

// Copy dataset query to clipboard
function copyDatasetQuery() {
    const queryText = document.getElementById('dataset-query-display').textContent;
    navigator.clipboard.writeText(queryText).then(() => {
        showToast('SQL copied to clipboard', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy to clipboard');
    });
}

// Add metric (placeholder)
function addMetric() {
    alert('Add metric feature coming soon! This will allow you to define calculated fields like SUM(amount), AVG(price), etc.');
}

// Update dataset query (placeholder)
function updateDatasetQuery() {
    alert('Update query feature coming soon!');
}

// Save dataset changes
async function saveDatasetChanges() {
    if (!currentEditingDataset) {
        alert('No dataset loaded');
        return;
    }

    try {
        const name = document.getElementById('edit-dataset-name').value.trim();
        const description = document.getElementById('edit-dataset-description').value.trim();

        if (!name) {
            alert('Dataset name is required');
            return;
        }

        const payload = {
            name: name,
            description: description
        };

        const response = await fetch(`/api/datasets/${currentEditingDataset.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to update dataset');
        }

        showToast('Dataset updated successfully!', 'success');

        // Update title
        document.getElementById('dataset-editor-title').textContent = name;
        document.getElementById('dataset-editor-subtitle').textContent = description || 'No description';

        // Update current dataset object
        currentEditingDataset.name = name;
        currentEditingDataset.description = description;

    } catch (error) {
        console.error('Error saving dataset:', error);
        alert('Error saving dataset: ' + error.message);
    }
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

// Datasets view toggle
window.currentDatasetsView = 'grid';

function toggleDatasetsView(view) {
    window.currentDatasetsView = view;

    // Update button states
    document.querySelectorAll('#datasets-view .view-toggle-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === view);
    });

    // Reload datasets with new view
    renderFilteredDatasets();
}
