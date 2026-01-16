"""
Setup complete visualization database schema
Moves all visualization config from YAML to database tables
"""
from connection_manager import connection_manager

def create_visualization_schema():
    print("🚀 Setting up complete visualization database schema...")
    print("=" * 60)

    with connection_manager.get_connection() as pg:

        # ============================================================
        # 1. DATA CONNECTIONS TABLE
        # ============================================================
        print("\n📦 Creating data_connections table...")
        pg.execute("""
            CREATE TABLE IF NOT EXISTS data_connections (
                id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(500) NOT NULL,
                type VARCHAR(50) NOT NULL DEFAULT 'postgres',
                host VARCHAR(255),
                port INTEGER,
                database_name VARCHAR(255),
                username VARCHAR(255),
                password TEXT,
                config JSONB,
                is_default BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ data_connections table created")

        # ============================================================
        # 2. DASHBOARDS TABLE
        # ============================================================
        print("\n📊 Creating dashboards table...")
        pg.execute("""
            CREATE TABLE IF NOT EXISTS dashboards (
                id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(500) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ dashboards table created")

        # ============================================================
        # 3. DASHBOARD TABS TABLE
        # ============================================================
        print("\n📑 Creating dashboard_tabs table...")
        pg.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_tabs (
                id VARCHAR(255) PRIMARY KEY,
                dashboard_id VARCHAR(255) NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
                name VARCHAR(500) NOT NULL,
                position INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ dashboard_tabs table created")

        # ============================================================
        # 4. CHARTS TABLE (Global)
        # ============================================================
        print("\n📈 Creating charts table...")
        pg.execute("""
            CREATE TABLE IF NOT EXISTS charts (
                id VARCHAR(255) PRIMARY KEY,
                title VARCHAR(500) NOT NULL,
                type VARCHAR(50) NOT NULL,
                model VARCHAR(255) NOT NULL,
                connection_id VARCHAR(255) REFERENCES data_connections(id),
                x_axis VARCHAR(255),
                y_axis VARCHAR(255),
                aggregation VARCHAR(50) DEFAULT 'sum',
                columns JSONB,
                category VARCHAR(255),
                config JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ charts table created")

        # ============================================================
        # 5. DASHBOARD_CHARTS JUNCTION TABLE
        # ============================================================
        print("\n🔗 Creating dashboard_charts junction table...")
        pg.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_charts (
                id SERIAL PRIMARY KEY,
                dashboard_id VARCHAR(255) NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
                chart_id VARCHAR(255) NOT NULL REFERENCES charts(id) ON DELETE CASCADE,
                tab_id VARCHAR(255) REFERENCES dashboard_tabs(id) ON DELETE CASCADE,
                position INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(dashboard_id, chart_id, tab_id)
            )
        """)
        print("   ✅ dashboard_charts table created")

        # ============================================================
        # 6. DASHBOARD FILTERS TABLE
        # ============================================================
        print("\n🔍 Creating dashboard_filters table...")
        pg.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_filters (
                id SERIAL PRIMARY KEY,
                dashboard_id VARCHAR(255) NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
                field VARCHAR(255) NOT NULL,
                label VARCHAR(255) NOT NULL,
                model VARCHAR(255),
                expression TEXT,
                apply_to_tabs TEXT[],
                position INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ dashboard_filters table created")

        # ============================================================
        # 7. CREATE INDEXES
        # ============================================================
        print("\n📇 Creating indexes...")
        pg.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_tabs_dashboard ON dashboard_tabs(dashboard_id)")
        pg.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_charts_dashboard ON dashboard_charts(dashboard_id)")
        pg.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_charts_chart ON dashboard_charts(chart_id)")
        pg.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_charts_tab ON dashboard_charts(tab_id)")
        pg.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_filters_dashboard ON dashboard_filters(dashboard_id)")
        # Note: connection_id index skipped - column may not exist if charts table created by migrations
        # pg.execute("CREATE INDEX IF NOT EXISTS idx_charts_connection ON charts(connection_id)")
        print("   ✅ All indexes created")

        # ============================================================
        # 8. CREATE TRIGGERS
        # ============================================================
        print("\n⚡ Creating update triggers...")
        pg.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql'
        """)

        # Drop existing triggers if any
        pg.execute("DROP TRIGGER IF EXISTS update_dashboards_updated_at ON dashboards")
        pg.execute("DROP TRIGGER IF EXISTS update_charts_updated_at ON charts")
        pg.execute("DROP TRIGGER IF EXISTS update_data_connections_updated_at ON data_connections")

        # Create triggers
        pg.execute("""
            CREATE TRIGGER update_dashboards_updated_at BEFORE UPDATE ON dashboards
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        """)
        pg.execute("""
            CREATE TRIGGER update_charts_updated_at BEFORE UPDATE ON charts
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        """)
        pg.execute("""
            CREATE TRIGGER update_data_connections_updated_at BEFORE UPDATE ON data_connections
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        """)
        print("   ✅ All triggers created")

        # ============================================================
        # 9. MIGRATE EXISTING DATA
        # ============================================================
        print("\n🔄 Migrating existing data...")

        # Migrate connection from .env to data_connections table
        import os
        from dotenv import load_dotenv
        load_dotenv()

        default_connection_id = 'transformdash'
        pg.execute("""
            INSERT INTO data_connections (id, name, type, host, port, database_name, username, password, is_default)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                host = EXCLUDED.host,
                port = EXCLUDED.port,
                database_name = EXCLUDED.database_name,
                username = EXCLUDED.username,
                is_default = EXCLUDED.is_default
        """, (
            default_connection_id,
            'TransformDash DB',
            'postgres',
            os.getenv('DB_HOST', 'localhost'),
            int(os.getenv('DB_PORT', 5432)),
            os.getenv('DB_NAME', 'transformdash'),
            os.getenv('DB_USER', 'postgres'),
            os.getenv('DB_PASSWORD', ''),
            True
        ))
        print(f"   ✅ Migrated default connection: {default_connection_id}")

        # Migrate dashboards from YAML
        import yaml
        from pathlib import Path

        dashboards_file = Path(__file__).parent / "models" / "dashboards.yml"
        if dashboards_file.exists():
            with open(dashboards_file, 'r') as f:
                data = yaml.safe_load(f)

            if data and 'dashboards' in data:
                for dashboard in data['dashboards']:
                    dashboard_id = dashboard.get('id')

                    # Insert dashboard
                    pg.execute("""
                        INSERT INTO dashboards (id, name, description)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            description = EXCLUDED.description
                    """, (
                        dashboard_id,
                        dashboard.get('name', ''),
                        dashboard.get('description', '')
                    ))

                    # Insert tabs
                    for tab in dashboard.get('tabs', []):
                        tab_id = tab.get('id')
                        pg.execute("""
                            INSERT INTO dashboard_tabs (id, dashboard_id, name, position)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE SET
                                name = EXCLUDED.name,
                                position = EXCLUDED.position
                        """, (
                            tab_id,
                            dashboard_id,
                            tab.get('name', ''),
                            tab.get('position', 0)
                        ))

                    # Insert filters
                    position = 0
                    for filter_def in dashboard.get('filters', []):
                        pg.execute("""
                            INSERT INTO dashboard_filters (dashboard_id, field, label, model, expression, apply_to_tabs, position)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            dashboard_id,
                            filter_def.get('field', ''),
                            filter_def.get('label', ''),
                            filter_def.get('model'),
                            filter_def.get('expression'),
                            filter_def.get('apply_to_tabs', []),
                            position
                        ))
                        position += 1

                    print(f"   ✅ Migrated dashboard: {dashboard_id}")

    print("\n" + "=" * 60)
    print("✨ Visualization database setup complete!")
    print("\n📋 Summary:")
    print("   • data_connections - Store database connection configs")
    print("   • dashboards - Dashboard definitions")
    print("   • dashboard_tabs - Tabs for organizing charts")
    print("   • charts - Global chart library")
    print("   • dashboard_charts - Chart assignments to dashboards/tabs")
    print("   • dashboard_filters - Dashboard filters")
    print("\n🎯 All visualization config is now in the database!")

if __name__ == "__main__":
    create_visualization_schema()
