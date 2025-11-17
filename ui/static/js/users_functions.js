// =============================================================================
// Users & Permissions Functions
// =============================================================================

async function loadUsersView() {
    try {
        // Load users
        const usersResponse = await fetch('/api/users');
        const usersData = await usersResponse.json();

        // Load roles
        const rolesResponse = await fetch('/api/roles');
        const rolesData = await rolesResponse.json();

        displayUsersTable(usersData.users);
        displayRolesTable(rolesData.roles);
    } catch (error) {
        console.error('Error loading users:', error);
        showToast('Failed to load users and roles', 'error');
    }
}

function displayUsersTable(users) {
    const container = document.getElementById('users-table-container');

    if (users.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 40px; color: #9ca3af;">No users found</div>';
        return;
    }

    const table = document.createElement('table');
    table.className = 'view-table';
    table.style.width = '100%';
    table.style.borderCollapse = 'separate';
    table.style.borderSpacing = '0';
    table.innerHTML = `
        <thead>
            <tr style="background: #f9fafb;">
                <th style="padding: 16px; text-align: left; font-weight: 600; font-size: 0.875rem; color: #374151; border-bottom: 2px solid #e5e7eb;">Username</th>
                <th style="padding: 16px; text-align: left; font-weight: 600; font-size: 0.875rem; color: #374151; border-bottom: 2px solid #e5e7eb;">Email</th>
                <th style="padding: 16px; text-align: left; font-weight: 600; font-size: 0.875rem; color: #374151; border-bottom: 2px solid #e5e7eb;">Full Name</th>
                <th style="padding: 16px; text-align: left; font-weight: 600; font-size: 0.875rem; color: #374151; border-bottom: 2px solid #e5e7eb;">Roles</th>
                <th style="padding: 16px; text-align: left; font-weight: 600; font-size: 0.875rem; color: #374151; border-bottom: 2px solid #e5e7eb;">Status</th>
                <th style="padding: 16px; text-align: left; font-weight: 600; font-size: 0.875rem; color: #374151; border-bottom: 2px solid #e5e7eb;">Superuser</th>
                <th style="padding: 16px; text-align: left; font-weight: 600; font-size: 0.875rem; color: #374151; border-bottom: 2px solid #e5e7eb;">Last Login</th>
                <th style="padding: 16px; text-align: right; font-weight: 600; font-size: 0.875rem; color: #374151; border-bottom: 2px solid #e5e7eb;">Actions</th>
            </tr>
        </thead>
        <tbody></tbody>
    `;

    const tbody = table.querySelector('tbody');

    users.forEach(user => {
        const row = document.createElement('tr');

        const roles = typeof user.roles === 'string' ? JSON.parse(user.roles) : user.roles;
        const roleNames = roles.map(r => r.name).join(', ') || 'No roles';

        const statusBadge = user.is_active
            ? '<span style="background: #10b981; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem;">Active</span>'
            : '<span style="background: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem;">Inactive</span>';

        const superuserBadge = user.is_superuser
            ? '<span style="background: #8b5cf6; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem;">Yes</span>'
            : '<span style="color: #9ca3af;">No</span>';

        const lastLogin = user.last_login
            ? new Date(user.last_login).toLocaleString()
            : '<span style="color: #9ca3af;">Never</span>';

        row.style.transition = 'background 0.15s';
        row.onmouseenter = () => row.style.background = '#f9fafb';
        row.onmouseleave = () => row.style.background = 'transparent';

        row.innerHTML = `
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6;"><strong style="color: #111827; font-size: 0.9375rem;">${user.username}</strong></td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6; color: #6b7280; font-size: 0.875rem;">${user.email}</td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6; color: #6b7280; font-size: 0.875rem;">${user.full_name || '<span style="color: #9ca3af;">-</span>'}</td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6;"><span style="background: #ede9fe; color: #7c3aed; padding: 6px 12px; border-radius: 6px; font-size: 0.8125rem; font-weight: 500;">${roleNames}</span></td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6;">${statusBadge}</td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6;">${superuserBadge}</td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6; color: #6b7280; font-size: 0.875rem;">${lastLogin}</td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6; text-align: right;">
                <button onclick="editUser(${user.id})" style="background: #3b82f6; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; margin-right: 8px; font-size: 0.875rem; font-weight: 500; transition: all 0.15s;" onmouseover="this.style.background='#2563eb'" onmouseout="this.style.background='#3b82f6'">
                    Edit
                </button>
                <button onclick="deleteUser(${user.id}, '${user.username}')" style="background: #ef4444; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 0.875rem; font-weight: 500; transition: all 0.15s;" onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='#ef4444'">
                    Delete
                </button>
            </td>
        `;

        tbody.appendChild(row);
    });

    container.innerHTML = '';
    container.appendChild(table);
}

