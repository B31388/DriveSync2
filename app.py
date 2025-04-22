from flask import Flask
from core import core

app = Flask(__name__)
app.secret_key = 'drivesync_secret_key'  # Required for session management
app.register_blueprint(core)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)