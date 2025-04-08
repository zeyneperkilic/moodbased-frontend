from flask import Flask, render_template, request
import requests


app = Flask(__name__)

import os
API_URL = "https://moodbasedmusicrec.onrender.com"

import sqlite3

def init_db():
    conn = sqlite3.connect('feedback.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        track_id TEXT,
        cluster_id INTEGER,
        comment TEXT,
        intensity TEXT,
        sentiment REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()


def add_feedback_sqlite(track_id, cluster_id, comment, intensity, sentiment):
    conn = sqlite3.connect('feedback.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO feedback (track_id, cluster_id, comment, intensity, sentiment)
        VALUES (?, ?, ?, ?, ?)
    ''', (track_id, cluster_id, comment, intensity, sentiment))
    conn.commit()
    conn.close()
    
@app.route('/')
def home():
    return render_template('cover.html')

@app.route('/mood-selection')
def mood_selection():
    return render_template('mood_selection.html')

@app.route('/mood-map/<color>')
def mood_map(color):
    color = color.lower()
    color_to_cluster = {
        "black": 0,  # sad
        "yellow": 1,  # happy
        "red": 2,     # energetic
        "green": 3    # calm
    }

    if color not in color_to_cluster:
        return "Invalid color", 400

    cluster_id = color_to_cluster[color]

    # İlgili mood'un 1000 şarkısını getiriyoruz
    response = requests.get(f"{API_URL}/clusters/{cluster_id}?limit=1000")
    songs = response.json().get("songs", []) if response.status_code == 200 else []

    return render_template(
        "mood_map.html",
        mood_name=color.capitalize(),
        mood_color=color,
        cluster_id=cluster_id,
        songs=songs,
        all_songs=songs  # İlk durumda 1000 şarkı da buraya gelsin
    )

@app.route('/recommend', methods=['GET'])
def recommend():
    cluster_id = request.args.get("cluster_id")
    intensity = request.args.get("intensity")

    if not cluster_id or not intensity:
        return "Missing parameters", 400

    response = requests.get(f"{API_URL}/recommend/{cluster_id}?intensity={intensity}")
    songs = response.json().get("songs", []) if response.status_code == 200 else []

    # Cluster renklendirmesi için mapping
    cluster_to_color = { "0": "black", "1": "yellow", "2": "red", "3": "green" }
    mood_color = cluster_to_color.get(str(cluster_id), "gray")

    return render_template(
        "mood_map.html",
        mood_name="Recommended Songs",
        mood_color=mood_color,   # burası önemli
        cluster_id=cluster_id,
        songs=songs,
        all_songs=songs
    )

@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    track_id = request.form.get("track_id")
    cluster_id = int(request.form.get("cluster_id"))
    comment = request.form.get("comment")
    intensity = request.form.get("intensity", "5")
    sentiment = float(request.form.get("sentiment", 0))  # bu backend tahmini olabilir

    add_feedback_sqlite(track_id, cluster_id, comment, intensity, sentiment)
    return redirect(f"/mood-map/{request.form.get('mood_color')}")
@app.route('/feedback')
def feedback():
    conn = sqlite3.connect('feedback.db')
    c = conn.cursor()
    c.execute('SELECT track_id, comment, cluster_id, sentiment, intensity, created_at FROM feedback ORDER BY created_at DESC')
    feedback_list = c.fetchall()
    conn.close()
    return render_template('feedback.html', feedback_list=feedback_list)


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001, debug=True)
