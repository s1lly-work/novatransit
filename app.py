from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nova_transit_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

SUPER_ADMIN_USERNAME = 's1llyy'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    experience = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/gallery')
def gallery():
    model = request.args.get('model', 'all')

    all_buses = [
        {'title': 'Solaris Urbino 12 III', 'image': '8571.png', 'category': 'u12-iii'},
        {'title': 'Solaris Urbino 12 IV', 'image': '0229.png', 'category': 'u12-iv'},
        {'title': 'Solaris Urbino 18 III', 'image': '8703.png', 'category': 'u18-iii'},
        {'title': 'Solaris Urbino 18 III', 'image': '8665.png', 'category': 'u18-iii'},
        {'title': 'Solaris Urbino 12 III', 'image': '8566.png', 'category': 'u12-iii'},
        {'title': 'Solaris Urbino 12 III', 'image': '8538.png', 'category': 'u12-iii'},
        {'title': 'Solaris Urbino 12 III', 'image': '8599.png', 'category': 'u12-iii'},
        {'title': 'Solaris Urbino 18 III', 'image': '8692.png', 'category': 'u18-iii'},
        {'title': 'Solaris Urbino 12 IV', 'image': '0231.png', 'category': 'u12-iv'},
        {'title': 'Solaris Urbino 12 III', 'image': '8574.png', 'category': 'u12-iii'},
        {'title': 'Solaris Urbino 12 III', 'image': '8590.png', 'category': 'u12-iii'},
        {'title': 'Solaris Urbino 12 III', 'image': '8658.png', 'category': 'u12-iii'},
        {'title': 'Solaris Urbino 18 III', 'image': '8691.png', 'category': 'u18-iii'},
    ]

    if model != 'all':
        buses = [b for b in all_buses if b['category'] == model]
    else:
        buses = all_buses

    return render_template('gallery.html', buses=buses, selected_model=model)

@app.route('/apply', methods=['GET', 'POST'])
@login_required
def apply():
    existing_application = Application.query.filter_by(user_id=current_user.id, status='Pending').first()

    if request.method == 'POST':
        if existing_application:
            flash('Вече имате активна кандидатура!', 'error')
            return redirect(url_for('apply'))

        name = request.form.get('name')
        experience = request.form.get('experience')

        new_app = Application(name=name, experience=experience, user_id=current_user.id)
        db.session.add(new_app)
        db.session.commit()
        flash('Кандидатурата е изпратена успешно!', 'success')
        return redirect(url_for('home'))

    return render_template('apply.html', has_pending_application=bool(existing_application))

@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('Нямате достъп до тази страница!', 'error')
        return redirect(url_for('home'))
    
    applications = Application.query.all()
    users = User.query.all()
    return render_template('admin.html', applications=applications, users=users)

@app.route('/toggle_admin/<int:user_id>')
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin:
        flash('Нямате достъп!', 'error')
        return redirect(url_for('home'))
    
    user = User.query.get_or_404(user_id)

    if user.username == SUPER_ADMIN_USERNAME:
        flash('Правата на главния администратор не могат да бъдат променяни!', 'error')
        return redirect(url_for('admin_panel'))

    user.is_admin = not user.is_admin
    db.session.commit()
    flash('Правата на потребителя бяха променени!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('home'))
        flash('Грешни данни за вход!', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Потребителското име вече съществува!', 'error')
        else:
            is_first_user = User.query.count() == 0
            new_user = User(username=username, password=password, is_admin=is_first_user)
            db.session.add(new_user)
            db.session.commit()
            flash('Успешна регистрация! Моля, влезете.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)