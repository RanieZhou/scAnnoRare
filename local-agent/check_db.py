import sqlite3
db = r'C:\Users\Z3183\AppData\Roaming\scAnnoRare\workspace\jobs\jobs.sqlite'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('Tables:', c.fetchall())
c.execute("PRAGMA table_info(jobs)")
print('Schema:', c.fetchall())
c.execute("SELECT * FROM jobs ORDER BY rowid DESC LIMIT 10")
rows = c.fetchall()
for r in rows:
    print(r)
conn.close()
