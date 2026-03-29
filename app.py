from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import io
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'hackathon2026_key_change_me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'reimburse.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

try:
    import pytesseract
    from PIL import Image
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    OCR_AVAILABLE = True
except:
    OCR_AVAILABLE = False

try:
    import requests as req
    REQUESTS_AVAILABLE = True
except:
    REQUESTS_AVAILABLE = False


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    currency = db.Column(db.String(10), default='USD')
    users = db.relationship('User', backref='company', lazy=True)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='employee')
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_manager_approver = db.Column(db.Boolean, default=True)
    manager = db.relationship('User', remote_side='User.id', foreign_keys='User.manager_id')


class ApprovalRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    rule_type = db.Column(db.String(20), default='sequential')
    percentage = db.Column(db.Float, default=100.0)
    specific_approver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    company = db.relationship('Company', backref='approval_rules')
    specific_approver = db.relationship('User', foreign_keys=[specific_approver_id])


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Float, default=0.0)
    foreign_amount = db.Column(db.Float, default=0.0)
    foreign_currency = db.Column(db.String(10), default='USD')
    category = db.Column(db.String(50))
    description = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    approvers = db.Column(db.Text, default='[]')
    approver_decisions = db.Column(db.Text, default='{}')
    current_approver_index = db.Column(db.Integer, default=0)
    comments = db.Column(db.Text, default='')
    submitter = db.relationship('User', foreign_keys=[user_id], backref='expenses')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_currency_for_country(country_name):
    if not REQUESTS_AVAILABLE:
        return 'USD'
    try:
        data = req.get('https://restcountries.com/v3.1/all?fields=name,currencies', timeout=5).json()
        for c in data:
            if country_name.lower() in str(c.get('name', '')).lower():
                currencies = c.get('currencies', {})
                if currencies:
                    return list(currencies.keys())[0]
    except:
        pass
    return 'USD'


def convert_to_company_currency(amount, from_currency, to_currency):
    if from_currency == to_currency or not REQUESTS_AVAILABLE:
        return amount
    try:
        data = req.get(f'https://api.exchangerate-api.com/v4/latest/{from_currency}', timeout=5).json()
        rate = data['rates'].get(to_currency, 1)
        return round(amount * rate, 2)
    except:
        return amount


def build_approver_list(expense_user):
    approver_ids = []
    if expense_user.manager_id and expense_user.is_manager_approver:
        approver_ids.append(expense_user.manager_id)
    admins = User.query.filter_by(company_id=expense_user.company_id, role='admin').all()
    for admin in admins:
        if admin.id not in approver_ids and admin.id != expense_user.id:
            approver_ids.append(admin.id)
    if not approver_ids:
        approver_ids.append(expense_user.id)
    return approver_ids


def evaluate_approval_rule(expense):
    company_id = expense.submitter.company_id
    rule = ApprovalRule.query.filter_by(company_id=company_id).first()
    if not rule or rule.rule_type == 'sequential':
        return False
    decisions = json.loads(expense.approver_decisions or '{}')
    approvers = json.loads(expense.approvers or '[]')
    approved_count = sum(1 for v in decisions.values() if v == 'approved')
    if rule.rule_type == 'percentage':
        return approved_count >= len(approvers) * (rule.percentage / 100)
    elif rule.rule_type == 'specific':
        return decisions.get(str(rule.specific_approver_id)) == 'approved'
    elif rule.rule_type == 'hybrid':
        pct_met = approved_count >= len(approvers) * (rule.percentage / 100)
        specific_met = decisions.get(str(rule.specific_approver_id)) == 'approved'
        return pct_met or specific_met
    return False


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('signup'))
        password = generate_password_hash(request.form['password'])
        country = request.form.get('country', 'USA')
        currency = get_currency_for_country(country)
        company = Company(name=f"{username}'s Company", currency=currency)
        db.session.add(company)
        db.session.flush()
        user = User(username=username, password=password, role='admin', company_id=company.id)
        db.session.add(user)
        db.session.commit()
        flash(f'Company created with currency {currency}!')
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'employee':
        expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    elif current_user.role == 'manager':
        all_pending = Expense.query.filter_by(status='pending').all()
        expenses = []
        for exp in all_pending:
            approvers = json.loads(exp.approvers or '[]')
            idx = exp.current_approver_index
            if idx < len(approvers) and approvers[idx] == current_user.id:
                expenses.append(exp)
        own = Expense.query.filter_by(user_id=current_user.id).all()
        expenses = expenses + [e for e in own if e not in expenses]
    else:
        expenses = Expense.query.order_by(Expense.date.desc()).all()

    all_users = User.query.filter_by(company_id=current_user.company_id).all()
    managers = [u for u in all_users if u.role in ('manager', 'admin')]
    approval_rule = ApprovalRule.query.filter_by(company_id=current_user.company_id).first()

    return render_template('dashboard.html',
                           expenses=expenses,
                           user=current_user,
                           all_users=all_users,
                           managers=managers,
                           approval_rule=approval_rule,
                           json=json)


