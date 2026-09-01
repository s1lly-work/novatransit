import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nova_transit_secret_key'

db_url = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url

SUPER_ADMIN_USERNAME = 's1llyy'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    roblox_username = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    experience = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

BUSES_DATA = [
    {"title": "Solaris Urbino 12 III", "image": "8566.png", "category": "u12-iii"},
    {"title": "Solaris Urbino 12 IV", "image": "8571.png", "category": "u12-iv"},
    {"title": "Solaris Urbino 18 III", "image": "8658.png", "category": "u18-iii"},
    {"title": "Solaris Urbino 18 III", "image": "8698.png", "category": "u18-iii"},
    {"title": "Solaris Urbino 12 III", "image": "8703.png", "category": "u12-iii"},
    {"title": "Solaris Urbino 12 III", "image": "8574.png", "category": "u12-iii"},
    {"title": "Solaris Urbino 12 III", "image": "8599.png", "category": "u12-iii"},
    {"title": "Solaris Urbino 18 III", "image": "8538.png", "category": "u18-iii"},
    {"title": "Solaris Urbino 12 IV", "image": "8601.png", "category": "u12-iv"},
    {"title": "Solaris Urbino 12 III", "image": "0231.png", "category": "u12-iii"},
    {"title": "Solaris Urbino 12 III", "image": "8665.png", "category": "u12-iii"},
    {"title": "Solaris Urbino 18 III", "image": "8550.png", "category": "u18-iii"},
]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/gallery')
def gallery():
    selected_model = request.args.get('model', 'all')
    if selected_model == 'all':
        filtered_buses = BUSES_DATA
    else:
        filtered_buses = [b for b in BUSES_DATA if b['category'] == selected_model]
    return render_template('gallery.html', buses=filtered_buses, selected_model=selected_model)

@app.route('/apply', methods=['GET', 'POST'])
@login_required
def apply():
    existing_app = Application.query.filter_by(username=current_user.username, status='Pending').first()
    if existing_app:
        flash('Вече имате активна кандидатура, която изчаква преглед!', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        roblox_username = request.form.get('roblox_username')
        age = request.form.get('age')
        experience = request.form.get('experience')

        new_app = Application(
            username=current_user.username,
            roblox_username=roblox_username,
            age=int(age),
            experience=experience
        )
        db.session.add(new_app)
        db.session.commit()
        flash('Кандидатурата е изпратена успешно!', 'success')
        return redirect(url_for('home'))

    return render_template('apply.html')

@app.route('/login', methods=['GET', 'POST'])
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
            flash('Грешно потребителско име или парола.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Това потребителско име вече е заето.', 'danger')
            return redirect(url_for('register'))

        hashed_pwd = generate_password_hash(password, method='scrypt')
        is_admin_user = True if username == 's1llyy' else False

        new_user = User(username=username, password=hashed_pwd, is_admin=is_admin_user)
        db.session.add(new_user)
        db.session.commit()
        flash('Регистрацията е успешна! Можете да влезете.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Излязохте от профила си.', 'info')
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('Нямате достъп до тази страница!', 'danger')
        return redirect(url_for('home'))
    
    applications = Application.query.all()
    users = User.query.all()
    return render_template('admin.html', applications=applications, users=users)

@app.route('/admin/action/<int:app_id>/<string:action>')
@login_required
def application_action(app_id, action):
    if not current_user.is_admin:
        return redirect(url_for('home'))
    
    app_item = Application.query.get_or_404(app_id)
    if action == 'approve':
        app_item.status = 'Approved'
    elif action == 'reject':
        app_item.status = 'Rejected'
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/toggle_admin/<int:user_id>')
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin:
        return redirect(url_for('home'))
    
    target_user = User.query.get_or_404(user_id)
    
    if target_user.username == 's1llyy':
        flash('Правата на Главния администратор не могат да бъдат променяни!', 'danger')
        return redirect(url_for('admin_panel'))
        
    target_user.is_admin = not target_user.is_admin
    db.session.commit()
    flash('Правата бяха обновени успешно!', 'success')
    return redirect(url_for('admin_panel'))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
