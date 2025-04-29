import os
import sqlite3
import hashlib
import matplotlib.pyplot as plt
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
import requests
from datetime import datetime
import json
import random

# OOP principu izmantošana - klases definīcijas
class User:
    def __init__(self, username, password_hash, role):
        self.username = username
        self.password_hash = password_hash
        self.role = role  # admin vai user
    
    def verify_password(self, password):
        hashed = hashlib.sha256(password.encode()).hexdigest()
        return hashed == self.password_hash
    
    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

class Team:
    def __init__(self, id, name, city, coach):
        self.id = id
        self.name = name
        self.city = city
        self.coach = coach
        self.players = []
    
    def add_player(self, player):
        self.players.append(player)
    
    def get_team_stats(self):
        # Aprēķina komandas vidējo statistiku
        if not self.players:
            return {"avg_points": 0, "avg_blocks": 0, "avg_serves": 0}
        
        avg_points = sum(player.stats.get("points", 0) for player in self.players) / len(self.players)
        avg_blocks = sum(player.stats.get("blocks", 0) for player in self.players) / len(self.players)
        avg_serves = sum(player.stats.get("serves", 0) for player in self.players) / len(self.players)
        
        return {
            "avg_points": round(avg_points, 2),
            "avg_blocks": round(avg_blocks, 2),
            "avg_serves": round(avg_serves, 2)
        }

class Player:
    def __init__(self, id, name, number, position, team_id):
        self.id = id
        self.name = name
        self.number = number
        self.position = position
        self.team_id = team_id
        self.stats = {"points": 0, "blocks": 0, "serves": 0, "games": 0}
    
    def update_stats(self, points, blocks, serves, games=1):
        self.stats["points"] += points
        self.stats["blocks"] += blocks
        self.stats["serves"] += serves
        self.stats["games"] += games
    
    def get_average_stats(self):
        if self.stats["games"] == 0:
            return {"avg_points": 0, "avg_blocks": 0, "avg_serves": 0}
        
        return {
            "avg_points": round(self.stats["points"] / self.stats["games"], 2),
            "avg_blocks": round(self.stats["blocks"] / self.stats["games"], 2),
            "avg_serves": round(self.stats["serves"] / self.stats["games"], 2)
        }

class Match:
    def __init__(self, id, team1_id, team2_id, date, score_team1, score_team2):
        self.id = id
        self.team1_id = team1_id
        self.team2_id = team2_id
        self.date = date
        self.score_team1 = score_team1
        self.score_team2 = score_team2
    
    def get_winner(self):
        if self.score_team1 > self.score_team2:
            return self.team1_id
        elif self.score_team2 > self.score_team1:
            return self.team2_id
        else:
            return None  # Neizšķirts

