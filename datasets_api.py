"""
Datasets API Endpoints
Handles CRUD operations for datasets
"""
import logging
import json
import re
from fastapi import HTTPException, Request
from connection_manager import connection_manager
from psycopg2 import sql


def validate_sql_identifier(name: str, field_name: str) -> str:
    """Validate that a string is a safe SQL identifier (alphanumeric + underscore only)"""
    if not name:
        return name
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}: must start with a letter or underscore and contain only letters, numbers, and underscores"
        )
    return name


async def get_all_datasets():
    """Get all datasets from the database"""
    try:
        logging.info("Fetching all datasets from database")

        with connection_manager.get_connection() as pg:
            datasets_data = pg.execute("""
                SELECT
                    d.id,
                    d.name,
                    d.description,
                    d.connection_id,
                    d.source_type,
                    d.table_name,
                    d.sql_query,
                    d.schema_name,
                    d.columns,
                    d.filters,
                    d.config,
                    d.file_path,
                    d.original_filename,
                    d.file_size_bytes,
                    d.created_at,
                    d.updated_at
                FROM datasets d
                ORDER BY d.created_at DESC
            """, fetch=True)

            all_datasets = []
            if datasets_data:
                for dataset in datasets_data:
                    dataset_dict = {
                        'id': dataset['id'],
                        'name': dataset['name'],
                        'description': dataset['description'],
                        'connection_id': dataset['connection_id'],
                        'source_type': dataset['source_type'],
                        'table_name': dataset['table_name'],
                        'sql_query': dataset['sql_query'],
                        'schema_name': dataset['schema_name'],
                        'columns': dataset['columns'] if dataset['columns'] else [],
                        'filters': dataset['filters'] if dataset['filters'] else [],
                        'config': dataset['config'] if dataset['config'] else {},
                        'file_path': dataset.get('file_path'),
                        'original_filename': dataset.get('original_filename'),
                        'file_size_bytes': dataset.get('file_size_bytes'),
                        'created_at': str(dataset['created_at']) if dataset['created_at'] else None,
                        'updated_at': str(dataset['updated_at']) if dataset['updated_at'] else None
                    }
                    all_datasets.append(dataset_dict)

            logging.info(f"Fetched {len(all_datasets)} datasets from database")
            return {"datasets": all_datasets}

    except Exception as e:
        import traceback
        logging.error(f"Error fetching datasets: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_dataset_by_id(dataset_id: str):
    """Get a single dataset by ID"""
    try:
        logging.info(f"Fetching dataset: {dataset_id}")

        with connection_manager.get_connection() as pg:
            dataset_data = pg.execute("""
                SELECT
                    d.id,
                    d.name,
                    d.description,
                    d.connection_id,
                    d.source_type,
                    d.table_name,
                    d.sql_query,
                    d.schema_name,
                    d.columns,
                    d.filters,
                    d.config,
                    d.file_path,
                    d.original_filename,
                    d.file_size_bytes,
                    d.created_at,
                    d.updated_at
                FROM datasets d
                WHERE d.id = %s
            """, (dataset_id,), fetch=True)

            if not dataset_data or len(dataset_data) == 0:
                raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")

            dataset = dataset_data[0]
            dataset_dict = {
                'id': dataset['id'],
                'name': dataset['name'],
                'description': dataset['description'],
                'connection_id': dataset['connection_id'],
                'source_type': dataset['source_type'],
                'table_name': dataset['table_name'],
                'sql_query': dataset['sql_query'],
                'schema_name': dataset['schema_name'],
                'columns': dataset['columns'] if dataset['columns'] else [],
                'filters': dataset['filters'] if dataset['filters'] else [],
                'config': dataset['config'] if dataset['config'] else {},
                'file_path': dataset.get('file_path'),
                'original_filename': dataset.get('original_filename'),
                'file_size_bytes': dataset.get('file_size_bytes'),
                'created_at': str(dataset['created_at']) if dataset['created_at'] else None,
                'updated_at': str(dataset['updated_at']) if dataset['updated_at'] else None
            }

            return {"dataset": dataset_dict}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error fetching dataset {dataset_id}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


async def create_dataset(request: Request):
    """Create a new dataset"""
    try:
        body = await request.json()
        logging.info(f"Creating dataset: {body}")

        # Extract dataset fields
        dataset_id = body.get("id")
        name = body.get("name")
        description = body.get("description", "")
        connection_id = body.get("connection_id")
        source_type = body.get("source_type", "table")  # 'table' or 'sql'
        table_name = body.get("table_name")
        sql_query = body.get("sql_query")
        schema_name = body.get("schema_name")
        columns = body.get("columns", [])
        filters = body.get("filters", [])
        config = body.get("config", {})

        # Validation
        if not dataset_id or not name:
            raise HTTPException(status_code=400, detail="Missing required fields: id, name")

        if source_type == "table" and not table_name:
            raise HTTPException(status_code=400, detail="table_name is required when source_type is 'table'")

        if source_type == "sql" and not sql_query:
            raise HTTPException(status_code=400, detail="sql_query is required when source_type is 'sql'")

        with connection_manager.get_connection() as pg:
            # Insert the dataset
            pg.execute("""
                INSERT INTO datasets (
                    id, name, description, connection_id,
                    source_type, table_name, sql_query, schema_name,
                    columns, filters, config
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                dataset_id,
                name,
                description,
                connection_id,
                source_type,
                table_name,
                sql_query,
                schema_name,
                json.dumps(columns) if columns else None,
                json.dumps(filters) if filters else None,
                json.dumps(config) if config else None
            ))

            logging.info(f"Dataset {dataset_id} created successfully")
            return {
                "success": True,
                "message": f"Dataset '{name}' created successfully",
                "dataset_id": dataset_id
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error creating dataset: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


async def update_dataset(dataset_id: str, request: Request):
    """Update an existing dataset"""
    try:
        body = await request.json()
        logging.info(f"Updating dataset {dataset_id}: {body}")

        # Extract fields to update
        name = body.get("name")
        description = body.get("description")
        connection_id = body.get("connection_id")
        source_type = body.get("source_type")
        table_name = body.get("table_name")
        sql_query = body.get("sql_query")
        schema_name = body.get("schema_name")
        columns = body.get("columns")
        filters = body.get("filters")
        config = body.get("config")

        with connection_manager.get_connection() as pg:
            # Check if dataset exists
            existing = pg.execute(
                "SELECT id FROM datasets WHERE id = %s",
                (dataset_id,),
                fetch=True
            )

            if not existing or len(existing) == 0:
                raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")

            # Update the dataset
            pg.execute("""
                UPDATE datasets SET
                    name = COALESCE(%s, name),
                    description = COALESCE(%s, description),
                    connection_id = COALESCE(%s, connection_id),
                    source_type = COALESCE(%s, source_type),
                    table_name = COALESCE(%s, table_name),
                    sql_query = COALESCE(%s, sql_query),
                    schema_name = COALESCE(%s, schema_name),
                    columns = COALESCE(%s, columns),
                    filters = COALESCE(%s, filters),
                    config = COALESCE(%s, config),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                name,
                description,
                connection_id,
                source_type,
                table_name,
                sql_query,
                schema_name,
                json.dumps(columns) if columns is not None else None,
                json.dumps(filters) if filters is not None else None,
                json.dumps(config) if config is not None else None,
                dataset_id
            ))

            logging.info(f"Dataset {dataset_id} updated successfully")
            return {
                "success": True,
                "message": f"Dataset updated successfully",
                "dataset_id": dataset_id
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error updating dataset {dataset_id}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


async def delete_dataset(dataset_id: str):
    """Delete a dataset"""
    try:
        logging.info(f"Deleting dataset: {dataset_id}")

        with connection_manager.get_connection() as pg:
            # Check if dataset exists
            existing = pg.execute(
                "SELECT id, name FROM datasets WHERE id = %s",
                (dataset_id,),
                fetch=True
            )

            if not existing or len(existing) == 0:
                raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")

            dataset_name = existing[0]['name']

            # Check if any charts reference this dataset
            charts_using = pg.execute(
                "SELECT COUNT(*) as count FROM charts WHERE dataset_id = %s",
                (dataset_id,),
                fetch=True
            )

            charts_count = charts_using[0]['count'] if charts_using else 0

            if charts_count > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot delete dataset '{dataset_name}'. It is used by {charts_count} chart(s). Please delete or reassign those charts first."
                )

            # Delete the dataset
            pg.execute("DELETE FROM datasets WHERE id = %s", (dataset_id,))

            logging.info(f"Dataset {dataset_id} deleted successfully")
            return {
                "success": True,
                "message": f"Dataset '{dataset_name}' deleted successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error deleting dataset {dataset_id}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


async def preview_dataset(request: Request):
    """Preview data from a dataset (execute query and return sample rows)"""
    try:
        body = await request.json()
        logging.info(f"Previewing dataset data")

        connection_id = body.get("connection_id")
        source_type = body.get("source_type", "table")
        table_name = body.get("table_name")
        sql_query = body.get("sql_query")
        schema_name = body.get("schema_name", "public")
        filters = body.get("filters", [])
        limit = body.get("limit", 100)  # Default to 100 rows

        # Validate limit is a positive integer within bounds
        if not isinstance(limit, int) or limit < 1 or limit > 10000:
            raise HTTPException(status_code=400, detail="limit must be an integer between 1 and 10000")

        # Build the query based on source type
        if source_type == "table":
            if not table_name:
                raise HTTPException(status_code=400, detail="table_name is required")

            # Validate identifiers to prevent SQL injection
            validate_sql_identifier(schema_name, "schema_name")
            validate_sql_identifier(table_name, "table_name")

            # Build query safely using psycopg2.sql module
            if schema_name:
                query = sql.SQL("SELECT * FROM {schema}.{table} LIMIT {limit}").format(
                    schema=sql.Identifier(schema_name),
                    table=sql.Identifier(table_name),
                    limit=sql.Literal(limit)
                )
            else:
                query = sql.SQL("SELECT * FROM {table} LIMIT {limit}").format(
                    table=sql.Identifier(table_name),
                    limit=sql.Literal(limit)
                )

            # Apply filters if any
            if filters:
                # TODO: Implement filter logic with parameterized queries
                pass

        elif source_type == "sql":
            # Direct SQL execution is disabled for security
            raise HTTPException(
                status_code=403,
                detail="Direct SQL execution is disabled for security. Use table-based datasets instead."
            )

        else:
            raise HTTPException(status_code=400, detail=f"Invalid source_type: {source_type}")

        # Execute the query
        # TODO: Use the specified connection_id to get the right connection
        with connection_manager.get_connection() as pg:
            results = pg.execute(query, fetch=True)

            # Convert to list of dicts
            data = []
            columns = []

            if results and len(results) > 0:
                # Get column names from first row
                columns = list(results[0].keys())

                # Convert rows to dicts
                for row in results:
                    data.append(dict(row))

            return {
                "success": True,
                "columns": columns,
                "data": data,
                "row_count": len(data)
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error previewing dataset: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
