from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return """<!doctype html>
<html lang="fr">
<head><meta charset="utf-8"><title>Test</title></head>
<body>
<h1 style='color:blue'>Test HTML rendu</h1>
<p>Si tu vois ce texte en bleu, Chrome interprète bien le HTML.</p>
</body>
</html>"""

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
