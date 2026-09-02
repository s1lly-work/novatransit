import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import text

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nova_transit_secret_key'

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db_url = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(50), default='Гост')

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    experience = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    uploader_username = db.Column(db.String(50), nullable=False)
    photo_date = db.Column(db.String(50), default='Неизвестна')
    photo_type = db.Column(db.String(100), default='Градски транспорт')
    location = db.Column(db.String(100), default='Неизвестна')
    vehicle_type = db.Column(db.String(100), default='Автобус')
    inventory_number = db.Column(db.String(50), default='')
    comment = db.Column(db.Text, default='')
    is_author = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    try:
        with db.engine.connect() as conn:
            conn.execute(text("""ALTER TABLE "user" ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'Гост';"""))
            conn.execute(text("""UPDATE "user" SET role = 'Web Developer', is_admin = True WHERE username = 's1llyy';"""))
            conn.commit()
    except Exception as e:
        print(f"Migration error: {e}")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def is_chief_admin():
    return current_user.is_authenticated and (
        current_user.role in ['Главен Администратор', 'Web Developer'] or current