class Database:
    def __init__(self, db_name='volleyball.db'):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        
    def connect(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        
    def close(self):
        if self.conn:
            self.conn.close()
            
    def execute(self, query, params=()):
        if not self.conn:
            self.connect()
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor
        
    def fetch_all(self, query, params=()):
        if not self.conn:
            self.connect()
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    
    def fetch_one(self, query, params=()):
        if not self.conn:
            self.connect()
        self.cursor.execute(query, params)
        return self.cursor.fetchone()
    
    def initialize_db(self):
        # Izveido tabulas, ja tās neeksistē
        self.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
        ''')
        
        self.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT,
            coach TEXT
        )
        ''')
        
        self.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            number INTEGER,
            position TEXT,
            team_id INTEGER,
            FOREIGN KEY (team_id) REFERENCES teams (id)
        )
        ''')
        
        self.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY,
            team1_id INTEGER,
            team2_id INTEGER,
            date TEXT,
            score_team1 INTEGER,
            score_team2 INTEGER,
            FOREIGN KEY (team1_id) REFERENCES teams (id),
            FOREIGN KEY (team2_id) REFERENCES teams (id)
        )
        ''')
        
        self.execute('''
        CREATE TABLE IF NOT EXISTS player_stats (
            id INTEGER PRIMARY KEY,
            player_id INTEGER,
            match_id INTEGER,
            points INTEGER DEFAULT 0,
            blocks INTEGER DEFAULT 0,
            serves INTEGER DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES players (id),
            FOREIGN KEY (match_id) REFERENCES matches (id)
        )
        ''')
        
        # Pievieno admin lietotāju, ja tas vēl nav izveidots
        admin_exists = self.fetch_one("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",))
        if admin_exists[0] == 0:
            admin_password_hash = User.hash_password("admin123")
            self.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                        ("admin", admin_password_hash, "admin"))
        
        # Pievieno testa datus, ja tabula teams ir tukša
        teams_count = self.fetch_one("SELECT COUNT(*) FROM teams")[0]
        if teams_count == 0:
            self.insert_sample_data()
    
    def insert_sample_data(self):
        # Komandas
        teams = [
            ("Lauvas", "Rīga", "Jānis Bērziņš"),
            ("Tīģeri", "Daugavpils", "Andris Kalniņš"),
            ("Vilki", "Liepāja", "Ieva Liepiņa"),
            ("Lāči", "Ventspils", "Kārlis Ozols")
        ]
        
        for team in teams:
            self.execute("INSERT INTO teams (name, city, coach) VALUES (?, ?, ?)", team)
        
        # Spēlētāji
        players = [
            # Lauvas komanda
            ("Artūrs Zariņš", 7, "Setter", 1),
            ("Mārtiņš Liepa", 9, "Outside Hitter", 1),
            ("Valdis Egle", 12, "Middle Blocker", 1),
            
            # Tīģeri komanda
            ("Pēteris Briedis", 5, "Setter", 2),
            ("Juris Kalns", 8, "Outside Hitter", 2),
            ("Kristaps Lācis", 10, "Middle Blocker", 2),
            
            # Vilki komanda
            ("Raivis Bērziņš", 3, "Setter", 3),
            ("Uldis Priede", 11, "Outside Hitter", 3),
            ("Gatis Kļava", 15, "Middle Blocker", 3),
            
            # Lāči komanda
            ("Oskars Ziemelis", 2, "Setter", 4),
            ("Edgars Linde", 6, "Outside Hitter", 4),
            ("Normunds Kļaviņš", 14, "Middle Blocker", 4)
        ]
        
        for player in players:
            self.execute("INSERT INTO players (name, number, position, team_id) VALUES (?, ?, ?, ?)", player)
        
        # Spēles
        current_date = datetime.now().strftime("%Y-%m-%d")
        matches = [
            (1, 2, current_date, 3, 1),  # Lauvas vs Tīģeri
            (3, 4, current_date, 2, 3),  # Vilki vs Lāči
            (1, 3, current_date, 3, 0),  # Lauvas vs Vilki
            (2, 4, current_date, 1, 3)   # Tīģeri vs Lāči
        ]
        
        for match in matches:
            self.execute("INSERT INTO matches (team1_id, team2_id, date, score_team1, score_team2) VALUES (?, ?, ?, ?, ?)", match)
        
        # Spēlētāju statistika
        # Nejauši ģenerēt statistiku katram spēlētājam katrā spēlē
        for match_id in range(1, 5):
            # Nosaka komandu ID, kas piedalās spēlē
            match_data = self.fetch_one("SELECT team1_id, team2_id FROM matches WHERE id = ?", (match_id,))
            team1_id, team2_id = match_data
            
            # Iegūst spēlētājus no abām komandām
            team1_players = self.fetch_all("SELECT id FROM players WHERE team_id = ?", (team1_id,))
            team2_players = self.fetch_all("SELECT id FROM players WHERE team_id = ?", (team2_id,))
            
            # Pievieno statistiku katram spēlētājam
            for player_id in team1_players + team2_players:
                points = random.randint(0, 15)
                blocks = random.randint(0, 5)
                serves = random.randint(0, 8)
                
                self.execute(
                    "INSERT INTO player_stats (player_id, match_id, points, blocks, serves) VALUES (?, ?, ?, ?, ?)",
                    (player_id[0], match_id, points, blocks, serves)
                )

# API klase sporta datu iegūšanai
class SportsAPI:
    def __init__(self):
        self.base_url = "https://api.example.com/volleyball"  # Šis ir piemēra URL
        self.api_key = "your_api_key"  # Šeit būtu jāievieto īstais API atslēga
    
    def get_recent_matches(self):
        # Reālajā dzīvē šeit būtu API pieprasījums
        # response = requests.get(f"{self.base_url}/matches/recent", headers={"Authorization": f"Bearer {self.api_key}"})
        # return response.json()
        
        # Tā kā šī ir demonstrācija, atgriežam piemēra datus
        return [
            {"team1": "International Team A", "team2": "International Team B", "score": "3-2", "date": "2023-04-20"},
            {"team1": "International Team C", "team2": "International Team D", "score": "3-0", "date": "2023-04-19"},
            {"team1": "International Team E", "team2": "International Team F", "score": "2-3", "date": "2023-04-18"}
        ]
    
    def get_player_info(self, player_name):
        # Reālajā dzīvē šeit būtu API pieprasījums
        # response = requests.get(f"{self.base_url}/players/{player_name}", headers={"Authorization": f"Bearer {self.api_key}"})
        # return response.json()
        
        # Tā kā šī ir demonstrācija, atgriežam piemēra datus
        return {
            "name": player_name,
            "rank": random.randint(1, 100),
            "country": "International",
            "height": f"{random.randint(180, 210)} cm",
            "position": random.choice(["Setter", "Outside Hitter", "Middle Blocker", "Libero"]),
            "career_points": random.randint(1000, 5000)
        }

# Flask lietotne
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Drošai sessiju glabāšanai

# Datubāzes instances izveidošana
db = Database()
db.initialize_db()

# Sports API instances izveidošana
sports_api = SportsAPI()

# Pārbaudīt, vai lietotājs ir autentificēts
def is_authenticated():
    return 'username' in session

