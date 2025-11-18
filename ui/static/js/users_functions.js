// =============================================================================
// Users & Permissions Functions
// =============================================================================

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} unsafe - Untrusted string that may contain HTML
 * @returns {string} - HTML-escaped safe string
 */
function escapeHtml(unsafe) {
    if (unsafe === null || unsafe === undefined) {
        return '';
    }
    return String(unsafe)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

async function loadUsersView() {
    try {
        // Load users
        const usersResponse = await fetch('/api/users');

        // Check if user has permission (403 = Forbidden)
        if (usersResponse.status === 403) {
            const usersContainer = document.getElementById('users-table-container');
            const rolesContainer = document.getElementById('roles-table-container');

            if (usersContainer) {
                usersContainer.innerHTML = '<div style="text-align: center; padding: 60px; color: #ef4444;"><h3 style="margin-bottom: 16px;">⛔ Access Denied</h3><p>You do not have permission to view users and roles.</p><p style="color: #6b7280; margin-top: 8px;">Contact your administrator to request access.</p></div>';
            }
            if (rolesContainer) {
                rolesContainer.innerHTML = '';
            }

            // Hide the "Add User" and "Add Role" buttons
            const addUserBtn = document.querySelector('[onclick="showCreateUserModal()"]');
            const addRoleBtn = document.querySelector('[onclick="showCreateRoleModal()"]');
            if (addUserBtn) addUserBtn.style.display = 'none';
            if (addRoleBtn) addRoleBtn.style.display = 'none';

            showToast('Access denied: Insufficient permissions', 'error');
            return;
        }

        if (!usersResponse.ok) {
            throw new Error('Failed to load users');
        }

        const usersData = await usersResponse.json();

        // Load roles
        const rolesResponse = await fetch('/api/roles');

        if (rolesResponse.status === 403) {
            showToast('Access denied: Cannot view roles', 'error');
            return;
        }

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
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6;"><strong style="color: #111827; font-size: 0.9375rem;">${escapeHtml(user.username)}</strong></td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6; color: #6b7280; font-size: 0.875rem;">${escapeHtml(user.email)}</td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6; color: #6b7280; font-size: 0.875rem;">${user.full_name ? escapeHtml(user.full_name) : '<span style="color: #9ca3af;">-</span>'}</td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6;"><span style="background: #ede9fe; color: #7c3aed; padding: 6px 12px; border-radius: 6px; font-size: 0.8125rem; font-weight: 500;">${escapeHtml(roleNames)}</span></td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6;">${statusBadge}</td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6;">${superuserBadge}</td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6; color: #6b7280; font-size: 0.875rem;">${lastLogin}</td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6; text-align: right;">
                <button onclick="editUser(${user.id})" style="background: #3b82f6; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; margin-right: 8px; font-size: 0.875rem; font-weight: 500; transition: all 0.15s;" onmouseover="this.style.background='#2563eb'" onmouseout="this.style.background='#3b82f6'">
                    Edit
                </button>
                <button onclick="deleteUser(${user.id}, '${escapeHtml(user.username)}')" style="background: #ef4444; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 0.875rem; font-weight: 500; transition: all 0.15s;" onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='#ef4444'">
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
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6;"><strong style="color: #111827; font-size: 0.9375rem;">${escapeHtml(role.name)}</strong></td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6; color: #6b7280; font-size: 0.875rem;">${role.description ? escapeHtml(role.description) : '<span style="color: #9ca3af;">-</span>'}</td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6;"><span style="background: #dbeafe; color: #1e40af; padding: 6px 12px; border-radius: 6px; font-size: 0.8125rem; font-weight: 500;">${escapeHtml(permissionCount.toString())} permissions</span></td>
            <td style="padding: 20px 16px; border-bottom: 1px solid #f3f4f6; text-align: right;">
                <button onclick="viewRolePermissions(${role.id}, '${escapeHtml(role.name)}')" style="background: #3b82f6; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; margin-right: 8px; font-size: 0.875rem; font-weight: 500; transition: all 0.15s;" onmouseover="this.style.background='#2563eb'" onmouseout="this.style.background='#3b82f6'">
                    View Permissions
                </button>
                <button onclick="editRole(${role.id}, '${escapeHtml(role.name)}')" style="background: #10b981; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; margin-right: 8px; font-size: 0.875rem; font-weight: 500; transition: all 0.15s;" onmouseover="this.style.background='#059669'" onmouseout="this.style.background='#10b981'">
                    Edit
                </button>
                <button onclick="deleteRole(${role.id}, '${escapeHtml(role.name)}')" style="background: #ef4444; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 0.875rem; font-weight: 500; transition: all 0.15s;" onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='#ef4444'">
                    Delete
                </button>
            </td>
        `;

        tbody.appendChild(row);
    });

    container.innerHTML = '';
    container.appendChild(table);
}

async function showCreateUserModal() {
    // Fetch available roles
    const rolesResponse = await fetch('/api/roles');
    const rolesData = await rolesResponse.json();
    const roles = rolesData.roles;

    // Create modal HTML
    const modalHtml = `
        <div id="createUserModal" class="modal" style="display: block; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); z-index: 10000; display: flex; align-items: center; justify-content: center; overflow-y: auto;">
            <div class="modal-content" style="max-width: 600px; background: white; border-radius: 16px; padding: 32px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04); max-height: 90vh; overflow-y: auto; position: relative; margin: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                    <h2 style="margin: 0; font-size: 1.5rem; color: #111827;">Create New User</h2>
                    <button onclick="closeCreateUserModal()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #6b7280;">&times;</button>
                </div>

                <form id="createUserForm" style="display: flex; flex-direction: column; gap: 20px;">
                    <div>
                        <label style="display: block; margin-bottom: 8px; font-weight: 500; color: #374151;">Username *</label>
                        <input type="text" id="newUsername" required style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.875rem;">
                    </div>

                    <div>
                        <label style="display: block; margin-bottom: 8px; font-weight: 500; color: #374151;">Email *</label>
                        <input type="email" id="newEmail" required style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.875rem;">
                    </div>

                    <div>
                        <label style="display: block; margin-bottom: 8px; font-weight: 500; color: #374151;">Password *</label>
                        <input type="password" id="newPassword" required minlength="8" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.875rem;">
                        <small style="color: #6b7280; font-size: 0.75rem;">Minimum 8 characters</small>
                    </div>

                    <div>
                        <label style="display: block; margin-bottom: 8px; font-weight: 500; color: #374151;">Full Name</label>
                        <input type="text" id="newFullName" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.875rem;">
                    </div>

                    <div>
                        <label style="display: block; margin-bottom: 8px; font-weight: 500; color: #374151;">Assign Roles</label>
                        <div id="roleCheckboxes" style="display: flex; flex-direction: column; gap: 10px; padding: 12px; background: #f9fafb; border-radius: 8px;">
                            ${roles.map(role => `
                                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                    <input type="checkbox" name="role" value="${role.id}" style="cursor: pointer;">
                                    <span style="font-size: 0.875rem; color: #374151;">
                                        <strong>${escapeHtml(role.name)}</strong>
                                        ${role.description ? `<span style="color: #6b7280;"> - ${escapeHtml(role.description)}</span>` : ''}
                                    </span>
                                </label>
                            `).join('')}
                        </div>
                    </div>

                    <div style="display: flex; align-items: center; gap: 8px;">
                        <input type="checkbox" id="newIsActive" checked style="cursor: pointer;">
                        <label for="newIsActive" style="font-size: 0.875rem; color: #374151; cursor: pointer;">Active user</label>
                    </div>

                    <div style="display: flex; align-items: center; gap: 8px;">
                        <input type="checkbox" id="newIsSuperuser" style="cursor: pointer;">
                        <label for="newIsSuperuser" style="font-size: 0.875rem; color: #374151; cursor: pointer;">
                            Superuser (bypasses all permission checks)
                        </label>
                    </div>

                    <div style="display: flex; gap: 12px; margin-top: 8px;">
                        <button type="submit" style="flex: 1; background: #3b82f6; color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 0.875rem;">
                            Create User
                        </button>
                        <button type="button" onclick="closeCreateUserModal()" style="flex: 1; background: #6b7280; color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 0.875rem;">
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        </div>
    `;

    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Close modal when clicking outside the content
    document.getElementById('createUserModal').addEventListener('click', (e) => {
        if (e.target.id === 'createUserModal') {
            closeCreateUserModal();
        }
    });

    // Handle form submission
    document.getElementById('createUserForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const username = document.getElementById('newUsername').value;
        const email = document.getElementById('newEmail').value;
        const password = document.getElementById('newPassword').value;
        const fullName = document.getElementById('newFullName').value;
        const isActive = document.getElementById('newIsActive').checked;
        const isSuperuser = document.getElementById('newIsSuperuser').checked;

        // Get selected roles
        const selectedRoles = Array.from(document.querySelectorAll('input[name="role"]:checked'))
            .map(cb => parseInt(cb.value));

        try {
            const response = await fetch('/api/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username,
                    email,
                    password,
                    full_name: fullName,
                    is_active: isActive,
                    is_superuser: isSuperuser,
                    role_ids: selectedRoles
                })
            });

            if (response.ok) {
                showToast('User created successfully', 'success');
                closeCreateUserModal();
                loadUsersView();
            } else {
                const error = await response.json();
                showToast(`Failed to create user: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error creating user:', error);
            showToast('Failed to create user', 'error');
        }
    });
}

