# TransformDash - TODO List

## High Priority

### Authentication & Authorization (Completed)
- [x] Create users and permissions database schema
- [x] Implement JWT authentication with login/logout
- [x] Add role-based access control (RBAC)
- [x] Add permission enforcement to API endpoints - **ALL CRITICAL ENDPOINTS PROTECTED!**
  - [x] Model execution (`/api/execute`, `/api/execute/{model_name}`)
  - [x] Model viewing (`/api/models`, `/api/models/{model_name}/code`)
  - [x] Dataset management (`/api/datasets` - GET/POST/PUT/DELETE)
  - [x] Dataset upload (`/api/datasets/upload-csv`)
  - [x] Chart management (`/api/charts/save`, `/api/charts/{id}` DELETE)
  - [x] User management (`/api/users` - GET/POST/PUT/DELETE)
  - [x] Role management (`/api/roles` - GET)
  - [x] Query execution (`/api/query`, `/api/query/execute`)
- [x] Create user management modals (create/edit users)
- [ ] Create role management modals (create/edit roles with permission assignment)

### Security - CRITICAL
- [x] Fix SQL injection in `/api/filter/values` (ui/app.py:2052-2061)
- [x] Fix SQL injection in `/api/query` (ui/app.py:1683, 1714-1719)
- [x] Fix SQL injection in `/api/query/execute` (SQL Query Lab schema parameter)
- [x] Fix XSS vulnerabilities in users table (users_functions.js:77-88)
- [x] Fix XSS vulnerabilities in roles table (users_functions.js:154-169)
- [x] Add input validation for SQL identifiers (schema, table, column names)
- [x] Add aggregation function whitelist (SUM, AVG, COUNT, MIN, MAX, STDDEV, VARIANCE)
- [ ] Add rate limiting to login endpoint
- [ ] Add file upload validation (type, size limits)

## Medium Priority

### Logging & Monitoring
- [ ] Move server logs from `/tmp/` to `logs/` directory in project
- [ ] Implement log rotation (daily or size-based)
- [ ] Separate log files: `logs/app.log`, `logs/error.log`, `logs/access.log`
- [ ] Add log levels (DEBUG, INFO, WARNING, ERROR)
- [ ] Configure logging in production mode

### Run History Management
- [ ] Implement retention policy for run history (e.g., keep last 30 days)
- [ ] Add cleanup job to delete old run files
- [ ] Consider moving run history from JSON files to PostgreSQL
- [ ] Add compression/archiving for old runs
- [ ] Add UI to configure retention settings

## Low Priority

### UI/UX Improvements
- [x] Improve Users & Permissions page layout and spacing
- [ ] Add dark mode support
- [ ] Improve mobile responsiveness
- [ ] Add keyboard shortcuts

### Performance
- [ ] Add caching for frequently accessed data
- [ ] Optimize large table rendering
- [ ] Add pagination for runs/users/roles

### Documentation
- [ ] Update README with authentication setup
- [ ] Add API documentation
- [ ] Create deployment guide
- [ ] Add troubleshooting section

---
**Last Updated:** 2025-11-17
