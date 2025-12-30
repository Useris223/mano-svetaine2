from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html lang="lt">
    <head>
        <meta charset="UTF-8">
        <title>Mano Python svetainė</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #0f172a;
                color: white;
                text-align: center;
                padding-top: 100px;
            }
            h1 {
                font-size: 48px;
            }
            p {
                font-size: 20px;
                color: #cbd5f5;
            }
        </style>
    </head>
    <body>
        <h1>🚀 Sveiki!</h1>
        <p>Mano pirma Python + Flask svetainė</p>
        <p>Ji veikia ir yra vieša 🌍</p>
    </body>
    </html>
    """

# ŠITA DALIS LABAI SVARBI
if __name__ == "__main__":
    app.run()
