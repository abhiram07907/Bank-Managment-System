from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, random, string, hashlib, math
from datetime import datetime, date, timedelta
from functools import wraps
import smtplib, ssl, threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "nexus_bank_ultra_secure_2024"
DB = "nexus.db"


# ═══════════════════════════════════════════════════════
#  EMAIL CONFIG — Stored in DB, editable from Admin Panel
# ═══════════════════════════════════════════════════════
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587

def get_email_config():
    """Load email config from database."""
    try:
        db = get_db()
        rows = db.execute("SELECT key, value FROM settings").fetchall()
        db.close()
        cfg = {r["key"]: r["value"] for r in rows}
        return cfg
    except:
        return {}

def save_setting(key, value):
    db = get_db()
    db.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key, value))
    db.commit()
    db.close()

def email_enabled():
    cfg = get_email_config()
    return cfg.get("email_enabled","0") == "1" and cfg.get("email_user","") not in ("","your_email@gmail.com")

# SMTP settings per provider
SMTP_PROVIDERS = {
    "gmail":    {"host": "smtp.gmail.com",        "port": 587, "tls": True},
    "outlook":  {"host": "smtp-mail.outlook.com", "port": 587, "tls": True},
    "yahoo":    {"host": "smtp.mail.yahoo.com",   "port": 587, "tls": True},
    "mailtrap": {"host": "sandbox.smtp.mailtrap.io", "port": 2525, "tls": True},
    "custom":   {"host": "",                      "port": 587, "tls": True},
}