function closeCreateUserModal() {
    const modal = document.getElementById('createUserModal');
    if (modal) {
        modal.remove();
    }
}

async function editUser(userId) {
    try {
        // Fetch user details
        const usersResponse = await fetch('/api/users');
        const usersData = await usersResponse.json();
        const user = usersData.users.find(u => u.id === userId);

        if (!user) {
            showToast('User not found', 'error');
            return;
        }

        // Fetch available roles
        const rolesResponse = await fetch('/api/roles');
        const rolesData = await rolesResponse.json();
        const roles = rolesData.roles;

        // Get user's current role IDs
        const userRoles = typeof user.roles === 'string' ? JSON.parse(user.roles) : user.roles;
        const userRoleIds = userRoles.map(r => r.id);

        // Create modal HTML
        const modalHtml = `
            <div id="editUserModal" class="modal" style="display: block; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); z-index: 10000; display: flex; align-items: center; justify-content: center; overflow-y: auto;">
                <div class="modal-content" style="max-width: 600px; background: white; border-radius: 16px; padding: 32px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04); max-height: 90vh; overflow-y: auto; position: relative; margin: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                        <h2 style="margin: 0; font-size: 1.5rem; color: #111827;">Edit User: ${escapeHtml(user.username)}</h2>
                        <button onclick="closeEditUserModal()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #6b7280;">&times;</button>
                    </div>

                    <form id="editUserForm" style="display: flex; flex-direction: column; gap: 20px;">
                        <div>
                            <label style="display: block; margin-bottom: 8px; font-weight: 500; color: #374151;">Username *</label>
                            <input type="text" id="editUsername" required value="${escapeHtml(user.username)}" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.875rem;">
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 8px; font-weight: 500; color: #374151;">Email *</label>
                            <input type="email" id="editEmail" required value="${escapeHtml(user.email)}" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.875rem;">
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 8px; font-weight: 500; color: #374151;">New Password (leave blank to keep current)</label>
                            <input type="password" id="editPassword" minlength="8" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.875rem;">
                            <small style="color: #6b7280; font-size: 0.75rem;">Minimum 8 characters</small>
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 8px; font-weight: 500; color: #374151;">Full Name</label>
                            <input type="text" id="editFullName" value="${escapeHtml(user.full_name || '')}" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.875rem;">
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 8px; font-weight: 500; color: #374151;">Assign Roles</label>
                            <div id="editRoleCheckboxes" style="display: flex; flex-direction: column; gap: 10px; padding: 12px; background: #f9fafb; border-radius: 8px;">
                                ${roles.map(role => `
                                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                        <input type="checkbox" name="role" value="${role.id}" ${userRoleIds.includes(role.id) ? 'checked' : ''} style="cursor: pointer;">
                                        <span style="font-size: 0.875rem; color: #374151;">
                                            <strong>${escapeHtml(role.name)}</strong>
                                            ${role.description ? `<span style="color: #6b7280;"> - ${escapeHtml(role.description)}</span>` : ''}
                                        </span>
                                    </label>
                                `).join('')}
                            </div>
                        </div>

                        <div style="display: flex; align-items: center; gap: 8px;">
                            <input type="checkbox" id="editIsActive" ${user.is_active ? 'checked' : ''} style="cursor: pointer;">
                            <label for="editIsActive" style="font-size: 0.875rem; color: #374151; cursor: pointer;">Active user</label>
                        </div>

                        <div style="display: flex; align-items: center; gap: 8px;">
                            <input type="checkbox" id="editIsSuperuser" ${user.is_superuser ? 'checked' : ''} style="cursor: pointer;">
                            <label for="editIsSuperuser" style="font-size: 0.875rem; color: #374151; cursor: pointer;">
                                Superuser (bypasses all permission checks)
                            </label>
                        </div>

                        <div style="display: flex; gap: 12px; margin-top: 8px;">
                            <button type="submit" style="flex: 1; background: #3b82f6; color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 0.875rem;">
                                Save Changes
                            </button>
                            <button type="button" onclick="closeEditUserModal()" style="flex: 1; background: #6b7280; color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 0.875rem;">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Close modal when clicking outside the content
        document.getElementById('editUserModal').addEventListener('click', (e) => {
            if (e.target.id === 'editUserModal') {
                closeEditUserModal();
            }
        });

        // Handle form submission
        document.getElementById('editUserForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('editUsername').value;
            const email = document.getElementById('editEmail').value;
            const password = document.getElementById('editPassword').value;
            const fullName = document.getElementById('editFullName').value;
            const isActive = document.getElementById('editIsActive').checked;
            const isSuperuser = document.getElementById('editIsSuperuser').checked;

            // Get selected roles
            const selectedRoles = Array.from(document.querySelectorAll('#editRoleCheckboxes input[name="role"]:checked'))
                .map(cb => parseInt(cb.value));

            const updateData = {
                username,
                email,
                full_name: fullName,
                is_active: isActive,
                is_superuser: isSuperuser,
                role_ids: selectedRoles
            };

            // Only include password if it was changed
            if (password) {
                updateData.password = password;
            }

            try {
                const response = await fetch(`/api/users/${userId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updateData)
                });

                if (response.ok) {
                    showToast('User updated successfully', 'success');
                    closeEditUserModal();
                    loadUsersView();
                } else {
                    const error = await response.json();
                    showToast(`Failed to update user: ${error.detail}`, 'error');
                }
            } catch (error) {
                console.error('Error updating user:', error);
                showToast('Failed to update user', 'error');
            }
        });
    } catch (error) {
        console.error('Error loading user details:', error);
        showToast('Failed to load user details', 'error');
    }
}

function closeEditUserModal() {
    const modal = document.getElementById('editUserModal');
    if (modal) {
        modal.remove();
    }
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
