# LinkedIn Post

I just open-sourced TransformDash - a data transformation platform I built after building custom Rust data transformations and working with dbt, Airflow, Airbyte, Superset, Tableau. Wanted a single tool that combines transformation, orchestration, and visualization.

What it does:
- SQL & Python models with Jinja templating
- DAG-based dependency resolution and scheduling (cron-based)
- Built-in dashboards and visualizations
- Works with your existing PostgreSQL database
- No separate warehouse needed

Built with Python (FastAPI backend) and vanilla JavaScript. The authentication system uses JWT with role-based access control, and I spent time making sure the SQL construction is injection-proof using psycopg2's composition tools.

Try it:
```
git clone https://github.com/kraftaa/transformdash
cd transformdash
python -c 'import secrets; print(secrets.token_urlsafe(32))' > jwt_key.txt
export JWT_SECRET_KEY=$(cat jwt_key.txt)
docker-compose up -d
```
Visit http://localhost:8000 (login: admin/admin)

Repo: https://github.com/kraftaa/transformdash

Feedback welcome!

#DataEngineering #OpenSource #Python #dbt #DataTransformation