def send_email_async(to_email, subject, html_body):
    """Send email in a background thread so it never blocks the request."""
    def _send():
        cfg = get_email_config()
        if cfg.get("email_enabled", "0") != "1":
            print(f"[EMAIL DISABLED] Would send to: {to_email}")
            return
        eu       = cfg.get("email_user", "").strip()
        ep       = cfg.get("email_password", "").strip()
        provider = cfg.get("email_provider", "gmail")
        custom_host = cfg.get("custom_host", "").strip()
        custom_port = int(cfg.get("custom_port", "587") or "587")

        if not eu or not ep:
            print("[EMAIL] Credentials not configured.")
            return

        info = SMTP_PROVIDERS.get(provider, SMTP_PROVIDERS["gmail"])
        host = custom_host if provider == "custom" else info["host"]
        port = custom_port if provider == "custom" else info["port"]

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = f"NexusBank <{eu}>"
            msg["To"]      = to_email
            msg.attach(MIMEText(html_body, "html"))
            context = ssl.create_default_context()
            with smtplib.SMTP(host, port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(eu, ep)
                server.sendmail(eu, to_email, msg.as_string())
            print(f"[EMAIL SENT ✅] To: {to_email} | Subject: {subject}")
        except Exception as e:
            print(f"[EMAIL ERROR ❌] {provider} → {e}")
    threading.Thread(target=_send, daemon=True).start()

def email_welcome(name, email, acc_no, acc_type, balance, joined):
    subject = f"Welcome to NexusBank — Your Account {acc_no} is Ready!"
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#050810;font-family:'Jost',Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#050810;padding:40px 20px">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="background:#0c1425;border:1px solid rgba(0,229,160,.2);border-radius:16px;overflow:hidden;max-width:600px">
      <!-- Header -->
      <tr><td style="background:linear-gradient(135deg,#06122a,#0a1d3d);padding:40px;text-align:center;border-bottom:1px solid rgba(0,229,160,.15)">
        <div style="font-size:28px;margin-bottom:8px">◈</div>
        <h1 style="color:#00e5a0;font-size:28px;margin:0;font-weight:700;letter-spacing:2px">NEXUSBANK</h1>
        <p style="color:rgba(255,255,255,.4);margin:8px 0 0;font-size:13px;letter-spacing:1px">ACCOUNT ACTIVATION NOTICE</p>
      </td></tr>
      <!-- Welcome -->
      <tr><td style="padding:36px 40px">
        <p style="color:#dde5f4;font-size:16px;margin:0 0 8px">Dear <strong>{name}</strong>,</p>
        <p style="color:#7b8fad;font-size:14px;line-height:1.7;margin:0 0 28px">Welcome to NexusBank! Your account has been successfully created. Below are your account details — please keep them safe.</p>
        <!-- Account Card -->
        <table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#06122a,#0a2040);border:1px solid rgba(0,229,160,.2);border-radius:12px;overflow:hidden;margin-bottom:28px">
          <tr><td style="padding:24px 28px">
            <p style="color:rgba(255,255,255,.35);font-size:10px;letter-spacing:2px;text-transform:uppercase;margin:0 0 6px">ACCOUNT NUMBER</p>
            <p style="color:#00e5a0;font-size:22px;font-family:'Courier New',monospace;font-weight:700;margin:0 0 20px;letter-spacing:3px">{acc_no}</p>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td width="50%" style="padding-bottom:12px">
                  <p style="color:rgba(255,255,255,.35);font-size:10px;letter-spacing:1px;text-transform:uppercase;margin:0 0 4px">ACCOUNT TYPE</p>
                  <p style="color:#dde5f4;font-size:14px;font-weight:600;margin:0">{acc_type} Account</p>
                </td>
                <td width="50%" style="padding-bottom:12px">
                  <p style="color:rgba(255,255,255,.35);font-size:10px;letter-spacing:1px;text-transform:uppercase;margin:0 0 4px">OPENING BALANCE</p>
                  <p style="color:#f5a623;font-size:14px;font-weight:700;margin:0">₹{balance:,.2f}</p>
                </td>
              </tr>
              <tr>
                <td width="50%">
                  <p style="color:rgba(255,255,255,.35);font-size:10px;letter-spacing:1px;text-transform:uppercase;margin:0 0 4px">REGISTERED EMAIL</p>
                  <p style="color:#dde5f4;font-size:13px;margin:0">{email}</p>
                </td>
                <td width="50%">
                  <p style="color:rgba(255,255,255,.35);font-size:10px;letter-spacing:1px;text-transform:uppercase;margin:0 0 4px">ACCOUNT OPENED</p>
                  <p style="color:#dde5f4;font-size:13px;margin:0">{joined}</p>
                </td>
              </tr>
            </table>
          </td></tr>
        </table>
        <!-- Security Note -->
        <table width="100%" cellpadding="0" cellspacing="0" style="background:rgba(245,166,35,.08);border:1px solid rgba(245,166,35,.2);border-radius:10px;margin-bottom:28px">
          <tr><td style="padding:16px 20px">
            <p style="color:#f5a623;font-size:13px;font-weight:700;margin:0 0 6px">⚠ Security Reminder</p>
            <p style="color:rgba(245,166,35,.75);font-size:12px;line-height:1.6;margin:0">Never share your PIN or account details with anyone, including NexusBank staff. We will never ask for your PIN via email or phone.</p>
          </td></tr>
        </table>
        <!-- What You Can Do -->
        <p style="color:#dde5f4;font-size:14px;font-weight:700;margin:0 0 14px">With your NexusBank account you can:</p>
        <table width="100%" cellpadding="0" cellspacing="0">
          {"".join(f'<tr><td style="padding:6px 0;color:#7b8fad;font-size:13px">✓ &nbsp;{feat}</td></tr>' for feat in [
            "Deposit & withdraw money anytime",
            "Transfer funds instantly to other accounts",
            "Apply for Personal, Home, Car & Education loans",
            "Open Fixed Deposits with up to 7.5% interest",
            "Track all transactions in real time",
            "Raise support tickets 24/7"
          ])}
        </table>
      </td></tr>
      <!-- Footer -->
      <tr><td style="background:#080e1c;padding:24px 40px;text-align:center;border-top:1px solid rgba(255,255,255,.06)">
        <p style="color:#7b8fad;font-size:12px;margin:0 0 6px">This is an automated message from NexusBank. Please do not reply.</p>
        <p style="color:rgba(255,255,255,.2);font-size:11px;margin:0">© 2024 NexusBank · Secure · Reliable · Modern</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""
    send_email_async(email, subject, html)

def email_transaction(name, email, acc_no, txn_type, amount, balance_after, description, timestamp):
    is_credit = txn_type in ["Deposit","Transfer Received","Account Opened","Loan Disbursed"]
    color  = "#00e5a0" if is_credit else "#ff5c7a"
    arrow  = "↓ CREDIT" if is_credit else "↑ DEBIT"
    subject = f"NexusBank: {'Credit' if is_credit else 'Debit'} of ₹{amount:,.2f} on your account"
    html = f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#050810;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#050810;padding:40px 20px">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#0c1425;border:1px solid rgba(255,255,255,.08);border-radius:16px;overflow:hidden;max-width:560px">
      <tr><td style="background:linear-gradient(135deg,#06122a,#0a1d3d);padding:28px 36px;border-bottom:1px solid rgba(255,255,255,.06)">
        <h1 style="color:#00e5a0;font-size:22px;margin:0;font-weight:700;letter-spacing:2px">◈ NEXUSBANK</h1>
        <p style="color:rgba(255,255,255,.4);margin:4px 0 0;font-size:12px">TRANSACTION ALERT</p>
      </td></tr>
      <tr><td style="padding:32px 36px">
        <p style="color:#dde5f4;font-size:15px;margin:0 0 24px">Dear <strong>{name}</strong>, a transaction has been recorded on your account.</p>
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#152240;border:1px solid rgba(255,255,255,.08);border-radius:12px;margin-bottom:24px">
          <tr><td style="padding:20px 24px;border-bottom:1px solid rgba(255,255,255,.06)">
            <p style="color:rgba(255,255,255,.4);font-size:10px;letter-spacing:2px;text-transform:uppercase;margin:0 0 6px">{arrow}</p>
            <p style="color:{color};font-size:32px;font-weight:700;margin:0;font-family:'Courier New',monospace">₹{amount:,.2f}</p>
          </td></tr>
          <tr><td style="padding:20px 24px">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td width="50%" style="padding-bottom:12px"><p style="color:rgba(255,255,255,.35);font-size:10px;letter-spacing:1px;text-transform:uppercase;margin:0 0 4px">TRANSACTION TYPE</p><p style="color:#dde5f4;font-size:13px;font-weight:600;margin:0">{txn_type}</p></td>
                <td width="50%" style="padding-bottom:12px"><p style="color:rgba(255,255,255,.35);font-size:10px;letter-spacing:1px;text-transform:uppercase;margin:0 0 4px">ACCOUNT NUMBER</p><p style="color:#f5a623;font-size:13px;font-family:'Courier New',monospace;margin:0">{acc_no}</p></td>
              </tr>
              <tr>
                <td width="50%"><p style="color:rgba(255,255,255,.35);font-size:10px;letter-spacing:1px;text-transform:uppercase;margin:0 0 4px">BALANCE AFTER</p><p style="color:#dde5f4;font-size:13px;font-weight:700;margin:0">₹{balance_after:,.2f}</p></td>
                <td width="50%"><p style="color:rgba(255,255,255,.35);font-size:10px;letter-spacing:1px;text-transform:uppercase;margin:0 0 4px">DATE & TIME</p><p style="color:#7b8fad;font-size:12px;margin:0">{timestamp}</p></td>
              </tr>
              {"<tr><td colspan='2' style='padding-top:12px'><p style='color:rgba(255,255,255,.35);font-size:10px;letter-spacing:1px;text-transform:uppercase;margin:0 0 4px'>DESCRIPTION</p><p style='color:#7b8fad;font-size:13px;margin:0'>" + description + "</p></td></tr>" if description else ""}
            </table>
          </td></tr>
        </table>
        <p style="color:rgba(255,92,122,.8);font-size:12px;background:rgba(255,92,122,.08);border:1px solid rgba(255,92,122,.15);border-radius:8px;padding:12px 16px;margin:0">If you did not authorize this transaction, contact support immediately.</p>
      </td></tr>
      <tr><td style="background:#080e1c;padding:20px 36px;text-align:center;border-top:1px solid rgba(255,255,255,.06)">
        <p style="color:rgba(255,255,255,.2);font-size:11px;margin:0">© 2024 NexusBank · This is an automated alert.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""
    send_email_async(email, subject, html)

# ═══════════════════════════════════════════════════════
#  DATABASE
# ═══════════════════════════════════════════════════════
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        account_no   TEXT UNIQUE NOT NULL,
        name         TEXT NOT NULL,
        email        TEXT UNIQUE NOT NULL,
        phone        TEXT NOT NULL,
        dob          TEXT,
        address      TEXT,
        pin_hash     TEXT NOT NULL,
        account_type TEXT DEFAULT 'Savings',
        balance      REAL DEFAULT 0,
        status       TEXT DEFAULT 'Active',
        kyc_verified INTEGER DEFAULT 0,
        created_at   TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS transactions (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        account_no    TEXT NOT NULL,
        type          TEXT NOT NULL,
        amount        REAL NOT NULL,
        balance_after REAL NOT NULL,
        description   TEXT,
        ref_account   TEXT,
        category      TEXT DEFAULT 'General',
        timestamp     TEXT NOT NULL,
        FOREIGN KEY (account_no) REFERENCES users(account_no)
    );
    CREATE TABLE IF NOT EXISTS loans (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        account_no    TEXT NOT NULL,
        loan_type     TEXT NOT NULL,
        principal     REAL NOT NULL,
        interest_rate REAL NOT NULL,
        tenure_months INTEGER NOT NULL,
        emi           REAL NOT NULL,
        paid_emis     INTEGER DEFAULT 0,
        outstanding   REAL NOT NULL,
        status        TEXT DEFAULT 'Pending',
        applied_at    TEXT NOT NULL,
        approved_at   TEXT,
        FOREIGN KEY (account_no) REFERENCES users(account_no)
    );
    CREATE TABLE IF NOT EXISTS fixed_deposits (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        account_no    TEXT NOT NULL,
        amount        REAL NOT NULL,
        interest_rate REAL NOT NULL,
        tenure_months INTEGER NOT NULL,
        maturity_date TEXT NOT NULL,
        maturity_amt  REAL NOT NULL,
        status        TEXT DEFAULT 'Active',
        created_at    TEXT NOT NULL,
        FOREIGN KEY (account_no) REFERENCES users(account_no)
    );
    CREATE TABLE IF NOT EXISTS beneficiaries (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        account_no  TEXT NOT NULL,
        ben_acc_no  TEXT NOT NULL,
        ben_name    TEXT NOT NULL,
        ben_bank    TEXT DEFAULT 'NexusBank',
        nickname    TEXT,
        added_at    TEXT NOT NULL,
        FOREIGN KEY (account_no) REFERENCES users(account_no)
    );
    CREATE TABLE IF NOT EXISTS support_tickets (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        account_no  TEXT NOT NULL,
        subject     TEXT NOT NULL,
        message     TEXT NOT NULL,
        status      TEXT DEFAULT 'Open',
        reply       TEXT,
        created_at  TEXT NOT NULL,
        FOREIGN KEY (account_no) REFERENCES users(account_no)
    );
    CREATE TABLE IF NOT EXISTS admin (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        username  TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT ''
    );
    INSERT OR IGNORE INTO settings (key,value) VALUES ('email_enabled','0');
    INSERT OR IGNORE INTO settings (key,value) VALUES ('email_provider','gmail');
    INSERT OR IGNORE INTO settings (key,value) VALUES ('email_user','');
    INSERT OR IGNORE INTO settings (key,value) VALUES ('email_password','');
    INSERT OR IGNORE INTO settings (key,value) VALUES ('custom_host','');
    INSERT OR IGNORE INTO settings (key,value) VALUES ('custom_port','587');
    INSERT OR IGNORE INTO settings (key,value) VALUES ('bank_name','NexusBank');
    INSERT OR IGNORE INTO admin (username, password_hash)
    VALUES ('admin', '""" + hashlib.sha256(b'admin123').hexdigest() + """');
    """)
    db.commit()
    db.close()

# ═══════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════
def hp(p): return hashlib.sha256(p.encode()).hexdigest()
def ts(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def gen_acc():
    return "NXS" + "".join(random.choices(string.digits, k=9))

def log_txn(db, acc, typ, amt, bal, desc="", ref="", cat="General"):
    db.execute("""INSERT INTO transactions
        (account_no,type,amount,balance_after,description,ref_account,category,timestamp)
        VALUES(?,?,?,?,?,?,?,?)""", (acc,typ,amt,bal,desc,ref,cat,ts()))

def calc_emi(principal, rate_annual, months):
    r = rate_annual / (12 * 100)
    if r == 0: return principal / months
    return round(principal * r * (1+r)**months / ((1+r)**months - 1), 2)

def login_required(f):
    @wraps(f)
    def dec(*a, **k):
        if "acc" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return f(*a, **k)
    return dec

def admin_required(f):
    @wraps(f)
    def dec(*a, **k):
        if "admin" not in session:
            return redirect(url_for("admin_login"))
        return f(*a, **k)
    return dec

def get_user(acc_no=None):
    db = get_db()
    u = db.execute("SELECT * FROM users WHERE account_no=?",
                   (acc_no or session.get("acc"),)).fetchone()
    db.close()
    return u

# ═══════════════════════════════════════════════════════
#  LANDING
# ═══════════════════════════════════════════════════════
@app.route("/")
def index():
    if "acc" in session: return redirect(url_for("dashboard"))
    return render_template("index.html")

# ═══════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        f = request.form
        name=f["name"].strip(); email=f["email"].strip().lower()
        phone=f["phone"].strip(); dob=f.get("dob","")
        address=f.get("address","").strip()
        acc_type=f["account_type"]; pin=f["pin"]; pin2=f["pin2"]
        dep=f["initial_deposit"]

        if not all([name,email,phone,pin,dep]):
            flash("All required fields must be filled.", "error"); return render_template("register.html")
        if pin != pin2:
            flash("PINs do not match.", "error"); return render_template("register.html")
        if not pin.isdigit() or len(pin)!=4:
            flash("PIN must be exactly 4 digits.", "error"); return render_template("register.html")
        try:
            dep = float(dep)
            if dep < 500: flash("Minimum deposit ₹500.", "error"); return render_template("register.html")
        except: flash("Invalid deposit amount.", "error"); return render_template("register.html")

        db = get_db()
        if db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            flash("Email already registered.", "error"); db.close(); return render_template("register.html")

        acc_no = gen_acc()
        while db.execute("SELECT 1 FROM users WHERE account_no=?", (acc_no,)).fetchone():
            acc_no = gen_acc()

        db.execute("""INSERT INTO users
            (account_no,name,email,phone,dob,address,pin_hash,account_type,balance,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (acc_no,name,email,phone,dob,address,hp(pin),acc_type,dep,ts()))
        log_txn(db, acc_no, "Account Opened", dep, dep, "Initial deposit", "", "Credit")
        db.commit(); db.close()
        # Send welcome email with account details
        email_welcome(name, email, acc_no, acc_type, dep, datetime.now().strftime("%d %b %Y"))
        flash(f"Account created! Your Account No: {acc_no} — Check your email for details.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        acc_no = request.form["account_no"].strip().upper()
        pin    = request.form["pin"].strip()
        db = get_db()
        u = db.execute("SELECT * FROM users WHERE account_no=?", (acc_no,)).fetchone()
        db.close()
        if u and u["pin_hash"] == hp(pin):
            if u["status"] == "Frozen":
                flash("Account is frozen. Contact support.", "error")
                return render_template("login.html")
            session["acc"]  = u["account_no"]
            session["name"] = u["name"]
            flash(f"Welcome back, {u['name'].split()[0]}! 👋", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid account number or PIN.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))

# ═══════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════
@app.route("/dashboard")
@login_required
def dashboard():
    db  = get_db()
    u   = db.execute("SELECT * FROM users WHERE account_no=?", (session["acc"],)).fetchone()
    txns= db.execute("SELECT * FROM transactions WHERE account_no=? ORDER BY id DESC LIMIT 6", (session["acc"],)).fetchall()
    loans= db.execute("SELECT * FROM loans WHERE account_no=? AND status='Approved'", (session["acc"],)).fetchall()
    fds  = db.execute("SELECT * FROM fixed_deposits WHERE account_no=? AND status='Active'", (session["acc"],)).fetchall()
    # spending by category this month
    month_start = date.today().replace(day=1).strftime("%Y-%m-%d")
    spent = db.execute("""SELECT category, SUM(amount) as total FROM transactions
        WHERE account_no=? AND type IN ('Withdrawal','Transfer Sent')
        AND timestamp >= ? GROUP BY category""", (session["acc"], month_start)).fetchall()
    total_loan = sum(l["outstanding"] for l in loans)
    total_fd   = sum(f["amount"] for f in fds)
    db.close()
    return render_template("dashboard.html", u=u, txns=txns,
                           total_loan=total_loan, total_fd=total_fd,
                           spent=spent, fds=fds, loans=loans)

# ═══════════════════════════════════════════════════════
#  TRANSACTIONS
# ═══════════════════════════════════════════════════════
@app.route("/deposit", methods=["GET","POST"])
@login_required
def deposit():
    if request.method == "POST":
        try: amount = float(request.form["amount"])
        except: flash("Invalid amount.", "error"); return render_template("deposit.html")
        if amount <= 0: flash("Amount must be positive.", "error"); return render_template("deposit.html")
        desc = request.form.get("description","Cash Deposit").strip() or "Cash Deposit"
        cat  = request.form.get("category","Credit")
        db   = get_db()
        u    = db.execute("SELECT * FROM users WHERE account_no=?", (session["acc"],)).fetchone()
        new_bal = u["balance"] + amount
        db.execute("UPDATE users SET balance=? WHERE account_no=?", (new_bal, session["acc"]))
        log_txn(db, session["acc"], "Deposit", amount, new_bal, desc, "", cat)
        db.commit()
        user_email = db.execute("SELECT email,name FROM users WHERE account_no=?", (session["acc"],)).fetchone()
        db.close()
        email_transaction(user_email["name"], user_email["email"], session["acc"], "Deposit", amount, new_bal, desc, ts())
        flash(f"₹{amount:,.2f} deposited! New balance: ₹{new_bal:,.2f}", "success")
        return redirect(url_for("dashboard"))
    return render_template("deposit.html")

@app.route("/withdraw", methods=["GET","POST"])
@login_required
def withdraw():
    u = get_user()
    if request.method == "POST":
        pin = request.form["pin"].strip()
        if u["pin_hash"] != hp(pin): flash("Incorrect PIN.", "error"); return render_template("withdraw.html", u=u)
        try: amount = float(request.form["amount"])
        except: flash("Invalid amount.", "error"); return render_template("withdraw.html", u=u)
        if amount <= 0: flash("Amount must be positive.", "error"); return render_template("withdraw.html", u=u)
        if u["balance"] < amount: flash(f"Insufficient balance. Available: ₹{u['balance']:,.2f}", "error"); return render_template("withdraw.html", u=u)
        desc = request.form.get("description","Cash Withdrawal").strip() or "Cash Withdrawal"
        cat  = request.form.get("category","Debit")
        db   = get_db()
        new_bal = u["balance"] - amount
        db.execute("UPDATE users SET balance=? WHERE account_no=?", (new_bal, session["acc"]))
        log_txn(db, session["acc"], "Withdrawal", amount, new_bal, desc, "", cat)
        db.commit()
        ue = db.execute("SELECT email,name FROM users WHERE account_no=?", (session["acc"],)).fetchone()
        db.close()
        email_transaction(ue["name"], ue["email"], session["acc"], "Withdrawal", amount, new_bal, desc, ts())
        flash(f"₹{amount:,.2f} withdrawn! Remaining: ₹{new_bal:,.2f}", "success")
        return redirect(url_for("dashboard"))
    return render_template("withdraw.html", u=u)

@app.route("/transfer", methods=["GET","POST"])
@login_required
def transfer():
    u = get_user()
    db_b = get_db()
    bens = db_b.execute("SELECT * FROM beneficiaries WHERE account_no=?", (session["acc"],)).fetchall()
    db_b.close()
    if request.method == "POST":
        to_acc = request.form["to_account"].strip().upper()
        pin    = request.form["pin"].strip()
        if u["pin_hash"] != hp(pin): flash("Incorrect PIN.", "error"); return render_template("transfer.html", u=u, bens=bens)
        if to_acc == session["acc"]: flash("Cannot transfer to yourself.", "error"); return render_template("transfer.html", u=u, bens=bens)
        try: amount = float(request.form["amount"])
        except: flash("Invalid amount.", "error"); return render_template("transfer.html", u=u, bens=bens)
        if amount <= 0: flash("Amount must be positive.", "error"); return render_template("transfer.html", u=u, bens=bens)
        if u["balance"] < amount: flash(f"Insufficient balance. Available: ₹{u['balance']:,.2f}", "error"); return render_template("transfer.html", u=u, bens=bens)
        desc = request.form.get("description","Fund Transfer").strip() or "Fund Transfer"
        db   = get_db()
        tgt  = db.execute("SELECT * FROM users WHERE account_no=?", (to_acc,)).fetchone()
        if not tgt: flash("Recipient account not found.", "error"); db.close(); return render_template("transfer.html", u=u, bens=bens)
        new_my  = u["balance"] - amount
        new_tgt = tgt["balance"] + amount
        db.execute("UPDATE users SET balance=? WHERE account_no=?", (new_my,  session["acc"]))
        db.execute("UPDATE users SET balance=? WHERE account_no=?", (new_tgt, to_acc))
        log_txn(db, session["acc"], "Transfer Sent",     amount, new_my,  f"{desc} → {tgt['name']}", to_acc,            "Transfer")
        log_txn(db, to_acc,         "Transfer Received", amount, new_tgt, f"{desc} ← {u['name']}",   session["acc"],    "Transfer")
        db.commit()
        now = ts()
        db.close()
        # Email both parties
        email_transaction(u["name"],    u["email"],   session["acc"], "Transfer Sent",     amount, new_my,  f"To {tgt['name']} ({to_acc})", now)
        email_transaction(tgt["name"], tgt["email"],  to_acc,         "Transfer Received", amount, new_tgt, f"From {u['name']} ({session['acc']})", now)
        flash(f"₹{amount:,.2f} transferred to {tgt['name']} successfully!", "success")
        return redirect(url_for("dashboard"))
    return render_template("transfer.html", u=u, bens=bens)

@app.route("/transactions")
@login_required
def transactions():
    db   = get_db()
    u    = db.execute("SELECT * FROM users WHERE account_no=?", (session["acc"],)).fetchone()
    txns = db.execute("SELECT * FROM transactions WHERE account_no=? ORDER BY id DESC", (session["acc"],)).fetchall()
    db.close()
    return render_template("transactions.html", txns=txns, u=u)

# ═══════════════════════════════════════════════════════
#  BENEFICIARIES
# ═══════════════════════════════════════════════════════
@app.route("/beneficiaries", methods=["GET","POST"])
@login_required
def beneficiaries():
    db = get_db()
    if request.method == "POST":
        ben_acc  = request.form["ben_acc"].strip().upper()
        nickname = request.form.get("nickname","").strip()
        if ben_acc == session["acc"]:
            flash("Cannot add yourself.", "error")
        else:
            tgt = db.execute("SELECT name FROM users WHERE account_no=?", (ben_acc,)).fetchone()
            if not tgt: flash("Account not found.", "error")
            else:
                exists = db.execute("SELECT 1 FROM beneficiaries WHERE account_no=? AND ben_acc_no=?",
                                    (session["acc"], ben_acc)).fetchone()
                if exists: flash("Beneficiary already added.", "warning")
                else:
                    db.execute("INSERT INTO beneficiaries (account_no,ben_acc_no,ben_name,nickname,added_at) VALUES(?,?,?,?,?)",
                               (session["acc"], ben_acc, tgt["name"], nickname or tgt["name"], ts()))
                    db.commit()
                    flash(f"{tgt['name']} added as beneficiary!", "success")
    bens = db.execute("SELECT * FROM beneficiaries WHERE account_no=? ORDER BY added_at DESC", (session["acc"],)).fetchall()
    db.close()
    return render_template("beneficiaries.html", bens=bens)

@app.route("/beneficiaries/delete/<int:bid>", methods=["POST"])
@login_required
def delete_beneficiary(bid):
    db = get_db()
    db.execute("DELETE FROM beneficiaries WHERE id=? AND account_no=?", (bid, session["acc"]))
    db.commit(); db.close()
    flash("Beneficiary removed.", "info")
    return redirect(url_for("beneficiaries"))

# ═══════════════════════════════════════════════════════
#  LOANS
# ═══════════════════════════════════════════════════════
LOAN_TYPES = {
    "Personal": {"rate": 12.5, "max": 500000, "min_tenure": 12, "max_tenure": 60},
    "Home":     {"rate": 8.5,  "max": 5000000,"min_tenure": 60, "max_tenure": 240},
    "Car":      {"rate": 10.0, "max": 1500000,"min_tenure": 12, "max_tenure": 84},
    "Education":{"rate": 9.0,  "max": 2000000,"min_tenure": 12, "max_tenure": 120},
}

@app.route("/loans", methods=["GET","POST"])
@login_required
def loans():
    db = get_db()
    u  = db.execute("SELECT * FROM users WHERE account_no=?", (session["acc"],)).fetchone()
    if request.method == "POST":
        loan_type = request.form["loan_type"]
        principal = float(request.form["principal"])
        tenure    = int(request.form["tenure"])
        pin       = request.form["pin"]
        if u["pin_hash"] != hp(pin):
            flash("Incorrect PIN.", "error")
        elif loan_type not in LOAN_TYPES:
            flash("Invalid loan type.", "error")
        else:
            info = LOAN_TYPES[loan_type]
            if principal > info["max"]:
                flash(f"Max loan for {loan_type} is ₹{info['max']:,}", "error")
            elif not (info["min_tenure"] <= tenure <= info["max_tenure"]):
                flash(f"Tenure must be between {info['min_tenure']}–{info['max_tenure']} months.", "error")
            else:
                emi = calc_emi(principal, info["rate"], tenure)
                db.execute("""INSERT INTO loans
                    (account_no,loan_type,principal,interest_rate,tenure_months,emi,outstanding,applied_at)
                    VALUES(?,?,?,?,?,?,?,?)""",
                    (session["acc"],loan_type,principal,info["rate"],tenure,emi,principal,ts()))
                db.commit()
                flash(f"{loan_type} Loan of ₹{principal:,.0f} applied! EMI: ₹{emi:,.2f}/month. Pending approval.", "success")

    my_loans = db.execute("SELECT * FROM loans WHERE account_no=? ORDER BY id DESC", (session["acc"],)).fetchall()
    db.close()
    return render_template("loans.html", u=u, my_loans=my_loans, loan_types=LOAN_TYPES)

@app.route("/loans/pay_emi/<int:lid>", methods=["POST"])
@login_required
def pay_emi(lid):
    db = get_db()
    u  = db.execute("SELECT * FROM users WHERE account_no=?", (session["acc"],)).fetchone()
    l  = db.execute("SELECT * FROM loans WHERE id=? AND account_no=?", (lid, session["acc"])).fetchone()
    if not l or l["status"] != "Approved":
        flash("Invalid loan.", "error"); db.close(); return redirect(url_for("loans"))
    pin = request.form["pin"]
    if u["pin_hash"] != hp(pin): flash("Incorrect PIN.", "error"); db.close(); return redirect(url_for("loans"))
    if u["balance"] < l["emi"]: flash(f"Insufficient balance. EMI: ₹{l['emi']:,.2f}", "error"); db.close(); return redirect(url_for("loans"))
    new_bal     = u["balance"] - l["emi"]
    new_out     = max(0, l["outstanding"] - l["emi"])
    paid        = l["paid_emis"] + 1
    new_status  = "Closed" if paid >= l["tenure_months"] else "Approved"
    db.execute("UPDATE users SET balance=? WHERE account_no=?", (new_bal, session["acc"]))
    db.execute("UPDATE loans SET outstanding=?,paid_emis=?,status=? WHERE id=?", (new_out,paid,new_status,lid))
    log_txn(db, session["acc"], "EMI Payment", l["emi"], new_bal, f"{l['loan_type']} Loan EMI #{paid}", "", "Loan")
    db.commit(); db.close()
    flash(f"EMI ₹{l['emi']:,.2f} paid! Remaining: ₹{new_out:,.2f}", "success")
    return redirect(url_for("loans"))

@app.route("/emi_calculator")
@login_required
def emi_calculator():
    return render_template("emi_calculator.html", loan_types=LOAN_TYPES)

@app.route("/api/calc_emi")
@login_required
def api_calc_emi():
    try:
        p = float(request.args["principal"])
        r = float(request.args["rate"])
        n = int(request.args["tenure"])
        emi = calc_emi(p, r, n)
        total = round(emi * n, 2)
        interest = round(total - p, 2)
        return jsonify({"emi": emi, "total": total, "interest": interest})
    except: return jsonify({"error": "Invalid input"})

# ═══════════════════════════════════════════════════════
#  FIXED DEPOSITS
# ═══════════════════════════════════════════════════════
FD_RATES = {6: 5.5, 12: 6.5, 24: 7.0, 36: 7.25, 60: 7.5}

@app.route("/fixed_deposits", methods=["GET","POST"])
@login_required
def fixed_deposits():
    u  = get_user()
    db = get_db()
    if request.method == "POST":
        try: amount = float(request.form["amount"])
        except: flash("Invalid amount.", "error"); return redirect(url_for("fixed_deposits"))
        tenure = int(request.form["tenure"])
        pin    = request.form["pin"]
        if u["pin_hash"] != hp(pin): flash("Incorrect PIN.", "error"); return redirect(url_for("fixed_deposits"))
        if amount < 1000: flash("Minimum FD amount is ₹1,000.", "error"); return redirect(url_for("fixed_deposits"))
        if u["balance"] < amount: flash("Insufficient balance.", "error"); return redirect(url_for("fixed_deposits"))
        if tenure not in FD_RATES: flash("Invalid tenure.", "error"); return redirect(url_for("fixed_deposits"))
        rate    = FD_RATES[tenure]
        mat_amt = round(amount * (1 + rate/100 * tenure/12), 2)
        mat_date= (date.today() + timedelta(days=30*tenure)).strftime("%Y-%m-%d")
        new_bal = u["balance"] - amount
        db.execute("UPDATE users SET balance=? WHERE account_no=?", (new_bal, session["acc"]))
        db.execute("INSERT INTO fixed_deposits (account_no,amount,interest_rate,tenure_months,maturity_date,maturity_amt,created_at) VALUES(?,?,?,?,?,?,?)",
                   (session["acc"],amount,rate,tenure,mat_date,mat_amt,ts()))
        log_txn(db, session["acc"], "FD Created", amount, new_bal, f"Fixed Deposit - {tenure} months @ {rate}%", "", "Investment")
        db.commit(); db.close()
        flash(f"FD of ₹{amount:,.2f} created! Matures on {mat_date} with ₹{mat_amt:,.2f}", "success")
        return redirect(url_for("fixed_deposits"))
    my_fds = db.execute("SELECT * FROM fixed_deposits WHERE account_no=? ORDER BY id DESC", (session["acc"],)).fetchall()
    db.close()
    return render_template("fixed_deposits.html", u=u, my_fds=my_fds, fd_rates=FD_RATES)

@app.route("/fixed_deposits/break/<int:fid>", methods=["POST"])
@login_required
def break_fd(fid):
    db = get_db()
    u  = db.execute("SELECT * FROM users WHERE account_no=?", (session["acc"],)).fetchone()
    fd = db.execute("SELECT * FROM fixed_deposits WHERE id=? AND account_no=?", (fid, session["acc"])).fetchone()
    if not fd or fd["status"] != "Active": flash("Invalid FD.", "error"); db.close(); return redirect(url_for("fixed_deposits"))
    pin = request.form["pin"]
    if u["pin_hash"] != hp(pin): flash("Incorrect PIN.", "error"); db.close(); return redirect(url_for("fixed_deposits"))
    # 1% penalty on break
    penalty    = round(fd["amount"] * 0.01, 2)
    refund     = fd["amount"] - penalty
    new_bal    = u["balance"] + refund
    db.execute("UPDATE users SET balance=? WHERE account_no=?", (new_bal, session["acc"]))
    db.execute("UPDATE fixed_deposits SET status='Broken' WHERE id=?", (fid,))
    log_txn(db, session["acc"], "FD Broken", refund, new_bal, f"FD #{fid} broken (₹{penalty} penalty)", "", "Credit")
    db.commit(); db.close()
    flash(f"FD broken. ₹{refund:,.2f} credited (₹{penalty} penalty deducted).", "warning")
    return redirect(url_for("fixed_deposits"))

# ═══════════════════════════════════════════════════════
#  PROFILE & SETTINGS
# ═══════════════════════════════════════════════════════
@app.route("/profile", methods=["GET","POST"])
@login_required
def profile():
    u = get_user()
    if request.method == "POST":
        action = request.form.get("action")
        db = get_db()
        if action == "update_info":
            phone   = request.form["phone"].strip()
            address = request.form["address"].strip()
            db.execute("UPDATE users SET phone=?,address=? WHERE account_no=?",
                       (phone, address, session["acc"]))
            db.commit()
            flash("Profile updated successfully!", "success")
        elif action == "change_pin":
            old=request.form["old_pin"]; new=request.form["new_pin"]; c=request.form["confirm_pin"]
            if u["pin_hash"] != hp(old): flash("Current PIN incorrect.", "error")
            elif new != c: flash("New PINs don't match.", "error")
            elif not new.isdigit() or len(new)!=4: flash("PIN must be 4 digits.", "error")
            else:
                db.execute("UPDATE users SET pin_hash=? WHERE account_no=?", (hp(new), session["acc"]))
                db.commit(); flash("PIN changed successfully!", "success")
        db.close()
        u = get_user()
    return render_template("profile.html", u=u)

@app.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    pin = request.form["pin"]
    u   = get_user()
    if u["pin_hash"] != hp(pin): flash("Incorrect PIN.", "error"); return redirect(url_for("profile"))
    db = get_db()
    for t in ["transactions","loans","fixed_deposits","beneficiaries","support_tickets"]:
        db.execute(f"DELETE FROM {t} WHERE account_no=?", (session["acc"],))
    db.execute("DELETE FROM users WHERE account_no=?", (session["acc"],))
    db.commit(); db.close()
    session.clear()
    flash("Account permanently deleted.", "info")
    return redirect(url_for("index"))

# ═══════════════════════════════════════════════════════
#  SUPPORT TICKETS
# ═══════════════════════════════════════════════════════
@app.route("/support", methods=["GET","POST"])
@login_required
def support():
    db = get_db()
    if request.method == "POST":
        subject = request.form["subject"].strip()
        message = request.form["message"].strip()
        if subject and message:
            db.execute("INSERT INTO support_tickets (account_no,subject,message,created_at) VALUES(?,?,?,?)",
                       (session["acc"], subject, message, ts()))
            db.commit()
            flash("Support ticket raised! We'll respond within 24 hours.", "success")
        else: flash("Subject and message are required.", "error")
    tickets = db.execute("SELECT * FROM support_tickets WHERE account_no=? ORDER BY id DESC", (session["acc"],)).fetchall()
    db.close()
    return render_template("support.html", tickets=tickets)

# ═══════════════════════════════════════════════════════
#  ADMIN PANEL
# ═══════════════════════════════════════════════════════
def ensure_admin():
    """Always reset admin credentials so they never get corrupted."""
    db = get_db()
    existing = db.execute("SELECT password_hash FROM admin WHERE username='admin'").fetchone()
    correct_hash = hp('admin123')
    if not existing or existing[0] != correct_hash:
        db.execute("DELETE FROM admin WHERE username='admin'")
        db.execute("INSERT INTO admin (username, password_hash) VALUES ('admin', ?)", (correct_hash,))
        db.commit()
    db.close()

@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    ensure_admin()  # Fix credentials on every login page visit
    if request.method == "POST":
        u = request.form["username"].strip()
        p = request.form["password"].strip()
        db = get_db()
        a  = db.execute("SELECT * FROM admin WHERE username=? AND password_hash=?", (u, hp(p))).fetchone()
        db.close()
        if a:
            session["admin"] = u
            flash("Welcome back, Admin!", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid credentials. Default: admin / admin123", "error")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    users  = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    txns   = db.execute("SELECT t.*,u.name FROM transactions t JOIN users u ON t.account_no=u.account_no ORDER BY t.id DESC LIMIT 20").fetchall()
    loans  = db.execute("SELECT l.*,u.name FROM loans l JOIN users u ON l.account_no=u.account_no ORDER BY l.id DESC").fetchall()
    tickets= db.execute("SELECT s.*,u.name FROM support_tickets s JOIN users u ON s.account_no=u.account_no ORDER BY s.id DESC").fetchall()
    stats  = {
        "total_users":    db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "total_balance":  db.execute("SELECT SUM(balance) FROM users").fetchone()[0] or 0,
        "total_txns":     db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0],
        "pending_loans":  db.execute("SELECT COUNT(*) FROM loans WHERE status='Pending'").fetchone()[0],
        "open_tickets":   db.execute("SELECT COUNT(*) FROM support_tickets WHERE status='Open'").fetchone()[0],
        "total_fds":      db.execute("SELECT COUNT(*) FROM fixed_deposits WHERE status='Active'").fetchone()[0],
    }
    db.close()
    return render_template("admin_dashboard.html", users=users, txns=txns,
                           loans=loans, tickets=tickets, stats=stats)

@app.route("/admin/freeze/<acc_no>", methods=["POST"])
@admin_required
def admin_freeze(acc_no):
    db=get_db()
    u=db.execute("SELECT status FROM users WHERE account_no=?", (acc_no,)).fetchone()
    new_status = "Active" if u["status"]=="Frozen" else "Frozen"
    db.execute("UPDATE users SET status=? WHERE account_no=?", (new_status, acc_no))
    db.commit(); db.close()
    flash(f"Account {acc_no} is now {new_status}.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/loan/<int:lid>/<action>", methods=["POST"])
@admin_required
def admin_loan_action(lid, action):
    db=get_db()
    if action in ["approve","reject"]:
        status = "Approved" if action=="approve" else "Rejected"
        approved_at = ts() if action=="approve" else None
        db.execute("UPDATE loans SET status=?,approved_at=? WHERE id=?", (status,approved_at,lid))
        if action == "approve":
            l = db.execute("SELECT * FROM loans WHERE id=?", (lid,)).fetchone()
            u = db.execute("SELECT * FROM users WHERE account_no=?", (l["account_no"],)).fetchone()
            new_bal = u["balance"] + l["principal"]
            db.execute("UPDATE users SET balance=? WHERE account_no=?", (new_bal, l["account_no"]))
            log_txn(db, l["account_no"], "Loan Disbursed", l["principal"], new_bal,
                    f"{l['loan_type']} Loan approved", "", "Loan")
        db.commit()
        flash(f"Loan {status}.", "success")
    db.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/ticket/<int:tid>", methods=["POST"])
@admin_required
def admin_ticket_reply(tid):
    reply = request.form["reply"].strip()
    db=get_db()
    db.execute("UPDATE support_tickets SET reply=?,status='Resolved' WHERE id=?", (reply,tid))
    db.commit(); db.close()
    flash("Ticket resolved.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/user/<acc_no>")
@admin_required
def admin_user_detail(acc_no):
    db = get_db()
    u     = db.execute("SELECT * FROM users WHERE account_no=?", (acc_no,)).fetchone()
    if not u:
        flash("User not found.", "error")
        db.close()
        return redirect(url_for("admin_dashboard"))
    txns  = db.execute("SELECT * FROM transactions WHERE account_no=? ORDER BY id DESC", (acc_no,)).fetchall()
    loans = db.execute("SELECT * FROM loans WHERE account_no=? ORDER BY id DESC", (acc_no,)).fetchall()
    fds   = db.execute("SELECT * FROM fixed_deposits WHERE account_no=? ORDER BY id DESC", (acc_no,)).fetchall()
    bens  = db.execute("SELECT * FROM beneficiaries WHERE account_no=?", (acc_no,)).fetchall()
    db.close()
    return render_template("admin_user_detail.html", u=u, txns=txns, loans=loans, fds=fds, bens=bens)

@app.route("/admin/user/<acc_no>/kyc", methods=["POST"])
@admin_required
def admin_toggle_kyc(acc_no):
    db = get_db()
    u  = db.execute("SELECT kyc_verified FROM users WHERE account_no=?", (acc_no,)).fetchone()
    new_kyc = 0 if u["kyc_verified"] else 1
    db.execute("UPDATE users SET kyc_verified=? WHERE account_no=?", (new_kyc, acc_no))
    db.commit(); db.close()
    flash(f"KYC {'Verified' if new_kyc else 'Unverified'} for {acc_no}.", "success")
    return redirect(url_for("admin_user_detail", acc_no=acc_no))


# ═══════════════════════════════════════════════════════
#  ADMIN — EMAIL SETTINGS
# ═══════════════════════════════════════════════════════
@app.route("/admin/email_settings", methods=["GET","POST"])
@admin_required
def admin_email_settings():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")

        if action == "save":
            eu       = request.form.get("email_user","").strip()
            ep       = request.form.get("email_password","").strip()
            provider = request.form.get("email_provider","gmail")
            c_host   = request.form.get("custom_host","").strip()
            c_port   = request.form.get("custom_port","587").strip()
            enabled  = "1" if request.form.get("email_enabled") else "0"
            for k,v in [("email_user",eu),("email_password",ep),
                        ("email_provider",provider),("custom_host",c_host),
                        ("custom_port",c_port),("email_enabled",enabled)]:
                db.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)",(k,v))
            db.commit()
            flash("Email settings saved successfully!", "success")

        elif action == "test":
            test_to = request.form.get("test_email","").strip()
            if not test_to:
                flash("Enter a test email address.", "error")
            else:
                cfg = get_email_config()
                if cfg.get("email_enabled","0") != "1" or not cfg.get("email_user"):
                    flash("Save & enable email settings first before sending test.", "error")
                else:
                    send_email_async(test_to, "NexusBank — Test Email ✅",
                        f"""<html><body style="background:#050810;font-family:Arial;padding:40px">
                        <div style="max-width:500px;margin:0 auto;background:#0c1425;border:1px solid rgba(0,229,160,.3);border-radius:16px;padding:36px">
                        <h2 style="color:#00e5a0;margin:0 0 16px">◈ NexusBank</h2>
                        <h3 style="color:#dde5f4;margin:0 0 12px">Test Email Successful! ✅</h3>
                        <p style="color:#7b8fad;line-height:1.7">Your NexusBank email configuration is working correctly.<br/>
                        Emails will now be sent automatically for:<br/>
                        • Account opening<br/>• Deposits & Withdrawals<br/>• Fund Transfers</p>
                        <p style="color:rgba(255,255,255,.2);font-size:12px;margin-top:24px">© 2024 NexusBank Admin Test</p>
                        </div></body></html>""")
                    flash(f"Test email sent to {test_to}! Check inbox (may take a few seconds).", "success")

        elif action == "resend_welcome":
            acc_no = request.form.get("acc_no","").strip().upper()
            u = db.execute("SELECT * FROM users WHERE account_no=?", (acc_no,)).fetchone()
            if not u:
                flash("Account not found.", "error")
            else:
                email_welcome(u["name"], u["email"], u["account_no"],
                              u["account_type"], u["balance"], u["created_at"][:10])
                flash(f"Welcome email resent to {u['email']}!", "success")

    cfg     = get_email_config()
    users   = db.execute("SELECT account_no, name, email FROM users ORDER BY created_at DESC").fetchall()
    db.close()
    return render_template("admin_email_settings.html", cfg=cfg, users=users)

if __name__ == "__main__":
    init_db()
    print("\n" + "="*55)
    print("  🏦  NEXUS BANK — Running at http://127.0.0.1:5000")
    print("  👑  Admin Panel: http://127.0.0.1:5000/admin")
    print("  🔑  Admin Login: admin / admin123")
    print("="*55 + "\n")
    app.run(debug=True)