function displayRolesTable(roles) {
    const container = document.getElementById('roles-table-container');

    if (roles.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 40px; color: #9ca3af;">No roles found</div>';
        return;
    }

    const table = document.createElement('table');
    table.className = 'view-table';
    table.style.width = '100%';
    table.style.borderCollapse = 'separate';
    table.style.borderSpacing = '0';
    table.innerHTML = `
        <thead>
            <tr style="background: #f9fafb;">
                <th style="padding: 16px; text-align: left; font-weight: 600; font-size: 0.875rem; color: #374151; border-bottom: 2px solid #e5e7eb;">Role Name</th>
                <th style="padding: 16px; text-align: left; font-weight: 600; font-size: 0.875rem; color: #374151; border-bottom: 2px solid #e5e7eb;">Description</th>
                <th style="padding: 16px; text-align: left; font-weight: 600; font-size: 0.875rem; color: #374151; border-bottom: 2px solid #e5e7eb;">Permissions</th>
                <th style="padding: 16px; text-align: right; font-weight: 600; font-size: 0.875rem; color: #374151; border-bottom: 2px solid #e5e7eb;">Actions</th>
            </tr>
        </thead>
        <tbody></tbody>
    `;

    const tbody = table.querySelector('tbody');

    roles.forEach(role => {
        const row = document.createElement('tr');
        row.style.transition = 'background 0.15s';
        row.onmouseenter = () => row.style.background = '#f9fafb';
        row.onmouseleave = () => row.style.background = 'transparent';

        const permissions = typeof role.permissions === 'string' ? JSON.parse(role.permissions) : role.permissions;
        const permissionCount = permissions.length;

        row.innerHTML = `
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6;"><strong style="color: #111827; font-size: 0.9375rem;">${role.name}</strong></td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6; color: #6b7280; font-size: 0.875rem;">${role.description || '<span style="color: #9ca3af;">-</span>'}</td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6;"><span style="background: #dbeafe; color: #1e40af; padding: 6px 12px; border-radius: 6px; font-size: 0.8125rem; font-weight: 500;">${permissionCount} permissions</span></td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6; text-align: right;">
                <button onclick="viewRolePermissions(${role.id}, '${role.name}')" style="background: #3b82f6; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; margin-right: 8px; font-size: 0.875rem; font-weight: 500; transition: all 0.15s;" onmouseover="this.style.background='#2563eb'" onmouseout="this.style.background='#3b82f6'">
                    View Permissions
                </button>
                <button onclick="editRole(${role.id}, '${role.name}')" style="background: #10b981; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; margin-right: 8px; font-size: 0.875rem; font-weight: 500; transition: all 0.15s;" onmouseover="this.style.background='#059669'" onmouseout="this.style.background='#10b981'">
                    Edit
                </button>
                <button onclick="deleteRole(${role.id}, '${role.name}')" style="background: #ef4444; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 0.875rem; font-weight: 500; transition: all 0.15s;" onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='#ef4444'">
                    Delete
                </button>
            </td>
        `;

        tbody.appendChild(row);
    });

    container.innerHTML = '';
    container.appendChild(table);
}

function showCreateUserModal() {
    alert('Create User Modal - Coming soon!\n\nThis feature will allow you to create new users with username, email, password, and assign roles.');
}

async function editUser(userId) {
    alert('Edit User Modal - Coming soon!\n\nThis feature will allow you to edit user details, change passwords, and update role assignments.');
}

async function deleteUser(userId, username) {
    if (!confirm(`Are you sure you want to delete user "${username}"?\n\nThis action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/users/${userId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showToast(`User "${username}" deleted successfully`, 'success');
            loadUsersView();
        } else {
            const error = await response.json();
            showToast(`Failed to delete user: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        showToast('Failed to delete user', 'error');
    }
}

function viewRolePermissions(roleId, roleName) {
    fetch('/api/roles')
        .then(response => response.json())
        .then(data => {
            const role = data.roles.find(r => r.id === roleId);
            if (!role) return;

            const permissions = typeof role.permissions === 'string' ? JSON.parse(role.permissions) : role.permissions;

            alert(`Permissions for role "${roleName}":\n\n${permissions.map(p => `• ${p.name} (${p.resource}:${p.action})`).join('\n')}`);
        });
}

// Hook into switchView to load users when view is activated
document.addEventListener('DOMContentLoaded', function() {
    const originalSwitchView = window.switchView;
    window.switchView = function(viewName) {
        originalSwitchView(viewName);
        if (viewName === 'users') {
            loadUsersView();
        }
    };
});

function showCreateRoleModal() {
    alert('Create Role Modal - Coming soon!\n\nThis feature will allow you to create new roles and assign permissions.');
}

function editRole(roleId, roleName) {
    alert('Edit Role Modal - Coming soon!\n\nThis feature will allow you to edit role details and modify assigned permissions.');
}

function deleteRole(roleId, roleName) {
    if (!confirm(`Are you sure you want to delete role "${roleName}"?\n\nThis action cannot be undone.`)) {
        return;
    }

    fetch(`/api/roles/${roleId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            showToast(`Role "${roleName}" deleted successfully`, 'success');
            loadUsersView();
        }
    })
    .catch(error => {
        console.error('Error deleting role:', error);
        showToast('Failed to delete role', 'error');
    });
}
