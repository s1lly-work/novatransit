from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nova_transit_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

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
    ]

    if model != 'all':
        buses = [b for b in all_buses if b['category'] == model]
    else:
        buses = all_buses

    return render_template('gallery.html', buses=buses, selected_model=model)

@app.route('/apply', methods=['GET', 'POST'])
@login_required
def apply():
    if request.method == 'POST':
        name = request.form.get('name')
        experience = request.form.get('experience')
        
        new_app = Application(name=name, experience=experience, user_id=current_user.id)
        db.session.add(new_app)
        db.session.commit()
        flash('Кандидатурата е изпратена успешно!', 'success')
        return redirect(url_for('home'))
        
    return render_template('apply.html')

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)