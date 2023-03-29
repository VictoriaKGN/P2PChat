import sqlite3

DB_NAME = 'AppDB.db'

# TODO LOCKS!
class DBManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.cursor = self.conn.cursor()

    def init_guid(self, guid):
        try:
            self.conn.execute(f"CREATE TABLE AppGuid (Guid TEXT)")
            self.conn.execute(f"INSERT INTO AppGuid (Guid) VALUES (?)", (guid, ))
            self.conn.commit()
            result = True
        except sqlite3.Error as e:
            print(e)
            result = False
        return result

    def fetch_guid(self):
        try:
            table = self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='AppGuid'").fetchone()
            if table:
                result = self.cursor.execute(f"SELECT Guid FROM AppGuid").fetchone()[0]
            else:
                result = None
        except sqlite3.Error as e:
            print(e)
            result = False
        return result

    def fetch_peers_info(self):
        try:
            self.cursor.row_factory = sqlite3.Row
            self.conn.execute(f"CREATE TABLE IF NOT EXISTS PeersInfo (Guid TEXT PRIMARY KEY, Username TEXT, Address TEXT, LastChat DATETIME)")
            self.conn.commit()
            self.cursor.execute(f"SELECT * FROM PeersInfo ORDER BY LastChat DESC")
            rows = self.cursor.fetchall()
            result = {row['Guid']: [row[col] for col in row.keys() if col != 'Guid'] for row in rows}
            self.cursor.row_factory = None
        except sqlite3.Error as e:
            print(e)
            result = False
        return result
    
    def update_peer_info(self, guid, username, address, last_chat):
        pass

    def fetch_peer_table(self, table_name):
        try:
            self.conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (Guid TEXT, Message TEXT)")
            self.conn.commit()
            result = self.cursor.execute(f"SELECT * FROM {table_name}")
        except sqlite3.Error as e:
            print(e)
            result = False
        return result
    
    # TODO check for max size of rows
    def write_peer_message(self, table_name, sender_id, message):
        try:
            self.conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (Guid TEXT, Message TEXT)")
            self.conn.commit()
            self.conn.execute(f"INSERT INTO {table_name} VALUES (?, ?)", (sender_id, message))
            self.conn.commit()
            result = True
        except sqlite3.Error as e:
            print(e)
            result = False
        return result

    def __del__(self):
        self.conn.close()

