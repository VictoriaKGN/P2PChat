import sqlite3
import uuid

DB_NAME = 'AppDB.db'

# TODO LOCKS!
class DBManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()

    def init_guid(self, guid):
        try:
            self.conn.execute(f"CREATE TABLE AppInfo (Guid TEXT, Username TEXT)")
            self.conn.execute(f"INSERT INTO AppInfo (Guid) VALUES (?)", (guid, ))
            self.conn.commit()
            result = True
        except sqlite3.Error as e:
            print(e)
            result = False
        return result
    
    def update_username(self, username):
        try:
            self.conn.execute(f"UPDATE AppInfo SET Username = ?", (username, ))
            self.conn.commit()
            result = True
        except sqlite3.Error as e:
            print(e)
            result = False
        return result

    def fetch_app_info(self):
        try:
            table = self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='AppInfo'").fetchone()
            if table:
                result = self.cursor.execute(f"SELECT * FROM AppInfo").fetchone()
            else:
                result = None
        except sqlite3.Error as e:
            print(e)
            result = False
        return result
    
    def get_guid_from_addr(self, addr):
        try:
            row = self.cursor.execute(f"SELECT Guid FROM PeersInfo WHERE Address = ?", (addr, )).fetchone()
            if row:
                result = row[0]
            else:
                result = None
        except sqlite3.Error as e:
            print(e)
            result = False
        return result

    def fetch_peers_info(self):
        print("fetch_peers_info")
        try:
            self.conn.execute(f"CREATE TABLE IF NOT EXISTS PeersInfo (Guid TEXT PRIMARY KEY, Username TEXT, Address TEXT, LastChat DATETIME)")
            self.conn.commit()
            self.cursor.execute(f"SELECT * FROM PeersInfo ORDER BY LastChat DESC")
            result = self.cursor.fetchall()
        except sqlite3.Error as e:
            print(e)
            result = False
        return result
    
    def update_peer_info(self, guid, username, address, last_chat):
        print("update_peers_info")
        try:
            self.conn.execute("INSERT OR REPLACE INTO PeersInfo (Guid, Username, Address, LastChat) VALUES (?, ?, ?, ?)", (guid, username, address, last_chat))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(e)
            result = False
        return result
    
    def update_peer_lastchat(self, guid, last_chat):
        print("update_peer_lastchat")
        try:
            self.conn.execute(f"UPDATE PeersInfo SET LastChat = ? WHERE Guid = ?", (last_chat, guid))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(e)
            result = False
        return result

    def fetch_peer_table(self, table_name):
        print("fetch_peer_table")
        try:
            self.conn.execute(f"CREATE TABLE IF NOT EXISTS \"{table_name}\" (Guid TEXT, Message TEXT)")
            self.conn.execute(f"CREATE TRIGGER IF NOT EXISTS MaxRowsTrigger AFTER INSERT ON \"{table_name}\" BEGIN DELETE FROM \"{table_name}\" WHERE Guid IN (SELECT Guid FROM \"{table_name}\" LIMIT -1 OFFSET 1000); END;")
            self.conn.commit()
            result = self.cursor.execute(f"SELECT * FROM \"{table_name}\"").fetchall()
        except sqlite3.Error as e:
            print(e)
            result = False
        return result
    
    def write_peer_message(self, table_name, sender_id, message):
        print("write_peer_message")
        try:
            self.conn.execute(f"CREATE TABLE IF NOT EXISTS \"{table_name}\" (Guid TEXT, Message TEXT)")
            self.conn.execute(f"CREATE TRIGGER IF NOT EXISTS MaxRowsTrigger AFTER INSERT ON \"{table_name}\" BEGIN DELETE FROM \"{table_name}\" WHERE Guid IN (SELECT Guid FROM \"{table_name}\" LIMIT -1 OFFSET 1000); END;")
            self.conn.commit()
            self.conn.execute(f"INSERT INTO \"{table_name}\" VALUES (?, ?)", (sender_id, message))
            self.conn.commit()
            result = True
        except sqlite3.Error as e:
            print(e)
            result = False
        return result

    def __del__(self):
        self.conn.close()

