import psycopg2

conn = psycopg2.connect(
    dbname = "Database Name",
    user = "postgres",
    password = "*****",
    host = "localhost",
    port = "5432"
)
cur = conn.cursor()

cur.execute("SELECT * FROM points")
rows = cur.fetchall()

for row in rows:
    print(row)

cur.close()
conn.close()