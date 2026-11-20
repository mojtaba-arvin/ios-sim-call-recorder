# Apply ordered SQL migrations once, recording each committed version.
from __future__ import annotations
import os
from pathlib import Path
import psycopg

def main():
    dsn=os.environ.get('DATABASE_URL','').strip()
    if not dsn: raise SystemExit('DATABASE_URL is required')
    migrations=Path(__file__).parent/'migrations'
    with psycopg.connect(dsn) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())')
        applied={row[0] for row in conn.execute('SELECT version FROM schema_migrations').fetchall()}
        for path in sorted(migrations.glob('*.sql')):
            if path.name in applied: continue
            sql=path.read_text(encoding='utf-8')
            with conn.transaction():
                conn.execute(sql)
                conn.execute('INSERT INTO schema_migrations(version) VALUES (%s)',(path.name,))
            print(f'applied {path.name}')

if __name__=='__main__': main()
