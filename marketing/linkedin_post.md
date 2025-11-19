# LinkedIn Post

I just open-sourced TransformDash - a data transformation platform I built to solve a problem I kept running into: needing dbt's elegant SQL transformations but without the overhead of a full data warehouse setup.

What it does:
- dbt-style SQL models with Jinja templating both SQL & python models
- DAG-based dependency resolution
- Built-in dashboards and visualizations
- Works with your existing PostgreSQL database (MongoDB/Redis - WIP)
- No separate warehouse needed

Built with Python (FastAPI backend) and vanilla JavaScript. The authentication system uses JWT with role-based access control, and I spent time making sure the SQL construction is injection-proof using psycopg2's composition tools.

Check it out: https://github.com/kraftaa/transformdash

It's still rough around the edges, but it works. Feedback welcome.

#DataEngineering #OpenSource #Python #dbt #DataTransformation
