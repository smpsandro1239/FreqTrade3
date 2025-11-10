from flask import Flask
from flask_socketio import SocketIO
from .routes import api
from .sockets import start_update_thread
from .database import init_database
from dotenv import load_dotenv
import os

load_dotenv()

socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    app = Flask(__name__, template_folder='../frontend/templates')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')

    app.register_blueprint(api)

    # Initialize extensions
    socketio.init_app(app)

    # Initialize database
    with app.app_context():
        init_database()

    # Start background tasks
    start_update_thread()

    return app