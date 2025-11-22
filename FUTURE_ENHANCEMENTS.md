# TransformDash - Future Enhancements

This document tracks planned features and improvements for TransformDash.

## Priority 1: Authentication & Authorization

### User Management System
- [ ] **User Registration & Login**
  - Email/password authentication
  - OAuth integration (Google, GitHub, Microsoft)
  - Password reset functionality
  - Email verification

- [ ] **Role-Based Access Control (RBAC)**
  - **Admin Role**: Full system access
    - Manage users and roles
    - Configure system settings
    - View all dashboards and models
    - Execute transformations

  - **Developer Role**: Data development access
    - Create/edit models
    - Run transformations
    - View all dashboards
    - Access logs and lineage

  - **Analyst Role**: Read-only dashboard access
    - View dashboards and charts
    - Export data (PDF, CSV, Excel)
    - Apply filters
    - No model editing or execution

  - **Viewer Role**: Limited read access
    - View specific dashboards only
    - No export capabilities
    - No access to models or lineage

- [ ] **Permissions System**
  - Dashboard-level permissions (who can view which dashboards)
  - Model-level permissions (who can edit which models)
  - Execution permissions (who can run transformations)
  - Export permissions (who can download data)

- [ ] **User Interface Components**
  - Login/logout pages
  - User profile management
  - Admin panel for user management
  - Role assignment interface
  - Permission matrix editor

### Implementation Notes
- Use JWT tokens for session management
- Store user data in PostgreSQL
- Hash passwords with bcrypt
- Implement middleware for route protection
- Add audit logging for security events

---

## Priority 2: View Toggle (List/Table)

### List vs. Table View for All Content
- [ ] **Run History View Toggle**
  - Card view (current): Expandable cards with details
  - Table view: Sortable data table with columns
    - Columns: Run ID, Status, Time, Success Rate, Duration, Actions
    - Inline expand for logs

- [ ] **Models View Toggle**
  - Card view (current): Visual cards with badges
  - Table view: Sortable/filterable table
    - Columns: Name, Layer, Type, Dependencies, Last Updated, Actions
    - Quick actions: View Code, Edit, Delete

- [ ] **Dashboards View Toggle**
  - Card view (current): Expandable dashboard cards
  - Table view: Dashboard list with metadata
    - Columns: Name, Description, Charts Count, Last Modified, Actions
    - Quick actions: Open, Edit, Export

- [ ] **Charts View Toggle**
  - Grid view (current): Visual chart previews
  - Table view: Chart metadata table
    - Columns: Title, Type, Table, Created, Actions

### Implementation
- Add toggle button in header: `[List] [Table]`
- Save preference in localStorage
- CSS classes: `.view-list` and `.view-table`
- Data table library: Use DataTables.js or TanStack Table

---

## Priority 3: UI/UX Improvements

- [ ] **Keyboard Shortcuts**
  - `Ctrl+K`: Global search
  - `Ctrl+D`: Toggle dark mode
  - `Ctrl+R`: Refresh current view
  - `Esc`: Close modals/collapse expanded items

- [ ] **Drag & Drop**
  - Reorder dashboards
  - Reorder charts within dashboards
  - Drag models to create dependencies

- [ ] **Advanced Filtering**
  - Multi-select filters
  - Date range pickers
  - Custom filter combinations
  - Save filter presets

- [ ] **Real-time Updates**
  - WebSocket connection for live run progress
  - Real-time log streaming
  - Live dashboard updates
  - Notification system

---

## Priority 4: Advanced Analytics

- [ ] **Performance Metrics**
  - Model execution time trends
  - Query performance analysis
  - Data freshness indicators
  - Resource usage tracking

- [ ] **Data Quality Monitoring**
  - Row count tracking
  - Null value detection
  - Schema change alerts
  - Data validation rules

- [ ] **Alerting System**
  - Email/Slack notifications for failures
  - Threshold-based alerts
  - Scheduled reports
  - Custom alert rules

---

## Priority 5: Developer Experience

- [ ] **Model Editor**
  - In-browser SQL editor with syntax highlighting
  - Auto-completion for tables/columns
  - Query validation
  - Test query functionality

- [ ] **Version Control Integration**
  - Git integration for model files
  - Diff viewer for model changes
  - Commit history
  - Branch/PR support

- [ ] **Collaboration Features**
  - Comments on models and dashboards
  - @mentions for team members
  - Activity feed
  - Share links with permissions

---

## Priority 6: Data Management

- [ ] **Data Catalog**
  - Browse all tables/columns
  - Column-level lineage
  - Data dictionary
  - Tag/categorize tables

- [ ] **Metadata Management**
  - Add descriptions to models/dashboards
  - Add owners to datasets
  - Add tags for discovery
  - Document transformations

- [ ] **Data Preview**
  - Quick sample data view
  - Column statistics
  - Data profiling
  - Export samples

---

## Priority 7: Deployment & Ops

- [ ] **Scheduling**
  - Cron-style scheduling for transformations
  - Dependency-aware scheduling
  - Retry policies
  - Schedule calendar view

- [ ] **CI/CD Integration**
  - GitHub Actions workflows
  - Automated testing
  - Deployment pipelines
  - Environment management

- [ ] **Monitoring & Logging**
  - Application metrics (Prometheus)
  - Distributed tracing
  - Error tracking (Sentry)
  - Performance profiling

---

## Priority 8: Mobile & API

- [ ] **Mobile-Responsive Design**
  - Touch-friendly interface
  - Mobile navigation
  - Optimized charts for mobile
  - Offline mode

- [ ] **REST API**
  - OpenAPI/Swagger documentation
  - API authentication (API keys)
  - Rate limiting
  - Webhook support

- [ ] **Public Dashboards**
  - Share dashboards publicly
  - Embed dashboards in websites
  - Custom branding for embeds
  - Access analytics

---

## Quick Wins (Easy Implementation)

- [ ] Keyboard navigation for lists
- [ ] Bulk actions (delete multiple runs, export multiple dashboards)
- [ ] Recent items history
- [ ] Favorites/bookmarks
- [ ] Custom color themes
- [ ] Dashboard templates
- [ ] Quick filters bar
- [ ] Column hiding/showing in tables
- [ ] Export preferences
- [ ] Compact/comfortable view density

---

##  Notes

- Features are prioritized based on user impact and implementation complexity
- Authentication system should be implemented first for security
- View toggles provide immediate UX improvement
- Consider user feedback when prioritizing features

---

**Last Updated**: 2025-10-20
**Maintained By**: TransformDash Development Team
