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
            conn.execute(text("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user' AND column_name='role') THEN
                        ALTER TABLE "user" ADD COLUMN role VARCHAR(50) DEFAULT 'Гост';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='photo' AND column_name='photo_date') THEN
                        ALTER TABLE photo ADD COLUMN photo_date VARCHAR(50) DEFAULT 'Неизвестна';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='photo' AND column_name='photo_type') THEN
                        ALTER TABLE photo ADD COLUMN photo_type VARCHAR(100) DEFAULT 'Градски транспорт';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='photo' AND column_name='location') THEN
                        ALTER TABLE photo ADD COLUMN location VARCHAR(100) DEFAULT 'Неизвестна';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='photo' AND column_name='vehicle_type') THEN
                        ALTER TABLE photo ADD COLUMN vehicle_type VARCHAR(100) DEFAULT 'Автобус';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='photo' AND column_name='inventory_number') THEN
                        ALTER TABLE photo ADD COLUMN inventory_number VARCHAR(50) DEFAULT '';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='photo' AND column_name='comment') THEN
                        ALTER TABLE photo ADD COLUMN comment TEXT DEFAULT '';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='photo' AND column_name='is_author') THEN
                        ALTER TABLE photo ADD COLUMN is_author BOOLEAN DEFAULT TRUE;
                    END IF;
                END $$;
            """))
            conn.execute(text("""UPDATE "user" SET role = 'Web Developer', is_admin = True WHERE username = 's1llyy';"""))
            conn.commit()
    except Exception as e:
        print(f"Migration notice: {e}")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def is_chief_admin():
    if not current_user.is_authenticated:
        return False
    return current_user.role in ['Главен Администратор', 'Web Developer'] or current_user.username == 's1llyy'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/team')
def team():
    return render_template('team.html')

@app.route('/gallery')
def gallery():
    approved_photos = Photo.query.filter_by(status='Approved').order_by(Photo.created_at.desc()).all()
    return render_template('gallery.html', photos=approved_photos)

@app.route('/upload-photo', methods=['GET', 'POST'])
@login_required
def upload_photo():
    if request.method == 'POST':
        if 'photo' not in request.files:
            flash('Няма избрана снимка!', 'danger')
            return redirect(request.url)
        
        file = request.files['photo']
        if file.filename == '' or not allowed_file(file.filename):
            flash('Невалиден формат на файла!', 'danger')
            return redirect(request.url)

        filename = secure_filename(f"{datetime.utcnow().timestamp()}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        day = request.form.get('day', '')
        month = request.form.get('month', '')
        year = request.form.get('year', '')
        date_unknown = request.form.get('date_unknown')

        if date_unknown:
            photo_date = "Неизвестна"
        elif day and month and year:
            photo_date = f"{day}.{month}.{year}"
        else:
            photo_date = "Неизвестна"

        new_photo = Photo(
            filename=filename,
            uploader_username=current_user.username,
            photo_date=photo_date,
            photo_type=request.form.get('photo_type', 'Градски транспорт'),
            location=request.form.get('location', 'Неизвестна'),
            vehicle_type=request.form.get('vehicle_type', 'Автобус'),
            inventory_number=request.form.get('inventory_number', ''),
            comment=request.form.get('comment', ''),
            is_author=True if request.form.get('is_author') else False,
            status='Pending'
        )
        db.session.add(new_photo)
        db.session.commit()

        flash('Снимката е изпратена за одобрение от Главен Администратор!', 'success')
        return redirect(url_for('gallery'))

    return render_template('upload_photos.html')

@app.route('/upload-photos', methods=['GET', 'POST'])
@login_required
def upload_photos():
    return upload_photo()

@app.route('/my-photos')
@login_required
def my_photos():
    if is_chief_admin():
        user_photos = Photo.query.order_by(Photo.created_at.desc()).all()
    else:
        user_photos = Photo.query.filter_by(uploader_username=current_user.username).order_by(Photo.created_at.desc()).all()
        
    return render_template('my_photos.html', photos=user_photos)

@app.route('/approve-photos')
@login_required
def approve_photos():
    if not is_chief_admin():
        flash('Нямате права за достъп до тази страница!', 'danger')
        return redirect(url_for('home'))

    pending_photos = Photo.query.filter_by(status='Pending').order_by(Photo.created_at.desc()).all()
    return render_template('approve_photos.html', photos=pending_photos)

@app.route('/approve-photos/action/<int:photo_id>/<string:action>')
@login_required
def photo_action(photo_id, action):
    if not is_chief_admin():
        flash('Нямате права за това действие!', 'danger')
        return redirect(url_for('home'))

    photo = db.session.get(Photo, photo_id)
    if not photo:
        flash('Снимката не е намерена!', 'danger')
        return redirect(url_for('approve_photos'))

    if action == 'approve':
        photo.status = 'Approved'
        flash('Снимката е одобрена и добавена в галерията!', 'success')
    elif action == 'reject':
        photo.status = 'Rejected'
        flash('Снимката е отхвърлена.', 'info')

    db.session.commit()
    return redirect(url_for('approve_photos'))

@app.route('/apply', methods=['GET', 'POST'])
@login_required
def apply():
    existing_app = Application.query.filter_by(username=current_user.username, status='Pending').first()
    if existing_app:
        flash('Вече имате активна кандидатура!', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        new_app = Application(
            username=current_user.username,
            age=int(request.form.get('age', 18)),
            experience=request.form.get('experience', '')
        )
        db.session.add(new_app)
        db.session.commit()
        flash('Кандидатурата е изпратена успешно!', 'success')
        return redirect(url_for('home'))

    return render_template('apply.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            flash('Успешен вход!', 'success')
            return redirect(url_for('home'))
        flash('Грешно потребителско име или парола.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        if User.query.filter_by(username=username).first():
            flash('Потребителското име е заето.', 'danger')
            return redirect(url_for('register'))

        hashed_pwd = generate_password_hash(request.form.get('password'), method='scrypt')
        is_admin = True if username == 's1llyy' else False
        role = 'Web Developer' if username == 's1llyy' else 'Гост'

        new_user = User(username=username, password=hashed_pwd, is_admin=is_admin, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash('Регистрацията е успешна!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin and not is_chief_admin():
        flash('Нямате достъп!', 'danger')
        return redirect(url_for('home'))
    
    applications = Application.query.all()
    users = User.query.all()
    return render_template('admin.html', applications=applications, users=users)

@app.route('/admin/set_role/<int:user_id>/<string:new_role>')
@app.route('/admin/set_role/<int:user_id>/<string:role>')
@app.route('/set_role/<int:user_id>/<string:new_role>')
@app.route('/set_role/<int:user_id>/<string:role>')
@login_required
def set_role(user_id, new_role=None, role=None):
    if not current_user.is_admin and not is_chief_admin():
        return redirect(url_for('home'))
    
    target_role = new_role or role
    target_user = db.session.get(User, user_id)
    if not target_user:
        flash('Потребителят не е намерен!', 'danger')
        return redirect(url_for('admin_panel'))

    if target_user.username == 's1llyy':
        flash('Не може да променяте главния разработчик!', 'danger')
        return redirect(url_for('admin_panel'))

    valid_roles = ['Гост', 'Шофьор', 'Диспечер', 'Администратор', 'Главен Администратор']
    if target_role in valid_roles:
        target_user.role = target_role
        target_user.is_admin = True if target_role in ['Администратор', 'Главен Администратор'] else False
        db.session.commit()
        flash(f'Ролята е променена на {target_role}!', 'success')

    return redirect(url_for('admin_panel'))

@app.route('/rules')
def rules():
    return render_template('index.html')

@app.route('/news')
def news():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
