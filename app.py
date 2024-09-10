from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from flask_mail import Mail, Message
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DateField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from dotenv import load_dotenv
from flask_migrate import Migrate
import os

# Load environment variables from .env file
load_dotenv()

# Flask app setup
app = Flask(__name__)

# Configuration 
app.config['SECRET_KEY'] = os.urandom(32).hex()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER') 
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL').lower() == 'true'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
mail = Mail(app)

# Define models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    tasks = db.relationship('Task', backref='author', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.String(10), nullable=False, default='Medium')
    category = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='In Progress')
    archived = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subtasks = db.relationship('Subtask', backref='parent_task', lazy=True)

class Subtask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)

# Define forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class TaskForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    due_date = DateField('Due Date', format='%Y-%m-%d')
    priority = SelectField('Priority', choices=[('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')])
    category = SelectField('Category', choices=[('Work', 'Work'), ('Personal', 'Personal'), ('School', 'School')])
    status = SelectField('Status', choices=[('In Progress', 'In Progress'), ('Completed', 'Completed')])
    submit = SubmitField('Submit')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
@login_required
def index():
    tasks = Task.query.filter_by(user_id=current_user.id, archived=False).all()
    return render_template('index.html', tasks=tasks)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(username=form.username.data, email=form.username.data, password=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            flash('Username or Email already exists', 'danger')
            db.session.rollback()
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login failed. Check username and/or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    form = TaskForm()
    if form.validate_on_submit():
        new_task = Task(
            title=form.title.data,
            description=form.description.data,
            due_date=form.due_date.data,
            priority=form.priority.data,
            category=form.category.data,
            status=form.status.data,
            author=current_user
        )
        db.session.add(new_task)
        db.session.commit()
        flash('Task added', 'success')
        return redirect(url_for('index'))
    return render_template('add_task.html', form=form)

@app.route('/update_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.author != current_user:
        abort(403)
    form = TaskForm(obj=task)
    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.due_date = form.due_date.data
        task.priority = form.priority.data
        task.category = form.category.data
        task.status = form.status.data
        db.session.commit()
        flash('Task updated', 'success')
        return redirect(url_for('index'))
    return render_template('update_task.html', form=form, task=task)

@app.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.author != current_user:
        abort(403)
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted', 'success')
    return redirect(url_for('index'))

@app.route('/archive_task/<int:task_id>')
@login_required
def archive_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.author != current_user:
        abort(403)
    task.archived = True
    db.session.commit()
    flash('Task archived', 'success')
    return redirect(url_for('index'))

@app.route('/archived_tasks')
@login_required
def archived_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id, archived=True).all()
    return render_template('archived_tasks.html', tasks=tasks)

@app.route('/add_subtask/<int:task_id>', methods=['POST'])
@login_required
def add_subtask(task_id):
    task = Task.query.get_or_404(task_id)
    if task.author != current_user:
        abort(403)
    title = request.form.get('title')
    new_subtask = Subtask(title=title, parent_task=task)
    db.session.add(new_subtask)
    db.session.commit()
    flash('Subtask added', 'success')
    return redirect(url_for('update_task', task_id=task_id))

@app.route('/toggle_subtask/<int:subtask_id>')
@login_required
def toggle_subtask(subtask_id):
    subtask = Subtask.query.get_or_404(subtask_id)
    if subtask.parent_task.author != current_user:
        abort(403)
    subtask.is_completed = not subtask.is_completed
    db.session.commit()
    flash('Subtask updated', 'success')
    return redirect(url_for('update_task', task_id=subtask.parent_task.id))

@app.route('/task_dashboard')
@login_required
def task_dashboard():
    total_tasks = Task.query.filter_by(user_id=current_user.id).count()
    completed_tasks = Task.query.filter_by(user_id=current_user.id, status='Completed').count()
    # Add more stats as needed
    return render_template('task_dashboard.html', total_tasks=total_tasks, completed_tasks=completed_tasks)

@app.route('/send_email/<int:task_id>')
@login_required
def send_email(task_id):
    task = Task.query.get_or_404(task_id)
    if task.author != current_user:
        abort(403)
    msg = Message('Task Reminder', sender=os.getenv('MAIL_USERNAME'), recipients=[current_user.email])
    msg.body = f'Reminder for task: {task.title}\nDue Date: {task.due_date}'
    mail.send(msg)
    flash('Reminder email sent', 'info')
    return redirect(url_for('index'))

# Error handling
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

if __name__ == '__main__':
    app.run(debug=True)
