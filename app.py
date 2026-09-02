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
                DO $$                BEGIN                     IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user' AND column_name='role') THEN                         ALTER TABLE "user" ADD COLUMN role VARCHAR(50) DEFAULT 'Гост';                     END IF;                     IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='photo' AND column_name='photo_date') THEN                         ALTER TABLE photo ADD COLUMN photo_date VARCHAR(50) DEFAULT 'Неизвестна';                     END IF;                     IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='photo' AND column_name='photo_type') THEN                         ALTER TABLE photo ADD COLUMN photo_type VARCHAR(100) DEFAULT 'Градски транспорт';                     END IF;                     IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='photo' AND column_name='location') THEN                         ALTER TABLE photo ADD COLUMN location VARCHAR(100) DEFAULT 'Неизвестна';                     END IF;                     IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='photo' AND column_name='vehicle_type') THEN                         ALTER TABLE photo ADD COLUMN vehicle_type VARCHAR(100) DEFAULT 'Автобус';                     END IF;                     IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='photo' AND column_name='inventory_number') THEN                         ALTER TABLE photo ADD COLUMN inventory_number VARCHAR(50) DEFAULT '';                     END IF;                     IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='photo' AND column_name='comment') THEN                         ALTER TABLE photo ADD COLUMN comment TEXT DEFAULT '';                     END IF;                     IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='photo' AND column_name='is_author') THEN                         ALTER TABLE photo ADD COLUMN is_author BOOLEAN DEFAULT TRUE;                     END IF;                 END $$;
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
    dev_user = User.query.filter(
        (User.username == 's1llyy') | (User.role == 'Web Developer')
    ).first()
    
    other_members = User.query.filter(
        User.role != 'Гост',
        User.role != 'Web Developer',
        User.username != 's1llyy'
    ).all()
    
    return render_template('team.html', dev_user=dev_user, other_members=other_members)

@app.route('/gallery')
def gallery():
    approved_photos = Photo.query.filter_by(status='Approved').order_by(Photo.created_at.desc()).all()
    return render_template('gallery.html', photos=approved_photos)

@app.route('/apply', methods=['GET', 'POST'])
@login_required
def apply():
    existing = Application.query.filter_by(username=current_user.username, status='Pending').first()
    if existing:
        flash('Вече имате подадена активна кандидатура!', 'warning')
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        age = request.form.get('age')
        experience = request.form.get('experience')
        
        if not age or not experience:
            flash('Моля, попълнете всички полета!', 'danger')
            return redirect(request.url)
            
        new_app = Application(
            username=current_user.username,
            age=int(age),
            experience=experience,
            status='Pending'
        )
        db.session.add(new_app)
        db.session.commit()
        
        flash('Кандидатурата ви е изпратена успешно!', 'success')
        return redirect(url_for('home'))
        
    return render_template('apply.html')

