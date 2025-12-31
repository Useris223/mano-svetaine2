# app.py
import os
from datetime import datetime
from flask import Flask, render_template

app = Flask(__name__)

DISCORD_INVITE = os.environ.get("DISCORD_INVITE", "https://discord.gg/PAKEISK_SITA")
NOTICE_TEXT = os.environ.get("NOTICE_TEXT", "⚠️ Svetainė kuriama (beta).")

@app.get("/")
def home():
    return render_template(
        "index.html",
        title="Svetainė",
        year=datetime.now().year,
        discord_invite=DISCORD_INVITE,
        notice_text=NOTICE_TEXT,
    )

if __name__ == "__main__":
    app.run(debug=True)