@app.route('/create_user', methods=['POST'])
@login_required
def create_user():
    if current_user.role != 'admin':
        flash('Not authorized')
        return redirect(url_for('dashboard'))
    username = request.form['username']
    if User.query.filter_by(username=username).first():
        flash('Username already exists')
        return redirect(url_for('dashboard'))
    password = generate_password_hash(request.form['password'])
    role = request.form['role']
    manager_id = request.form.get('manager_id') or None
    is_manager_approver = 'is_manager_approver' in request.form
    user = User(
        username=username, password=password, role=role,
        company_id=current_user.company_id,
        manager_id=int(manager_id) if manager_id else None,
        is_manager_approver=is_manager_approver
    )
    db.session.add(user)
    db.session.commit()
    flash(f'User {username} created as {role}!')
    return redirect(url_for('dashboard'))


@app.route('/edit_user/<int:user_id>', methods=['POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        flash('Not authorized')
        return redirect(url_for('dashboard'))
    user = User.query.get_or_404(user_id)
    user.role = request.form['role']
    manager_id = request.form.get('manager_id') or None
    user.manager_id = int(manager_id) if manager_id else None
    user.is_manager_approver = 'is_manager_approver' in request.form
    db.session.commit()
    flash(f'User {user.username} updated!')
    return redirect(url_for('dashboard'))


@app.route('/set_approval_rule', methods=['POST'])
@login_required
def set_approval_rule():
    if current_user.role != 'admin':
        flash('Not authorized')
        return redirect(url_for('dashboard'))
    rule = ApprovalRule.query.filter_by(company_id=current_user.company_id).first()
    if not rule:
        rule = ApprovalRule(company_id=current_user.company_id)
        db.session.add(rule)
    rule.rule_type = request.form['rule_type']
    rule.percentage = float(request.form.get('percentage', 100))
    specific_id = request.form.get('specific_approver_id') or None
    rule.specific_approver_id = int(specific_id) if specific_id else None
    db.session.commit()
    flash('Approval rule saved!')
    return redirect(url_for('dashboard'))


@app.route('/submit_expense', methods=['POST'])
@login_required
def submit_expense():
    foreign_amount = float(request.form.get('foreign_amount') or 0)
    foreign_currency = (request.form.get('foreign_currency') or 'USD').strip()
    company_currency = current_user.company.currency
    if foreign_amount and foreign_currency != company_currency:
        amount = convert_to_company_currency(foreign_amount, foreign_currency, company_currency)
    else:
        amount = float(request.form.get('amount') or 0)
    approver_ids = build_approver_list(current_user)
    custom = request.form.get('custom_approvers', '').strip()
    if custom:
        try:
            approver_ids = [int(x.strip()) for x in custom.split(',') if x.strip()]
        except:
            pass
    date_str = request.form.get('date', '')
    try:
        expense_date = datetime.strptime(date_str, '%Y-%m-%d')
    except:
        expense_date = datetime.utcnow()
    expense = Expense(
        user_id=current_user.id,
        amount=amount,
        foreign_amount=foreign_amount,
        foreign_currency=foreign_currency,
        category=request.form['category'],
        description=request.form['description'],
        date=expense_date,
        approvers=json.dumps(approver_ids),
        approver_decisions=json.dumps({})
    )
    db.session.add(expense)
    db.session.commit()
    flash('Expense submitted!')
    return redirect(url_for('dashboard'))


@app.route('/upload_receipt', methods=['POST'])
@login_required
def upload_receipt():
    if not OCR_AVAILABLE:
        flash('OCR not available — Tesseract not installed.')
        return redirect(url_for('dashboard'))
    if 'receipt' not in request.files or request.files['receipt'].filename == '':
        flash('No file selected.')
        return redirect(url_for('dashboard'))
    if 'receipt' in request.files:
        file = request.files['receipt']
        try:
            img = Image.open(io.BytesIO(file.read()))
        except Exception:
            flash('Could not read image. Please upload a JPG or PNG file.')
            return redirect(url_for('dashboard'))
        amount = 0.0
        for word in ocr_data.split():
            cleaned = word.replace('$','').replace('₹','').replace(',','').replace('€','').replace('£','')
            try:
                val = float(cleaned)
                if val > amount:
                    amount = val
            except:
                pass
        approver_ids = build_approver_list(current_user)
        expense = Expense(
            user_id=current_user.id, amount=amount,
            description=f'OCR: {ocr_data[:150]}',
            category='Receipt',
            approvers=json.dumps(approver_ids),
            approver_decisions=json.dumps({})
        )
        db.session.add(expense)
        db.session.commit()
        flash(f'OCR done! Amount: {current_user.company.currency} {amount:.2f}')
    return redirect(url_for('dashboard'))


@app.route('/approve/<int:exp_id>', methods=['POST'])
@login_required
def approve(exp_id):
    expense = Expense.query.get_or_404(exp_id)
    approvers = json.loads(expense.approvers or '[]')
    decisions = json.loads(expense.approver_decisions or '{}')
    if current_user.id not in approvers:
        flash('Not authorized to approve this expense')
        return redirect(url_for('dashboard'))
    idx = expense.current_approver_index
    if idx < len(approvers) and approvers[idx] != current_user.id and current_user.role != 'admin':
        flash('Not your turn to approve yet')
        return redirect(url_for('dashboard'))
    decisions[str(current_user.id)] = 'approved'
    expense.approver_decisions = json.dumps(decisions)
    expense.comments += f"✓ Approved by {current_user.username} on {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    expense.current_approver_index = idx + 1
    if evaluate_approval_rule(expense):
        expense.status = 'approved'
        flash('Expense approved via conditional rule!')
    elif expense.current_approver_index >= len(approvers):
        expense.status = 'approved'
        flash('Expense fully approved!')
    else:
        nxt = User.query.get(approvers[expense.current_approver_index])
        flash(f'Approval recorded. Next: {nxt.username if nxt else "N/A"}')
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/reject/<int:exp_id>', methods=['POST'])
@login_required
def reject(exp_id):
    expense = Expense.query.get_or_404(exp_id)
    approvers = json.loads(expense.approvers or '[]')
    if current_user.id not in approvers and current_user.role != 'admin':
        flash('Not authorized')
        return redirect(url_for('dashboard'))
    comment = request.form.get('comment', 'No reason given')
    decisions = json.loads(expense.approver_decisions or '{}')
    decisions[str(current_user.id)] = 'rejected'
    expense.approver_decisions = json.dumps(decisions)
    expense.status = 'rejected'
    expense.comments += f"✗ Rejected by {current_user.username}: {comment}\n"
    db.session.commit()
    flash('Expense rejected')
    return redirect(url_for('dashboard'))


@app.route('/override/<int:exp_id>', methods=['POST'])
@login_required
def override(exp_id):
    if current_user.role != 'admin':
        flash('Only admins can override')
        return redirect(url_for('dashboard'))
    expense = Expense.query.get_or_404(exp_id)
    action = request.form.get('action', 'approved')
    expense.status = action
    expense.comments += f"⚡ Override by {current_user.username}: {action} on {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    db.session.commit()
    flash(f'Expense {action} via admin override!')
    return redirect(url_for('dashboard'))


@app.route('/api/currency/<code>')
def get_currency(code):
    if not REQUESTS_AVAILABLE:
        return jsonify({'error': 'not available'})
    try:
        data = req.get(f'https://api.exchangerate-api.com/v4/latest/{code}', timeout=5).json()
        return jsonify(data['rates'])
    except:
        return jsonify({'error': 'API unavailable'})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)