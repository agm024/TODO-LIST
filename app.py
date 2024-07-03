from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from cs50 import SQL
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your own secret key

# Connect to SQLite database
db = SQL("sqlite:///tasks.db")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    try:
        # Fetch tasks from the database
        tasks = db.execute("SELECT * FROM tasks WHERE user_id = ?", session["user_id"])
        return render_template('index.html', tasks=tasks)
    except Exception as e:
        flash(f"An error occurred: {str(e)}")
        return render_template('index.html', tasks=[]), 500

@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    try:
        # Extract task details from the form
        task = request.form['task']
        date = request.form['date']
        time = request.form['time']

        if not task or not date or not time:
            flash("All fields are required.")
            return redirect(url_for('index'))

        # Insert task into the database
        db.execute("INSERT INTO tasks (task, date, time, user_id) VALUES (?, ?, ?, ?)", task, date, time, session["user_id"])

        # Redirect to the home page
        flash("Task added successfully!")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"An error occurred: {str(e)}")
        return redirect(url_for('index'))

@app.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    try:
        # Delete task from the database
        result = db.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", task_id, session["user_id"])
        if result == 0:
            flash("Task not found or you do not have permission to delete this task.")
            return redirect(url_for('index'))

        flash("Task deleted successfully!")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"An error occurred: {str(e)}")
        return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for('register'))

        # Check if the username already exists
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) > 0:
            flash("Username already exists.")
            return redirect(url_for('register'))

        # Insert the new user into the database
        hash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)

        flash("Registered successfully! Please log in.")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    session.clear()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for('login'))

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) != 1 or not check_password_hash(rows[0]['hash'], password):
            flash("Invalid username and/or password.")
            return redirect(url_for('login'))

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        flash("Logged in successfully!")
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
