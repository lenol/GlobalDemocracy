# app.py / poc.py
import sqlite3, datetime
from flask import Flask, request, redirect, url_for, render_template_string, abort

app = Flask(__name__)

DB_PATH = "worldvote.db"

NAV = """
<nav style="padding:10px;display:flex;gap:12px;border-bottom:1px solid #ddd;">
  <a href="/charte">charte</a>
  <a href="/vote">vote</a>
  <a href="/propose">propose</a>
  <a href="/results">results</a>
</nav>
"""

LAYOUT = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WorldVote · MVP</title>
<style>
:root{
  --bg:#0b0e14; --card:#141824; --muted:#9aa4b2;
  --text:#e6ebef; --accent:#7dd3fc; --accent-2:#a78bfa; --border:#232838;
  --ok:#34d399; --err:#f87171;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}
.container{max-width:960px;margin:28px auto;padding:0 16px}
header{display:flex;align-items:center;gap:10px;margin:8px 0 12px}
.logo{width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,var(--accent),var(--accent-2));display:inline-block}
h1{font-size:20px;margin:8px 0 14px}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px;margin:12px 0;box-shadow:0 6px 20px rgba(0,0,0,.25)}
.card h2{margin:0 0 8px;font-size:16px}
.muted{color:var(--muted);font-size:13px}
.btn{padding:8px 12px;border:1px solid var(--border);border-radius:10px;background:#1a2030;color:var(--text);cursor:pointer}
.btn:hover{background:#20283a}
.btn-primary{border-color:transparent;background:linear-gradient(135deg,var(--accent),var(--accent-2));color:#0b0e14;font-weight:600}
.btn-primary:hover{opacity:.95}
input[type=text],textarea{width:100%;padding:10px;border-radius:10px;border:1px solid var(--border);background:#0f1420;color:var(--text)}
label{display:block;margin:10px 0 6px}
.radio-row label{display:inline-block;margin-right:14px}
nav.tabs{display:flex;gap:10px;border-bottom:1px solid var(--border);padding-bottom:10px;margin-bottom:16px;flex-wrap:wrap}
nav.tabs a{padding:8px 12px;border:1px solid var(--border);border-bottom:none;border-radius:10px 10px 0 0;background:#111626;color:var(--text);text-decoration:none}
nav.tabs a:hover{background:#151b2b}
nav.tabs a.active{
  background:linear-gradient(135deg,var(--accent),var(--accent-2));
  color:#0b0e14;
  font-weight:700;
  border-color:transparent;
}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;background:#111826;border:1px solid var(--border);font-size:12px;color:var(--muted)}
.ok{color:var(--ok)}
.err{color:var(--err)}
</style>
</head>
<body>
  <div class="container">
    <header>
      <span class="logo"></span>
      <div>
        <div style="font-weight:700">WorldVote</div>
         <div class="muted">vote global — MVP local</div>
      </div>
    </header>

    <nav class="tabs">
    <a href="/charte" class="{{ 'active' if active_tab=='charte' else '' }}">charte</a>
    <a href="/vote" class="{{ 'active' if active_tab=='vote' else '' }}">vote</a>
    <a href="/propose" class="{{ 'active' if active_tab=='propose' else '' }}">propose</a>
    <a href="/results" class="{{ 'active' if active_tab=='results' else '' }}">results</a>
    </nav>


    {{ content|safe }}
  </div>
</body>
</html>"""

def get_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr) or "0.0.0.0"

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        c = conn.cursor()
        # questions
        c.execute("""
        CREATE TABLE IF NOT EXISTS questions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          text TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
        """)
        # options (2 à 5 par question)
        c.execute("""
        CREATE TABLE IF NOT EXISTS options(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          question_id INTEGER NOT NULL,
          text TEXT NOT NULL,
          FOREIGN KEY(question_id) REFERENCES questions(id)
        )
        """)
        # votes (un vote par IP et par question)
        # On (re)crée la table votes proprement pour stocker option_id
        c.execute("""
        CREATE TABLE IF NOT EXISTS votes(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          question_id INTEGER NOT NULL,
          option_id INTEGER NOT NULL,
          voter_ip TEXT NOT NULL,
          created_at TEXT NOT NULL,
          UNIQUE(question_id, voter_ip),
          FOREIGN KEY(question_id) REFERENCES questions(id),
          FOREIGN KEY(option_id) REFERENCES options(id)
        )
        """)
        conn.commit()

@app.after_request
def force_html(resp):
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp

@app.route("/charte")
def charter():
    content = """
    <h1>Charte</h1>
    <div class="card">
      <p>• Vote ouvert, anonyme (limitation par IP en MVP).<br>
         • Pas d’email, pas de pub, pas de tracking perso.<br>
         • Questions proposées librement. Options entre 2 et 5.<br>
         • Résultats publics (SQLite local pour le POC).</p>
      <p class="muted">Ce MVP est local (localhost) pour prototypage.</p>
    </div>
    """
    return render_template_string(LAYOUT, nav=NAV, content=content, active_tab="charte")

@app.route("/")
@app.route("/vote", methods=["GET"])
def vote():
    with db() as conn:
        qs = conn.execute("SELECT * FROM questions ORDER BY id DESC").fetchall()
        items = []
        for q in qs:
            opts = conn.execute("SELECT * FROM options WHERE question_id=? ORDER BY id ASC", (q["id"],)).fetchall()
            if not opts:
                continue
            radios = "".join(
                f'<label><input type="radio" name="option_id" value="{o["id"]}" required> {o["text"]}</label>'
                for o in opts
            )
            items.append(f"""
            <div class="card">
              <div><strong>Q{q['id']}</strong> — {q['text']}</div>
              <form method="POST" action="{url_for('cast_vote', qid=q['id'])}">
                <div style="margin:8px 0">{radios}</div>
                <button class="btn" type="submit">Voter</button>
              </form>
              <div class="muted">Un vote / question / IP.</div>
            </div>
            """)
    content = "<h1>Vote</h1>" + ("\n".join(items) if items else '<p class="muted">Aucune question pour l’instant.</p>')
    return render_template_string(LAYOUT, nav=NAV, content=content, active_tab="vote")

@app.route("/vote/<int:qid>", methods=["POST"])
def cast_vote(qid):
    option_id = request.form.get("option_id")
    if not option_id or not option_id.isdigit():
        abort(400)
    ip = get_ip()
    now = datetime.datetime.utcnow().isoformat()
    with db() as conn:
        q = conn.execute("SELECT id FROM questions WHERE id=?", (qid,)).fetchone()
        if not q:
            abort(404)
        o = conn.execute("SELECT id FROM options WHERE id=? AND question_id=?", (option_id, qid)).fetchone()
        if not o:
            abort(400)
        try:
            conn.execute(
                "INSERT INTO votes(question_id, option_id, voter_ip, created_at) VALUES(?,?,?,?)",
                (qid, int(option_id), ip, now)
            )
            conn.commit()
            msg = f'<p class="ok">Vote enregistré pour Q{qid}.</p>'
        except sqlite3.IntegrityError:
            msg = f'<p class="err">Déjà voté pour Q{qid} depuis votre IP.</p>'
    return redirect(url_for('results', flash=msg))

@app.route("/propose", methods=["GET","POST"])
def propose():
    info = ""
    if request.method == "POST":
        text = (request.form.get("text") or "").strip()
        opts = [(request.form.get(f"opt{i}") or "").strip() for i in range(1,6)]
        # garder seulement les non vides
        opts = [o for o in opts if o]
        errors = []
        if not text:
            errors.append("Texte de la question manquant.")
        if not (2 <= len(opts) <= 5):
            errors.append("Il faut fournir entre 2 et 5 options.")
        for o in opts:
            if len(o) > 25:
                errors.append(f"Option trop longue (>25) : “{o}”")
        if errors:
            info = '<div class="err">' + "<br>".join(errors) + "</div>"
        else:
            with db() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO questions(text, created_at) VALUES(?,?)",
                            (text, datetime.datetime.utcnow().isoformat()))
                qid = cur.lastrowid
                for o in opts:
                    cur.execute("INSERT INTO options(question_id, text) VALUES(?,?)", (qid, o))
                conn.commit()
            return redirect(url_for("vote"))
    # Formulaire sans JS: 5 champs optionnels (on exigera 2 min côté serveur)
    content = f"""
    <h1>Propose</h1>
    <div class="card">
      <form method="POST">
        <label for="text">Question (max 200 caractères)</label><br>
        <input id="text" name="text" type="text" maxlength="200" required><br><br>

        <div class="muted">Options (entre 2 et 5, ≤ 25 caractères chacune) :</div>
        <label>Option 1</label><input type="text" name="opt1" maxlength="25" required>
        <label>Option 2</label><input type="text" name="opt2" maxlength="25" required>
        <label>Option 3</label><input type="text" name="opt3" maxlength="25">
        <label>Option 4</label><input type="text" name="opt4" maxlength="25">
        <label>Option 5</label><input type="text" name="opt5" maxlength="25"><br><br>

        <button class="btn" type="submit">Envoyer</button>
      </form>
      {info}
      <p class="muted">Astuce : laisse vides les options 3–5 si tu n’en as pas besoin.</p>
    </div>
    """
    return render_template_string(LAYOUT, nav=NAV, content=content, active_tab="propose")

@app.route("/results")
def results():
    flash_html = request.args.get("flash","")
    blocks = []
    with db() as conn:
        qs = conn.execute("SELECT * FROM questions ORDER BY id DESC").fetchall()
        for q in qs:
            opts = conn.execute("SELECT * FROM options WHERE question_id=? ORDER BY id ASC", (q["id"],)).fetchall()
            if not opts:
                continue
            counts = dict(conn.execute("""
                SELECT option_id, COUNT(*) AS c FROM votes
                WHERE question_id=? GROUP BY option_id
            """, (q["id"],)).fetchall())
            total = sum(counts.get(o["id"], 0) for o in opts)
            lines = []
            for o in opts:
                c = counts.get(o["id"], 0)
                pct = (100.0*c/total) if total else 0.0
                lines.append(f"{o['text']}: {c} ({pct:.1f}%)")
            block = f"""
            <div class="card">
              <div><strong>Q{q['id']}:</strong> {q['text']}</div>
              <div class="muted">Créée: {q['created_at']}</div>
              <div style="margin-top:6px">{' — '.join(lines)} — TOTAL: {total}</div>
            </div>
            """
            blocks.append(block)
    content = "<h1>Results (historique)</h1>" + flash_html + ("\n".join(blocks) if blocks else '<p class="muted">Aucun résultat pour l’instant.</p>')
    return render_template_string(LAYOUT, nav=NAV, content=content, active_tab="results")

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
