import os
import sqlite3

dirname = os.path.dirname(__file__)
data_file = os.path.join(dirname, 'rules.db')

conn = sqlite3.connect(data_file)
cursor = conn.cursor()

cursor.execute('''UPDATE data SET mutable=0''')

conn.commit()
conn.close()