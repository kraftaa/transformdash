# TransformDash - TODO List

## High Priority

### Authentication & Authorization (In Progress)
- [x] Create users and permissions database schema
- [x] Implement JWT authentication with login/logout
- [x] Add role-based access control (RBAC)
- [ ] Add permission enforcement to API endpoints
- [ ] Create user management modals (create/edit users)
- [ ] Create role management modals (create/edit roles with permission assignment)

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
