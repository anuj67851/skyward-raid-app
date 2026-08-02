import sqlite3
import pandas as pd

DB_NAME = "rosters.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Roster metadata
    c.execute('''CREATE TABLE IF NOT EXISTS rosters
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  raid_date TEXT,
                  general_notes TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Roster members
    c.execute('''CREATE TABLE IF NOT EXISTS roster_members
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  roster_id INTEGER,
                  username TEXT,
                  role TEXT,
                  is_reserve INTEGER DEFAULT 0,
                  player_notes TEXT,
                  FOREIGN KEY (roster_id) REFERENCES rosters(id) ON DELETE CASCADE)''')
    
    conn.commit()
    conn.close()

def save_roster(name, raid_date, general_notes, main_team, reserves):
    """
    main_team: list of dicts {'username': ..., 'role': ..., 'notes': ...}
    reserves: list of dicts {'username': ..., 'role': ..., 'notes': ...}
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        c.execute("INSERT INTO rosters (name, raid_date, general_notes) VALUES (?, ?, ?)",
                  (name, raid_date, general_notes))
        roster_id = c.lastrowid
        
        for player in main_team:
            c.execute("INSERT INTO roster_members (roster_id, username, role, is_reserve, player_notes) VALUES (?, ?, ?, 0, ?)",
                      (roster_id, player['username'], player['role'], player['notes']))
            
        for player in reserves:
            c.execute("INSERT INTO roster_members (roster_id, username, role, is_reserve, player_notes) VALUES (?, ?, ?, 1, ?)",
                      (roster_id, player['username'], player['role'], player['notes']))
        
        conn.commit()
        return roster_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_all_rosters():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM rosters ORDER BY created_at DESC", conn)
    conn.close()
    return df

def get_roster_details(roster_id):
    conn = sqlite3.connect(DB_NAME)
    roster = pd.read_sql_query("SELECT * FROM rosters WHERE id = ?", conn, params=(int(roster_id),))
    members = pd.read_sql_query("SELECT * FROM roster_members WHERE roster_id = ?", conn, params=(int(roster_id),))
    conn.close()
    
    if roster.empty:
        return None, None
    
    main_team = members[members['is_reserve'] == 0]
    reserves = members[members['is_reserve'] == 1]
    
    return roster.iloc[0], (main_team, reserves)

def delete_roster(roster_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM rosters WHERE id = ?", (roster_id,))
    c.execute("DELETE FROM roster_members WHERE roster_id = ?", (roster_id,))
    conn.commit()
    conn.close()