@app.route('/upload-photos', methods=['GET', 'POST'], endpoint='upload_photos')
@app.route('/upload-photo', methods=['GET', 'POST'], endpoint='upload_photo')
@login_required
def upload_photos():
    if request.method == 'POST':
        if 'photo' not in request.files:
            flash('Няма избрана снимка!', 'danger')
            return redirect(request.url)
        
        file = request.files['photo']
        if file.filename == '':
            flash('Не е избран файл!', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            day = request.form.get('day', '').strip()
            month = request.form.get('month', '').strip()
            year = request.form.get('year', '').strip()
            date_unknown = request.form.get('date_unknown')
            
            if date_unknown or not (day or month or year):
                photo_date = 'Неизвестна'
            else:
                photo_date = f"{day}.{month}.{year}".strip('.')
                
            photo_type = request.form.get('photo_type', 'Градски транспорт')
            location = request.form.get('location', '').strip() or 'Неизвестна'
            vehicle_type = request.form.get('vehicle_type', 'Автобус')
            inventory_number = request.form.get('inventory_number', '').strip()
            comment = request.form.get('comment', '').strip()
            is_author = True if request.form.get('is_author') else False
            
            new_photo = Photo(
                filename=filename,
                uploader_username=current_user.username,
                photo_date=photo_date,
                photo_type=photo_type,
                location=location,
                vehicle_type=vehicle_type,
                inventory_number=inventory_number,
                comment=comment,
                is_author=is_author,
                status='Pending'
            )
            db.session.add(new_photo)
            db.session.commit()
            
            flash('Снимката е изпратена успешно за одобрение!', 'success')
            return redirect(url_for('my_photos'))
        else:
            flash('Невалиден формат на файла!', 'danger')
            
    return render_template('upload_photos.html')

@app.route('/my-photos', endpoint='my_photos')
@login_required
def my_photos():
    photos = Photo.query.filter_by(uploader_username=current_user.username).order_by(Photo.created_at.desc()).all()
    return render_template('my_photos.html', photos=photos)

@app.route('/approve-photos', endpoint='approve_photos')
@login_required
def approve_photos():
    if not is_chief_admin():
        flash('Нямате достъп до тази страница!', 'danger')
        return redirect(url_for('home'))
    pending_photos = Photo.query.filter_by(status='Pending').all()
    return render_template('approve_photos.html', photos=pending_photos)

@app.route('/approve/<int:photo_id>', endpoint='approve_photo_action')
@login_required
def approve_photo_action(photo_id):
    if not is_chief_admin():
        return redirect(url_for('home'))
    photo = Photo.query.get_or_404(photo_id)
    photo.status = 'Approved'
    db.session.commit()
    flash('Снимката е одобрена!', 'success')
    return redirect(url_for('approve_photos'))

@app.route('/reject/<int:photo_id>', endpoint='reject_photo_action')
@login_required
def reject_photo_action(photo_id):
    if not is_chief_admin():
        return redirect(url_for('home'))
    photo = Photo.query.get_or_404(photo_id)
    db.session.delete(photo)
    db.session.commit()
    flash('Снимката е отхвърлена и изтрита.', 'info')
    return redirect(url_for('approve_photos'))

@app.route('/admin', methods=['GET', 'POST'], endpoint='admin')
@login_required
def admin():
    if not is_chief_admin():
        flash('Нямате права за административния панел!', 'danger')
        return redirect(url_for('home'))
    applications = Application.query.filter_by(status='Pending').all()
    users = User.query.all()
    return render_template('admin.html', applications=applications, users=users)

@app.route('/update-role/<int:user_id>/<role>', endpoint='update_role')
@login_required
def update_role(user_id, role):
    if not is_chief_admin():
        return redirect(url_for('home'))
    user = User.query.get_or_404(user_id)
    if user.username == 's1llyy':
        flash('Ролята на главния разработчик не може да бъде променяна!', 'danger')
        return redirect(url_for('admin'))
    
    valid_roles = ['Гост', 'Шофьор', 'Диспечер', 'Администратор', 'Главен Администратор']
    if role in valid_roles:
        user.role = role
        user.is_admin = (role in ['Администратор', 'Главен Администратор'])
        db.session.commit()
        flash(f'Ролята на {user.username} беше променена на {role}.', 'success')
    return redirect(url_for('admin'))

@app.route('/delete-user/<int:user_id>', methods=['POST'], endpoint='delete_user')
@login_required
def delete_user(user_id):
    if not is_chief_admin():
        flash('Нямате права да изтривате потребители!', 'danger')
        return redirect(url_for('admin'))
    
    user_to_delete = User.query.get_or_404(user_id)
    if user_to_delete.username == 's1llyy':
        flash('Главният разработчик не може да бъде изтрит!', 'danger')
        return redirect(url_for('admin'))
    
    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f'Потребителят {user_to_delete.username} беше изтрит успешно.', 'success')
    return redirect(url_for('admin'))

@app.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Успешен вход!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Грешно потребителско име или парола!', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'], endpoint='register')
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Потребителското име вече е заето!', 'danger')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, role='Гост')
        db.session.add(new_user)
        db.session.commit()
        
        flash('Успешна регистрация! Моля влезте в профила си.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout', endpoint='logout')
@login_required
def logout():
    logout_user()
    flash('Излязохте от профила си.', 'info')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