# Pārbaudīt, vai lietotājam ir admin tiesības
def is_admin():
    if not is_authenticated():
        return False
    
    user_data = db.fetch_one("SELECT role FROM users WHERE username = ?", (session['username'],))
    if user_data and user_data[0] == 'admin':
        return True
    return False

@app.route('/')
def home():
    if not is_authenticated():
        return redirect(url_for('login'))
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Volejbola Statistikas App</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }
            .container { width: 80%; margin: auto; padding: 20px; }
            .header { background-color: #333; color: white; padding: 20px; text-align: center; }
            .menu { background-color: #444; padding: 10px; margin-bottom: 20px; }
            .menu a { color: white; padding: 10px; text-decoration: none; margin-right: 10px; }
            .menu a:hover { background-color: #555; }
            .content { background-color: white; padding: 20px; border-radius: 5px; }
            .footer { text-align: center; padding: 10px; background-color: #333; color: white; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Volejbola Statistikas Lietotne</h1>
        </div>
        <div class="menu">
            <a href="/teams">Komandas</a>
            <a href="/players">Spēlētāji</a>
            <a href="/matches">Spēles</a>
            <a href="/api-data">API Dati</a>
            <a href="/logout" style="float: right;">Iziet</a>
        </div>
        <div class="container">
            <div class="content">
                <div class="section">
                    <h2>Komandas informācija</h2>
                    <p><strong>Nosaukums:</strong> {{ team_name }}</p>
                    <p><strong>Pilsēta:</strong> {{ team_city }}</p>
                    <p><strong>Treneris:</strong> {{ team_coach }}</p>
                </div>
                
                <div class="section">
                    <h2>Spēlētāji</h2>
                    {% if is_admin %}
                    <p><a href="/player/add/{{ team_id }}" class="btn">Pievienot jaunu spēlētāju</a></p>
                    {% endif %}
                    <table>
                        <tr>
                            <th>Nr.</th>
                            <th>Vārds</th>
                            <th>Pozīcija</th>
                            <th>Spēles</th>
                            <th>Punkti (vid.)</th>
                            <th>Bloki (vid.)</th>
                            <th>Serves (vid.)</th>
                            <th>Darbības</th>
                        </tr>
                        {% for player in players %}
                        <tr>
                            <td>{{ player.number }}</td>
                            <td>{{ player.name }}</td>
                            <td>{{ player.position }}</td>
                            <td>{{ player.games }}</td>
                            <td>{{ player.total_points }} ({{ player.avg_points }})</td>
                            <td>{{ player.total_blocks }} ({{ player.avg_blocks }})</td>
                            <td>{{ player.total_serves }} ({{ player.avg_serves }})</td>
                            <td>
                                <a href="/player/{{ player.id }}" class="btn">Detaļas</a>
                                {% if is_admin %}
                                <a href="/player/edit/{{ player.id }}" class="btn">Rediģēt</a>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>
                
                <div class="section">
                    <h2>Spēles</h2>
                    <table>
                        <tr>
                            <th>Datums</th>
                            <th>Mājinieki</th>
                            <th>Viesi</th>
                            <th>Rezultāts</th>
                            <th>Iznākums</th>
                            <th>Darbības</th>
                        </tr>
                        {% for match in matches %}
                        <tr>
                            <td>{{ match.date }}</td>
                            <td>{{ match.team1_name }}</td>
                            <td>{{ match.team2_name }}</td>
                            <td>{{ match.score }}</td>
                            <td>{{ match.result }}</td>
                            <td>
                                <a href="/match/{{ match.id }}" class="btn">Detaļas</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>
            </div>
        </div>
        <div class="footer">
            &copy; 2023 Volejbola Statistikas Lietotne
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, 
                                team_id=team_id,
                                team_name=name,
                                team_city=city,
                                team_coach=coach,
                                players=players,
                                matches=matches,
                                is_admin=is_admin())

@app.route('/players')
def players():
    if not is_authenticated():
        return redirect(url_for('login'))
    
    players_data = db.fetch_all("""
        SELECT p.id, p.name, p.number, p.position, t.name as team_name, t.id as team_id,
            SUM(ps.points) as total_points, 
            SUM(ps.blocks) as total_blocks, 
            SUM(ps.serves) as total_serves,
            COUNT(DISTINCT ps.match_id) as games_played
        FROM players p
        JOIN teams t ON p.team_id = t.id
        LEFT JOIN player_stats ps ON p.id = ps.player_id
        GROUP BY p.id
        ORDER BY total_points DESC
    """)
    
    players_list = []
    for player_data in players_data:
        player_id, name, number, position, team_name, team_id, points, blocks, serves, games = player_data
        
        # Aprēķina vidējos rādītājus
        avg_points = round(points / games if games > 0 else 0, 2)
        avg_blocks = round(blocks / games if games > 0 else 0, 2)
        avg_serves = round(serves / games if games > 0 else 0, 2)
        
        players_list.append({
            'id': player_id,
            'name': name,
            'number': number,
            'position': position,
            'team_name': team_name,
            'team_id': team_id,
            'total_points': points or 0,
            'total_blocks': blocks or 0,
            'total_serves': serves or 0,
            'games': games or 0,
            'avg_points': avg_points,
            'avg_blocks': avg_blocks,
            'avg_serves': avg_serves
        })
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Spēlētāji - Volejbola Statistikas App</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }
            .container { width: 80%; margin: auto; padding: 20px; }
            .header { background-color: #333; color: white; padding: 20px; text-align: center; }
            .menu { background-color: #444; padding: 10px; margin-bottom: 20px; }
            .menu a { color: white; padding: 10px; text-decoration: none; margin-right: 10px; }
            .menu a:hover { background-color: #555; }
            .content { background-color: white; padding: 20px; border-radius: 5px; }
            .footer { text-align: center; padding: 10px; background-color: #333; color: white; margin-top: 20px; }
            table { width: 100%; border-collapse: collapse; }
            table, th, td { border: 1px solid #ddd; }
            th, td { padding: 12px; text-align: left; }
            th { background-color: #444; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            .btn { padding: 8px 16px; background-color: #4CAF50; color: white; border: none; cursor: pointer; text-decoration: none; }
            .btn:hover { background-color: #45a049; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Volejbola Spēlētāji</h1>
        </div>
        <div class="menu">
            <a href="/">Sākums</a>
            <a href="/teams">Komandas</a>
            <a href="/players">Spēlētāji</a>
            <a href="/matches">Spēles</a>
            <a href="/api-data">API Dati</a>
            <a href="/logout" style="float: right;">Iziet</a>
        </div>
        <div class="container">
            <div class="content">
                <h2>Spēlētāju saraksts</h2>
                {% if is_admin %}
                <p><a href="/player/add" class="btn">Pievienot jaunu spēlētāju</a></p>
                {% endif %}
                <table>
                    <tr>
                        <th>Nr.</th>
                        <th>Vārds</th>
                        <th>Pozīcija</th>
                        <th>Komanda</th>
                        <th>Spēles</th>
                        <th>Punkti (vid.)</th>
                        <th>Bloki (vid.)</th>
                        <th>Serves (vid.)</th>
                        <th>Darbības</th>
                    </tr>
                    {% for player in players %}
                    <tr>
                        <td>{{ player.number }}</td>
                        <td>{{ player.name }}</td>
                        <td>{{ player.position }}</td>
                        <td><a href="/team/{{ player.team_id }}">{{ player.team_name }}</a></td>
                        <td>{{ player.games }}</td>
                        <td>{{ player.total_points }} ({{ player.avg_points }})</td>
                        <td>{{ player.total_blocks }} ({{ player.avg_blocks }})</td>
                        <td>{{ player.total_serves }} ({{ player.avg_serves }})</td>
                        <td>
                            <a href="/player/{{ player.id }}" class="btn">Detaļas</a>
                            {% if is_admin %}
                            <a href="/player/edit/{{ player.id }}" class="btn">Rediģēt</a>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
        <div class="footer">
            &copy; 2023 Volejbola Statistikas Lietotne
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, players=players_list, is_admin=is_admin())

@app.route('/player/<int:player_id>')
def player_details(player_id):
    if not is_authenticated():
        return redirect(url_for('login'))
    
    player_data = db.fetch_one("""
        SELECT p.id, p.name, p.number, p.position, t.name as team_name, t.id as team_id
        FROM players p
        JOIN teams t ON p.team_id = t.id
        WHERE p.id = ?
    """, (player_id,))
    
    if not player_data:
        return "Spēlētājs nav atrasts", 404
    
    player_id, name, number, position, team_name, team_id = player_data
    
    # Iegūst spēlētāja statistiku pa spēlēm
    stats_data = db.fetch_all("""
        SELECT ps.match_id, m.date, t1.name as team1_name, t2.name as team2_name, 
            m.score_team1, m.score_team2, ps.points, ps.blocks, ps.serves
        FROM player_stats ps
        JOIN matches m ON ps.match_id = m.id
        JOIN teams t1 ON m.team1_id = t1.id
        JOIN teams t2 ON m.team2_id = t2.id
        WHERE ps.player_id = ?
        ORDER BY m.date DESC
    """, (player_id,))
    
    stats = []
    total_points = 0
    total_blocks = 0
    total_serves = 0
    games_played = 0
    
    for stat in stats_data:
        match_id, date, team1_name, team2_name, score_team1, score_team2, points, blocks, serves = stat
        
        # Aprēķina kopējo statistiku
        total_points += points or 0
        total_blocks += blocks or 0
        total_serves += serves or 0
        games_played += 1
        
        stats.append({
            'match_id': match_id,
            'date': date,
            'match': f"{team1_name} vs {team2_name}",
            'score': f"{score_team1}-{score_team2}",
            'points': points or 0,
            'blocks': blocks or 0,
            'serves': serves or 0
        })
    
    # Aprēķina vidējos rādītājus
    avg_points = round(total_points / games_played if games_played > 0 else 0, 2)
    avg_blocks = round(total_blocks / games_played if games_played > 0 else 0, 2)
    avg_serves = round(total_serves / games_played if games_played > 0 else 0, 2)
    
    # Iegūst internacionālo statistiku no API
    api_data = sports_api.get_player_info(name)
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ player_name }} - Spēlētāja Detaļas</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }
            .container { width: 80%; margin: auto; padding: 20px; }
            .header { background-color: #333; color: white; padding: 20px; text-align: center; }
            .menu { background-color: #444; padding: 10px; margin-bottom: 20px; }
            .menu a { color: white; padding: 10px; text-decoration: none; margin-right: 10px; }
            .menu a:hover { background-color: #555; }
            .content { background-color: white; padding: 20px; border-radius: 5px; }
            .footer { text-align: center; padding: 10px; background-color: #333; color: white; margin-top: 20px; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
            table, th, td { border: 1px solid #ddd; }
            th, td { padding: 12px; text-align: left; }
            th { background-color: #444; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            .btn { padding: 8px 16px; background-color: #4CAF50; color: white; border: none; cursor: pointer; text-decoration: none; }
            .btn:hover { background-color: #45a049; }
            .section { margin-bottom: 30px; }
            .player-info { display: flex; }
            .player-details { flex: 1; }
            .player-stats { flex: 1; padding-left: 20px; }
            .api-section { background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{{ player_name }} - Spēlētāja Detaļas</h1>
        </div>
        <div class="menu">
            <a href="/">Sākums</a>
            <a href="/teams">Komandas</a>
            <a href="/players">Spēlētāji</a>
            <a href="/matches">Spēles</a>
            <a href="/api-data">API Dati</a>
            <a href="/logout" style="float: right;">Iziet</a>
        </div>
        <div class="container">
            <div class="content">
                <div class="player-info">
                    <div class="player-details">
                        <h2>Spēlētāja informācija</h2>
                        <p><strong>Vārds:</strong> {{ player_name }}</p>
                        <p><strong>Numurs:</strong> {{ player_number }}</p>
                        <p><strong>Pozīcija:</strong> {{ player_position }}</p>
                        <p><strong>Komanda:</strong> <a href="/team/{{ team_id }}">{{ team_name }}</a></p>
                    </div>
                    <div class="player-stats">
                        <h2>Kopējā statistika</h2>
                        <p><strong>Spēles:</strong> {{ games_played }}</p>
                        <p><strong>Kopējie punkti:</strong> {{ total_points }} (vidēji {{ avg_points }} spēlē)</p>
                        <p><strong>Kopējie bloki:</strong> {{ total_blocks }} (vidēji {{ avg_blocks }} spēlē)</p>
                        <p><strong>Kopējās serves:</strong> {{ total_serves }} (vidēji {{ avg_serves }} spēlē)</p>
                    </div>
                </div>
                
                <div class="api-section">
                    <h2>Internacionālā statistika (API dati)</h2>
                    <p><strong>Rangs:</strong> {{ api_data.rank }}</p>
                    <p><strong>Valsts:</strong> {{ api_data.country }}</p>
                    <p><strong>Augums:</strong> {{ api_data.height }}</p>
                    <p><strong>Pozīcija:</strong> {{ api_data.position }}</p>
                    <p><strong>Karjeras punkti:</strong> {{ api_data.career_points }}</p>
                </div>
                
                <div class="section">
                    <h2>Statistika pa spēlēm</h2>
                    <table>
                        <tr>
                            <th>Datums</th>
                            <th>Spēle</th>
                            <th>Rezultāts</th>
                            <th>Punkti</th>
                            <th>Bloki</th>
                            <th>Serves</th>
                        </tr>
                        {% for stat in stats %}
                        <tr>
                            <td>{{ stat.date }}</td>
                            <td>{{ stat.match }}</td>
                            <td>{{ stat.score }}</td>
                            <td>{{ stat.points }}</td>
                            <td>{{ stat.blocks }}</td>
                            <td>{{ stat.serves }}</td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>
                
                <div class="section">
                    <h2>Statistikas vizualizācija</h2>
                    <div id="chart-container">
                        <img src="/player/{{ player_id }}/chart" alt="Spēlētāja statistikas grafiks" width="100%">
                    </div>
                </div>
                
                {% if is_admin %}
                <div class="section">
                    <a href="/player/edit/{{ player_id }}" class="btn">Rediģēt spēlētāju</a>
                    <a href="/player/stats/add/{{ player_id }}" class="btn">Pievienot statistiku</a>
                </div>
                {% endif %}
            </div>
        </div>
        <div class="footer">
            &copy; 2023 Volejbola Statistikas Lietotne
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, 
                                player_id=player_id,
                                player_name=name,
                                player_number=number,
                                player_position=position,
                                team_name=team_name,
                                team_id=team_id,
                                games_played=games_played,
                                total_points=total_points,
                                total_blocks=total_blocks,
                                total_serves=total_serves,
                                avg_points=avg_points,
                                avg_blocks=avg_blocks,
                                avg_serves=avg_serves,
                                stats=stats,
                                api_data=api_data,
                                is_admin=is_admin())

@app.route('/player/<int:player_id>/chart')
def player_chart(player_id):
    if not is_authenticated():
        return redirect(url_for('login'))
    
    # Iegūst spēlētāja statistiku pa spēlēm
    stats_data = db.fetch_all("""
        SELECT ps.match_id, m.date, ps.points, ps.blocks, ps.serves
        FROM player_stats ps
        JOIN matches m ON ps.match_id = m.id
        WHERE ps.player_id = ?
        ORDER BY m.date
    """, (player_id,))
    
    dates = []
    points = []
    blocks = []
    serves = []
    
    for stat in stats_data:
        match_id, date, point, block, serve = stat
        dates.append(date)
        points.append(point or 0)
        blocks.append(block or 0)
        serves.append(serve or 0)
    
    # Izveido grafiku
    plt.figure(figsize=(10, 6))
    plt.plot(dates, points, 'ro-', label='Punkti')
    plt.plot(dates, blocks, 'go-', label='Bloki')
    plt.plot(dates, serves, 'bo-', label='Serves')
    plt.title(f'Spēlētāja statistika pa spēlēm')
    plt.xlabel('Datums')
    plt.ylabel('Vērtība')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Saglabā grafiku atmiņā
    from io import BytesIO
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    
    # Atgriež grafiku
    from flask import send_file
    return send_file(buffer, mimetype='image/png')

@app.route('/matches')
def matches():
    if not is_authenticated():
        return redirect(url_for('login'))
    
    matches_data = db.fetch_all("""
        SELECT m.id, t1.name as team1_name, t2.name as team2_name, 
            m.date, m.score_team1, m.score_team2
        FROM matches m
        JOIN teams t1 ON m.team1_id = t1.id
        JOIN teams t2 ON m.team2_id = t2.id
        ORDER BY m.date DESC
    """)
    
    matches_list = []
    for match in matches_data:
        match_id, team1_name, team2_name, date, score_team1, score_team2 = match
        
        # Nosaka uzvarētāju
        if score_team1 > score_team2:
            winner = team1_name
        elif score_team2 > score_team1:
            winner = team2_name
        else:
            winner = "Neizšķirts"
        
        matches_list.append({
            'id': match_id,
            'team1_name': team1_name,
            'team2_name': team2_name,
            'date': date,
            'score': f"{score_team1} - {score_team2}",
            'winner': winner
        })
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Spēles - Volejbola Statistikas App</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }
            .container { width: 80%; margin: auto; padding: 20px; }
            .header { background-color: #333; color: white; padding: 20px; text-align: center; }
            .menu { background-color: #444; padding: 10px; margin-bottom: 20px; }
            .menu a { color: white; padding: 10px; text-decoration: none; margin-right: 10px; }
            .menu a:hover { background-color: #555; }
            .content { background-color: white; padding: 20px; border-radius: 5px; }
            .footer { text-align: center; padding: 10px; background-color: #333; color: white; margin-top: 20px; }
            table { width: 100%; border-collapse: collapse; }
            table, th, td { border: 1px solid #ddd; }
            th, td { padding: 12px; text-align: left; }
            th { background-color: #444; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            .btn { padding: 8px 16px; background-color: #4CAF50; color: white; border: none; cursor: pointer; text-decoration: none; }
            .btn:hover { background-color: #45a049; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Volejbola Spēles</h1>
        </div>
        <div class="menu">
            <a href="/">Sākums</a>
            <a href="/teams">Komandas</a>
            <a href="/players">Spēlētāji</a>
            <a href="/matches">Spēles</a>
            <a href="/api-data">API Dati</a>
            <a href="/logout" style="float: right;">Iziet</a>
        </div>
        <div class="container">
            <div class="content">
                <h2>Spēļu saraksts</h2>
                {% if is_admin %}
                <p><a href="/match/add" class="btn">Pievienot jaunu spēli</a></p>
                {% endif %}
                <table>
                    <tr>
                        <th>Datums</th>
                        <th>Mājinieki</th>
                        <th>Viesi</th>
                        <th>Rezultāts</th>
                        <th>Uzvarētājs</th>
                        <th>Darbības</th>
                    </tr>
                    {% for match in matches %}
                    <tr>
                        <td>{{ match.date }}</td>
                        <td>{{ match.team1_name }}</td>
                        <td>{{ match.team2_name }}</td>
                        <td>{{ match.score }}</td>
                        <td>{{ match.winner }}</td>
                        <td>
                            <a href="/match/{{ match.id }}" class="btn">Detaļas</a>
                            {% if is_admin %}
                            <a href="/match/edit/{{ match.id }}" class="btn">Rediģēt</a>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
        <div class="footer">
            &copy; 2023 Volejbola Statistikas Lietotne
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, matches=matches_list, is_admin=is_admin())

@app.route('/match/<int:match_id>')
def match_details(match_id):
    if not is_authenticated():
        return redirect(url_for('login'))
    
    match_data = db.fetch_one("""
        SELECT m.id, t1.name as team1_name, t2.name as team2_name, t1.id as team1_id, t2.id as team2_id,
            m.date, m.score_team1, m.score_team2
        FROM matches m
        JOIN teams t1 ON m.team1_id = t1.id
        JOIN teams t2 ON m.team2_id = t2.id
        WHERE m.id = ?
    """, (match_id,))
    
    if not match_data:
        return "Spēle nav atrasta", 404
    
    match_id, team1_name, team2_name, team1_id, team2_id, date, score_team1, score_team2 = match_data
    
    # Nosaka uzvarētāju
    if score_team1 > score_team2:
        winner = team1_name
    elif score_team2 > score_team1:
        winner = team2_name
    else:
        winner = "Neizšķirts"
    
    # Iegūst spēlētāju statistiku šajā spēlē
    team1_stats = db.fetch_all("""
        SELECT p.id, p.name, p.number, ps.points, ps.blocks, ps.serves
        FROM player_stats ps
        JOIN players p ON ps.player_id = p.id
        WHERE ps.match_id = ? AND p.team_id = ?
        ORDER BY ps.points DESC
    """, (match_id, team1_id))
    
    team2_stats = db.fetch_all("""
        SELECT p.id, p.name, p.number, ps.points, ps.blocks, ps.serves
        FROM player_stats ps
        JOIN players p ON ps.player_id = p.id
        WHERE ps.match_id = ? AND p.team_id = ?
        ORDER BY ps.points DESC
    """, (match_id, team2_id))
    
    # Konvertē datus sarakstā
    team1_players = []
    team2_players = []
    
    for stat in team1_stats:
        player_id, name, number, points, blocks, serves = stat
        team1_players.append({
            'id': player_id,
            'name': name,
            'number': number,
            'points': points or 0,
            'blocks': blocks or 0,
            'serves': serves or 0
        })
    
    for stat in team2_stats:
        player_id, name, number, points, blocks, serves = stat
        team2_players.append({
            'id': player_id,
            'name': name,
            'number': number,
            'points': points or 0,
            'blocks': blocks or 0,
            'serves': serves or 0
        })
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Spēles Detaļas - Volejbola Statistikas App</title>
        <style>
            body { font-family: Arial, sans-serif
            <a href="/api-data">API Dati</a>
            <a href="/logout" style="float: right;">Iziet</a>
        </div>
        <div class="container">
            <div class="content">
                <h2>Sveicināti, {{username}}!</h2>
                <p>Šī lietotne ļauj jums aplūkot volejbola komandu, spēlētāju un spēļu statistiku.</p>
                <p>Ko jūs vēlētos darīt šodien?</p>
            </div>
        </div>
        <div class="footer">
            &copy; 2023 Volejbola Statistikas Lietotne
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_data = db.fetch_one("SELECT password_hash FROM users WHERE username = ?", (username,))
        
        if user_data and User.hash_password(password) == user_data[0]:
            session['username'] = username
            return redirect(url_for('home'))
        else:
            error_message = "Nepareizs lietotājvārds vai parole"
            return render_template_string(LOGIN_HTML, error=error_message)
    
    return render_template_string(LOGIN_HTML)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            error_message = "Paroles nesakrīt"
            return render_template_string(REGISTER_HTML, error=error_message)
        
        # Pārbauda, vai lietotājvārds jau eksistē
        user_exists = db.fetch_one("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
        if user_exists[0] > 0:
            error_message = "Lietotājvārds jau eksistē"
            return render_template_string(REGISTER_HTML, error=error_message)
        
        # Reģistrē jaunu lietotāju
        password_hash = User.hash_password(password)
        db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        
        session['username'] = username
        return redirect(url_for('home'))
    
    return render_template_string(REGISTER_HTML)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/teams')
def teams():
    if not is_authenticated():
        return redirect(url_for('login'))
    
    teams_data = db.fetch_all("SELECT id, name, city, coach FROM teams")
    teams_list = []
    
    for team_data in teams_data:
        team_id, name, city, coach = team_data
        
        # Iegūst komandas spēlētāju skaitu
        player_count = db.fetch_one("SELECT COUNT(*) FROM players WHERE team_id = ?", (team_id,))[0]
        
        # Iegūst komandas spēļu rezultātus
        wins = db.fetch_one("""
            SELECT COUNT(*) FROM matches 
            WHERE (team1_id = ? AND score_team1 > score_team2) OR (team2_id = ? AND score_team2 > score_team1)
        """, (team_id, team_id))[0]
        
        losses = db.fetch_one("""
            SELECT COUNT(*) FROM matches 
            WHERE (team1_id = ? AND score_team1 < score_team2) OR (team2_id = ? AND score_team2 < score_team1)
        """, (team_id, team_id))[0]
        
        teams_list.append({
            'id': team_id,
            'name': name,
            'city': city,
            'coach': coach,
            'player_count': player_count,
            'wins': wins,
            'losses': losses
        })
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Komandas - Volejbola Statistikas App</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }
            .container { width: 80%; margin: auto; padding: 20px; }
            .header { background-color: #333; color: white; padding: 20px; text-align: center; }
            .menu { background-color: #444; padding: 10px; margin-bottom: 20px; }
            .menu a { color: white; padding: 10px; text-decoration: none; margin-right: 10px; }
            .menu a:hover { background-color: #555; }
            .content { background-color: white; padding: 20px; border-radius: 5px; }
            .footer { text-align: center; padding: 10px; background-color: #333; color: white; margin-top: 20px; }
            table { width: 100%; border-collapse: collapse; }
            table, th, td { border: 1px solid #ddd; }
            th, td { padding: 12px; text-align: left; }
            th { background-color: #444; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            .btn { padding: 8px 16px; background-color: #4CAF50; color: white; border: none; cursor: pointer; text-decoration: none; }
            .btn:hover { background-color: #45a049; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Volejbola Komandas</h1>
        </div>
        <div class="menu">
            <a href="/">Sākums</a>
            <a href="/teams">Komandas</a>
            <a href="/players">Spēlētāji</a>
            <a href="/matches">Spēles</a>
            <a href="/api-data">API Dati</a>
            <a href="/logout" style="float: right;">Iziet</a>
        </div>
        <div class="container">
            <div class="content">
                <h2>Komandu saraksts</h2>
                {% if is_admin %}
                <p><a href="/team/add" class="btn">Pievienot jaunu komandu</a></p>
                {% endif %}
                <table>
                    <tr>
                        <th>Nosaukums</th>
                        <th>Pilsēta</th>
                        <th>Treneris</th>
                        <th>Spēlētāju skaits</th>
                        <th>Uzvaras</th>
                        <th>Zaudējumi</th>
                        <th>Darbības</th>
                    </tr>
                    {% for team in teams %}
                    <tr>
                        <td>{{ team.name }}</td>
                        <td>{{ team.city }}</td>
                        <td>{{ team.coach }}</td>
                        <td>{{ team.player_count }}</td>
                        <td>{{ team.wins }}</td>
                        <td>{{ team.losses }}</td>
                        <td>
                            <a href="/team/{{ team.id }}" class="btn">Detaļas</a>
                            {% if is_admin %}
                            <a href="/team/edit/{{ team.id }}" class="btn">Rediģēt</a>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
        <div class="footer">
            &copy; 2023 Volejbola Statistikas Lietotne
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, teams=teams_list, is_admin=is_admin())

@app.route('/team/<int:team_id>')
def team_details(team_id):
    if not is_authenticated():
        return redirect(url_for('login'))
    
    team_data = db.fetch_one("SELECT id, name, city, coach FROM teams WHERE id = ?", (team_id,))
    if not team_data:
        return "Komanda nav atrasta", 404
    
    team_id, name, city, coach = team_data
    
    # Iegūst komandas spēlētājus
    players_data = db.fetch_all("""
        SELECT p.id, p.name, p.number, p.position, 
            SUM(ps.points) as total_points, 
            SUM(ps.blocks) as total_blocks, 
            SUM(ps.serves) as total_serves,
            COUNT(DISTINCT ps.match_id) as games_played
        FROM players p
        LEFT JOIN player_stats ps ON p.id = ps.player_id
        WHERE p.team_id = ?
        GROUP BY p.id
    """, (team_id,))
    
    players = []
    for player_data in players_data:
        player_id, player_name, number, position, points, blocks, serves, games = player_data
        
        # Aprēķina vidējos rādītājus
        avg_points = round(points / games if games > 0 else 0, 2)
        avg_blocks = round(blocks / games if games > 0 else 0, 2)
        avg_serves = round(serves / games if games > 0 else 0, 2)
        
        players.append({
            'id': player_id,
            'name': player_name,
            'number': number,
            'position': position,
            'total_points': points or 0,
            'total_blocks': blocks or 0,
            'total_serves': serves or 0,
            'games': games or 0,
            'avg_points': avg_points,
            'avg_blocks': avg_blocks,
            'avg_serves': avg_serves
        })
    
    # Iegūst komandas spēļu informāciju
    matches_data = db.fetch_all("""
        SELECT m.id, t1.name as team1_name, t2.name as team2_name, 
            m.date, m.score_team1, m.score_team2
        FROM matches m
        JOIN teams t1 ON m.team1_id = t1.id
        JOIN teams t2 ON m.team2_id = t2.id
        WHERE m.team1_id = ? OR m.team2_id = ?
    """, (team_id, team_id))
    
    matches = []
    for match_data in matches_data:
        match_id, team1_name, team2_name, date, score_team1, score_team2 = match_data
        
        # Nosaka, vai komanda uzvarēja
        if (team1_name == name and score_team1 > score_team2) or (team2_name == name and score_team2 > score_team1):
            result = "Uzvara"
        elif score_team1 == score_team2:
            result = "Neizšķirts"
        else:
            result = "Zaudējums"
        
        matches.append({
            'id': match_id,
            'team1_name': team1_name,
            'team2_name': team2_name,
            'date': date,
            'score': f"{score_team1} - {score_team2}",
            'result': result
        })