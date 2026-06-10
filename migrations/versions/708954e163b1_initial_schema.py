"""initial_schema

Revision ID: 708954e163b1
Revises: 
Create Date: 2026-06-10 18:21:22.309358

"""
from typing import Sequence, Union

# pyrefly: ignore [missing-import]
from alembic import op
# pyrefly: ignore [missing-import]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '708954e163b1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(255) DEFAULT '',
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Leads table
    op.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id SERIAL PRIMARY KEY,
            place_id VARCHAR(255),
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            phone VARCHAR(50) DEFAULT '',
            address TEXT DEFAULT '',
            website TEXT DEFAULT '',
            rating REAL DEFAULT 0.0,
            reviews INTEGER DEFAULT 0,
            category VARCHAR(255) DEFAULT '',
            city VARCHAR(255) DEFAULT '',
            priority VARCHAR(50) DEFAULT 'LOW',
            whatsapp_number VARCHAR(50) DEFAULT '',
            source VARCHAR(100) DEFAULT 'google_maps',
            contacted BOOLEAN DEFAULT FALSE,
            contact_date TIMESTAMP DEFAULT NULL,
            notes TEXT DEFAULT '',
            instagram VARCHAR(255) DEFAULT '',
            facebook VARCHAR(255) DEFAULT '',
            custom_pitch TEXT DEFAULT '',
            is_broken_website BOOLEAN DEFAULT FALSE,
            line_type VARCHAR(100) DEFAULT '',
            pipeline_stage VARCHAR(100) DEFAULT 'NEW',
            email VARCHAR(255) DEFAULT '',
            remind_date DATE DEFAULT NULL,
            remind_status VARCHAR(100) DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT leads_place_id_user_id_key UNIQUE (place_id, user_id)
        )
    """)
    # Search history table
    op.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            query TEXT NOT NULL,
            city VARCHAR(255) NOT NULL,
            results_count INTEGER DEFAULT 0,
            leads_count INTEGER DEFAULT 0,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Message log table
    op.execute("""
        CREATE TABLE IF NOT EXISTS message_log (
            id SERIAL PRIMARY KEY,
            lead_id INTEGER,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            template_used VARCHAR(255) DEFAULT '',
            message_sent TEXT DEFAULT '',
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
        )
    """)
    # Indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_leads_user_id ON leads(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_leads_city ON leads(city)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_leads_priority ON leads(priority)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_leads_pipeline ON leads(pipeline_stage)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_leads_contacted ON leads(contacted)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_leads_remind ON leads(remind_status, remind_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_search_user_id ON search_history(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_search_date ON search_history(searched_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_msglog_lead ON message_log(lead_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_msglog_user ON message_log(user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS message_log CASCADE")
    op.execute("DROP TABLE IF EXISTS search_history CASCADE")
    op.execute("DROP TABLE IF EXISTS leads CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
