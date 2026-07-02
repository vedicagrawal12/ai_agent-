import psycopg2

def migrate():
    try:
        conn = psycopg2.connect(
            dbname="leadhunter_db",
            user="postgres",
            password="",  # Assuming no password for local dev, or it's standard
            host="localhost",
            port=5432
        )
        cur = conn.cursor()
        cur.execute("ALTER TABLE leads ADD COLUMN whatsapp_reply_received BOOLEAN DEFAULT FALSE;")
        conn.commit()
        print("Successfully added whatsapp_reply_received to leads.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Migration failed or already applied: {e}")

if __name__ == "__main__":
    migrate()
