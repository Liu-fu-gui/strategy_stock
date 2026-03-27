import psycopg2

conn = psycopg2.connect(
    host="10.100.20.206",
    port=5432,
    user="stock",
    password="stock123456",
    database="app"
)

cur = conn.cursor()
cur.execute("ALTER TABLE stocks ADD COLUMN IF NOT EXISTS circulating_market_cap NUMERIC(20, 2)")
conn.commit()
cur.close()
conn.close()

print("✓ 市值字段已添加")
