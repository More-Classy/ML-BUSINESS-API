#!/usr/bin/env python3
"""
Script to run the chat tables migration
Usage: python run_migration.py
"""
import asyncio
import aiomysql
from pathlib import Path
import sys
import os

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import settings

async def run_migration():
    """Run the SQL migration script"""
    sql_file = Path(__file__).parent / "create_chat_tables.sql"
    
    if not sql_file.exists():
        print(f"Error: Migration file not found at {sql_file}")
        return False
    
    # Read SQL file
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    try:
        # Connect to database
        conn = await aiomysql.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            db=settings.DATABASE_NAME,
            autocommit=False
        )
        
        cursor = await conn.cursor()
        
        # Execute SQL script (split by semicolons for multiple statements)
        statements = [s.strip() for s in sql_script.split(';') if s.strip() and not s.strip().startswith('--')]
        
        for statement in statements:
            if statement:
                try:
                    await cursor.execute(statement)
                    print(f"✓ Executed: {statement[:50]}...")
                except Exception as e:
                    # Ignore "table already exists" errors
                    if "already exists" in str(e).lower():
                        print(f"⚠ Table already exists, skipping...")
                    else:
                        print(f"✗ Error executing statement: {e}")
                        raise
        
        await conn.commit()
        print("\n✅ Migration completed successfully!")
        
        await cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_migration())
    sys.exit(0 if success else 1)
