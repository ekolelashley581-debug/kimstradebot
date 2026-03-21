"""
KIM'S TRADE BOT – ULTIMATE PROFESSIONAL EDITION
Multi-country, multi-language, full payments, admin transfers
"""

from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from functools import wraps
import sqlite3
from datetime import datetime, timedelta
import hashlib
import os
import subprocess
import json
import requests
import threading
import time
import uuid

app = Flask(__name__)
app.secret_key = "5ee54608761f4af8a367f550af2c86d9"
CORS(app, supports_credentials=True)

# Get port from environment variable (Render sets this automatically)
port = int(os.environ.get('PORT', 5000))

# ============================================
# CONFIGURATION – CHANGE THESE!
# ============================================

class Config:
    # Get the directory where this script is located
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BOT_PATH = r'C:\Users\USER\Desktop\TradingBot\version 2\TradingBot.V2.exe'  # Only works locally
    FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
    DB_PATH = os.path.join(BASE_DIR, 'database', 'kims_bot.db')
    
    # Admin email (only you)
    ADMIN_EMAIL = "mikyjones3225@gmail.com"
    
    
    
    # Supported countries with local payment
    COUNTRIES = {
        'CM': {
            'name': 'Cameroon',
            'flag': '🇨🇲',
            'currency': 'XAF',
            'lang': 'fr',
            'premium': 5000,
            'pro': 15000,
            'mtn_key': 'YOUR_CM_KEY',
            'mtn_secret': 'YOUR_CM_SECRET',
            'mtn_number': '67XXXXXX'
        },
        'NG': {
            'name': 'Nigeria',
            'flag': '🇳🇬',
            'currency': 'NGN',
            'lang': 'en',
            'premium': 5000,
            'pro': 15000,
            'mtn_key': 'YOUR_NG_KEY',
            'mtn_secret': 'YOUR_NG_SECRET',
            'mtn_number': '080XXXXXXX'
        },
        'ZA': {
            'name': 'South Africa',
            'flag': '🇿🇦',
            'currency': 'ZAR',
            'lang': 'en',
            'premium': 150,
            'pro': 450,
            'mtn_key': 'YOUR_ZA_KEY',
            'mtn_secret': 'YOUR_ZA_SECRET',
            'mtn_number': '07XXXXXXXX'
        },
        'GH': {
            'name': 'Ghana',
            'flag': '🇬🇭',
            'currency': 'GHS',
            'lang': 'en',
            'premium': 100,
            'pro': 300,
            'mtn_key': 'YOUR_GH_KEY',
            'mtn_secret': 'YOUR_GH_SECRET',
            'mtn_number': '054XXXXXXX'
        },
        'KE': {
            'name': 'Kenya',
            'flag': '🇰🇪',
            'currency': 'KES',
            'lang': 'en',
            'premium': 500,
            'pro': 1500,
            'mpesa_key': 'YOUR_KE_KEY',
            'mpesa_secret': 'YOUR_KE_SECRET',
            'mpesa_number': '07XXXXXXXX'
        }
    }
    
    # Recommended news sources (RSS)
    RECOMMENDED_SOURCES = [
        {'name': 'CoinDesk', 'url': 'https://www.coindesk.com/feed', 'category': 'crypto', 'icon': '₿', 'lang': 'en'},
        {'name': 'Reuters', 'url': 'https://www.reuters.com/feeds/marketsNews', 'category': 'finance', 'icon': '🌐', 'lang': 'en'},
        {'name': 'Bloomberg', 'url': 'https://feeds.bloomberg.com/markets/news.rss', 'category': 'finance', 'icon': '📈', 'lang': 'en'},
        {'name': 'Le Monde', 'url': 'https://www.lemonde.fr/economie/rss_full.xml', 'category': 'finance', 'icon': '🇫🇷', 'lang': 'fr'},
        {'name': 'Jeune Afrique', 'url': 'https://www.jeuneafrique.com/rss', 'category': 'africa', 'icon': '🌍', 'lang': 'fr'}
    ]

config = Config()

# ============================================
# DATABASE
# ============================================

def init_db():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, 
                  email TEXT UNIQUE, 
                  password TEXT,
                  phone TEXT,
                  country TEXT DEFAULT 'CM',
                  lang TEXT DEFAULT 'en',
                  tier TEXT DEFAULT 'free_trial',
                  trial_start TEXT,
                  trial_end TEXT,
                  subscription_start TEXT,
                  subscription_end TEXT,
                  created_at TEXT,
                  last_login TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS payments
                 (id INTEGER PRIMARY KEY, 
                  transaction_id TEXT UNIQUE, 
                  user_id INTEGER,
                  amount INTEGER,
                  currency TEXT,
                  phone TEXT,
                  country TEXT,
                  status TEXT,
                  plan TEXT,
                  created_at TEXT,
                  completed_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS support_messages
                 (id INTEGER PRIMARY KEY, 
                  user_id INTEGER, 
                  message TEXT,
                  status TEXT DEFAULT 'unread', 
                  created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_sources
                 (id INTEGER PRIMARY KEY, 
                  user_id INTEGER, 
                  source_name TEXT,
                  source_url TEXT,
                  category TEXT,
                  added_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS admin_transfers
                 (id INTEGER PRIMARY KEY,
                  amount INTEGER,
                  destination TEXT,
                  account_details TEXT,
                  status TEXT,
                  created_at TEXT,
                  completed_at TEXT)''')
    
    conn.commit()
    conn.close()

# ============================================
# UTILS
# ============================================

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'error': 'Unauthorized'}), 403
        return f(*args, **kwargs)
    return decorated

# ============================================
# SERVE FILES
# ============================================

@app.route('/')
def serve_index():
    return send_from_directory(config.FRONTEND_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_file(filename):
    return send_from_directory(config.FRONTEND_DIR, filename)

@app.route('/favicon.ico')
def favicon():
    return '', 204

# ============================================
# AUTHENTICATION
# ============================================

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    phone = data.get('phone', '')
    country = data.get('country', 'CM')
    lang = data.get('lang', 'en')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT id FROM users WHERE email=?", (email,))
        if c.fetchone():
            return jsonify({'error': 'Email exists'}), 400
        
        now = datetime.now()
        trial_end = now + timedelta(days=7)
        c.execute('''INSERT INTO users 
                     (email, password, phone, country, lang, tier, trial_start, trial_end, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (email, hash_password(password), phone, country, lang, 'free_trial',
                   now.isoformat(), trial_end.isoformat(), now.isoformat()))
        conn.commit()
        return jsonify({'message': 'User created', 'trial_end': trial_end.isoformat()}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, tier, phone, country, lang FROM users WHERE email=? AND password=?",
              (email, hash_password(password)))
    user = c.fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user[0]
        session['email'] = email
        session['tier'] = user[1]
        session['phone'] = user[2] or ''
        session['country'] = user[3] or 'CM'
        session['lang'] = user[4] or 'en'
        session['is_admin'] = (email == config.ADMIN_EMAIL)
        return jsonify({
            'success': True, 
            'email': email, 
            'tier': user[1], 
            'country': user[3],
            'lang': user[4],
            'is_admin': session['is_admin']
        })
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/check_session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'email': session['email'],
            'tier': session['tier'],
            'country': session.get('country', 'CM'),
            'lang': session.get('lang', 'en'),
            'is_admin': session.get('is_admin', False)
        })
    return jsonify({'logged_in': False})

@app.route('/api/user/profile', methods=['GET'])
@login_required
def get_profile():
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT email, phone, country, lang, tier, created_at, trial_end, subscription_end
                 FROM users WHERE id=?''', (session['user_id'],))
    user = c.fetchone()
    conn.close()
    
    return jsonify({
        'email': user[0],
        'phone': user[1] or '',
        'country': user[2],
        'lang': user[3],
        'tier': user[4],
        'joined': user[5],
        'trial_end': user[6],
        'subscription_end': user[7]
    })

@app.route('/api/user/update', methods=['POST'])
@login_required
def update_profile():
    data = request.json
    phone = data.get('phone')
    lang = data.get('lang')
    
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    if phone:
        c.execute("UPDATE users SET phone=? WHERE id=?", (phone, session['user_id']))
    if lang:
        c.execute("UPDATE users SET lang=? WHERE id=?", (lang, session['user_id']))
        session['lang'] = lang
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ============================================
# MARKET ANALYSIS (C++ Bot - Hidden from UI)
# ============================================

@app.route('/api/analyze', methods=['POST'])
@login_required
def analyze():
    if not os.path.exists(config.BOT_PATH):
        return jsonify({'result': 'Analysis engine initializing...'})
    
    try:
        result = subprocess.run([config.BOT_PATH], capture_output=True, text=True, timeout=30)
        output = result.stdout if result.returncode == 0 else result.stderr
        return jsonify({'success': True, 'result': output})
    except Exception as e:
        return jsonify({'result': f'Analysis in progress...'})

# ============================================
# AI NEWS ANALYSIS (Professional Format)
# ============================================

@app.route('/api/ai-news', methods=['POST'])
@login_required
def ai_news():
    # In production, this would use OpenAI
    # For now, return professional mock data
    return jsonify({
        'pairs': [
            {
                'pair': 'BTCUSD',
                'signal': 'BUY',
                'confidence': 92,
                'reason': 'Bullish momentum, strong support at $72k',
                'color': 'success'
            },
            {
                'pair': 'ETHUSD',
                'signal': 'BUY',
                'confidence': 87,
                'reason': 'Ecosystem growth, institutional interest',
                'color': 'success'
            },
            {
                'pair': 'EURUSD',
                'signal': 'WAIT',
                'confidence': 45,
                'reason': 'Mixed signals from ECB, wait for clarity',
                'color': 'warning'
            },
            {
                'pair': 'GBPUSD',
                'signal': 'SELL',
                'confidence': 68,
                'reason': 'Resistance at key level, overbought',
                'color': 'danger'
            },
            {
                'pair': 'XAUUSD',
                'signal': 'BUY',
                'confidence': 88,
                'reason': 'Safe haven demand, geopolitical tensions',
                'color': 'success'
            }
        ]
    })

# ============================================
# NEWS SOURCES
# ============================================

@app.route('/api/recommended-sources', methods=['GET'])
def get_recommended_sources():
    lang = request.args.get('lang', 'en')
    # Filter by language
    sources = [s for s in config.RECOMMENDED_SOURCES if s['lang'] == lang]
    return jsonify(sources)

@app.route('/api/user/sources', methods=['GET', 'POST'])
@login_required
def user_sources():
    if request.method == 'POST':
        data = request.json
        conn = sqlite3.connect(config.DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO user_sources (user_id, source_name, source_url, category, added_at)
                     VALUES (?, ?, ?, ?, ?)''',
                  (session['user_id'], data['name'], data['url'], data.get('category', 'custom'),
                   datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT source_name, source_url, category FROM user_sources WHERE user_id=?''', (session['user_id'],))
    sources = c.fetchall()
    conn.close()
    return jsonify({'sources': [{'name': s[0], 'url': s[1], 'category': s[2]} for s in sources]})

# ============================================
# REAL-TIME NEWS FROM API
# ============================================

@app.route('/api/news', methods=['GET'])
def get_news():
    """Get real-time news from NewsAPI"""
    category = request.args.get('category', 'business')
    lang = request.args.get('lang', 'en')
    
    # NewsAPI endpoint
    url = "https://newsapi.org/v2/top-headlines"
    
    params = {
        'category': category,
        'language': lang,
        'apiKey': NEWS_API_KEY,
        'pageSize': 10
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('status') == 'ok':
            articles = []
            for article in data.get('articles', []):
                articles.append({
                    'title': article.get('title', ''),
                    'source': article.get('source', {}).get('name', ''),
                    'url': article.get('url', ''),
                    'publishedAt': article.get('publishedAt', ''),
                    'description': article.get('description', '')
                })
            return jsonify({'success': True, 'articles': articles})
        else:
            return jsonify({'success': False, 'error': data.get('message', 'API error')})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/news/search', methods=['POST'])
def search_news():
    """Search for news by keyword"""
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({'success': False, 'error': 'No search query'})
    
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': query,
        'apiKey': NEWS_API_KEY,
        'pageSize': 10
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('status') == 'ok':
            articles = []
            for article in data.get('articles', []):
                articles.append({
                    'title': article.get('title', ''),
                    'source': article.get('source', {}).get('name', ''),
                    'url': article.get('url', ''),
                    'publishedAt': article.get('publishedAt', ''),
                    'description': article.get('description', '')
                })
            return jsonify({'success': True, 'articles': articles})
        else:
            return jsonify({'success': False, 'error': data.get('message', 'API error')})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# SUPPORT CHAT
# ============================================

@app.route('/api/support/send', methods=['POST'])
@login_required
def send_support():
    msg = request.json.get('message')
    if not msg:
        return jsonify({'error': 'Message required'}), 400
    
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO support_messages (user_id, message, created_at)
                 VALUES (?, ?, ?)''', (session['user_id'], msg, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/support/messages', methods=['GET'])
@admin_required
def get_support_messages():
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT u.email, s.message, s.created_at, s.status
                 FROM support_messages s JOIN users u ON s.user_id = u.id
                 ORDER BY s.created_at DESC''')
    messages = c.fetchall()
    conn.close()
    return jsonify({'messages': [{'user': m[0], 'message': m[1], 'time': m[2], 'status': m[3]} for m in messages]})

# ============================================
# PAYMENTS
# ============================================

@app.route('/api/countries', methods=['GET'])
def get_countries():
    return jsonify({code: {
        'name': info['name'],
        'flag': info['flag'],
        'currency': info['currency'],
        'premium': info['premium'],
        'pro': info['pro']
    } for code, info in config.COUNTRIES.items()})

@app.route('/api/payment/request', methods=['POST'])
@login_required
def payment_request():
    data = request.json
    plan = data.get('plan')
    phone = data.get('phone')
    country = session.get('country', 'CM')
    
    if country not in config.COUNTRIES:
        return jsonify({'error': 'Invalid country'}), 400
    
    country_info = config.COUNTRIES[country]
    amount = country_info['premium'] if plan == 'premium' else country_info['pro']
    currency = country_info['currency']
    tid = f"KIM_{session['user_id']}_{int(time.time())}"
    
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO payments (transaction_id, user_id, amount, currency, phone, country, status, plan, created_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (tid, session['user_id'], amount, currency, phone, country, 'PENDING', plan, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    # Simulate payment processing
    def process_payment():
        time.sleep(3)
        conn = sqlite3.connect(config.DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE payments SET status='SUCCESSFUL', completed_at=? WHERE transaction_id=?", 
                  (datetime.now().isoformat(), tid))
        
        now = datetime.now()
        sub_end = now + timedelta(days=30)
        c.execute("UPDATE users SET tier=?, subscription_start=?, subscription_end=? WHERE id=?",
                  (plan, now.isoformat(), sub_end.isoformat(), session['user_id']))
        conn.commit()
        conn.close()
    
    threading.Thread(target=process_payment).start()
    
    return jsonify({'success': True, 'tid': tid})

@app.route('/api/payment/status/<tid>', methods=['GET'])
@login_required
def payment_status(tid):
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status FROM payments WHERE transaction_id=?", (tid,))
    status = c.fetchone()
    conn.close()
    return jsonify({'status': status[0] if status else 'not found'})

@app.route('/api/user/payments', methods=['GET'])
@login_required
def user_payments():
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT amount, currency, plan, created_at, status FROM payments 
                 WHERE user_id=? AND status='SUCCESSFUL' ORDER BY created_at DESC''', (session['user_id'],))
    payments = c.fetchall()
    conn.close()
    return jsonify({'payments': [{'amount': p[0], 'currency': p[1], 'plan': p[2], 'date': p[3]} for p in payments]})

# ============================================
# ADMIN PANEL – Professional with Transfers
# ============================================

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    
    # User stats
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE tier IN ('premium','pro')")
    paid_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE tier='free_trial'")
    trial_users = c.fetchone()[0]
    
    # Payment stats
    c.execute("SELECT SUM(amount) FROM payments WHERE status='SUCCESSFUL'")
    total_revenue = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(amount) FROM payments WHERE status='SUCCESSFUL' AND created_at > date('now', '-30 days')")
    monthly_revenue = c.fetchone()[0] or 0
    
    # Recent payments
    c.execute('''SELECT u.email, p.amount, p.currency, p.plan, p.created_at 
                 FROM payments p JOIN users u ON p.user_id = u.id 
                 WHERE p.status='SUCCESSFUL' ORDER BY p.created_at DESC LIMIT 10''')
    payments = c.fetchall()
    
    # All users
    c.execute('''SELECT id, email, tier, country, created_at, last_login FROM users ORDER BY created_at DESC''')
    users = c.fetchall()
    
    # Support messages
    c.execute("SELECT COUNT(*) FROM support_messages WHERE status='unread'")
    unread_support = c.fetchone()[0]
    
    # Transfer history
    c.execute('''SELECT amount, destination, status, created_at FROM admin_transfers ORDER BY created_at DESC LIMIT 10''')
    transfers = c.fetchall()
    
    conn.close()
    
    return jsonify({
        'stats': {
            'total_users': total_users,
            'paid_users': paid_users,
            'trial_users': trial_users,
            'total_revenue': total_revenue,
            'monthly_revenue': monthly_revenue,
            'unread_support': unread_support
        },
        'payments': [{'user': p[0], 'amount': p[1], 'currency': p[2], 'plan': p[3], 'date': p[4]} for p in payments],
        'users': [{'id': u[0], 'email': u[1], 'tier': u[2], 'country': u[3], 'joined': u[4], 'last_login': u[5]} for u in users],
        'transfers': [{'amount': t[0], 'destination': t[1], 'status': t[2], 'date': t[3]} for t in transfers]
    })

@app.route('/api/admin/upgrade', methods=['POST'])
@admin_required
def admin_upgrade():
    data = request.json
    user_id = data.get('user_id')
    plan = data.get('plan')
    
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    now = datetime.now()
    sub_end = now + timedelta(days=30)
    c.execute("UPDATE users SET tier=?, subscription_start=?, subscription_end=? WHERE id=?",
              (plan, now.isoformat(), sub_end.isoformat(), user_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/transfer', methods=['POST'])
@admin_required
def admin_transfer():
    data = request.json
    amount = data.get('amount')
    destination = data.get('destination')  # 'bank' or 'momo'
    account_details = data.get('account_details', {})
    
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO admin_transfers (amount, destination, account_details, status, created_at)
                 VALUES (?, ?, ?, ?, ?)''',
              (amount, destination, json.dumps(account_details), 'pending', datetime.now().isoformat()))
    transfer_id = c.lastrowid
    conn.commit()
    conn.close()
    
    # In production, would call actual payment API here
    # For demo, we'll simulate success
    def process_transfer():
        time.sleep(2)
        conn = sqlite3.connect(config.DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE admin_transfers SET status='completed', completed_at=? WHERE id=?",
                  (datetime.now().isoformat(), transfer_id))
        conn.commit()
        conn.close()
    
    threading.Thread(target=process_transfer).start()
    
    return jsonify({'success': True, 'transfer_id': transfer_id})

@app.route('/api/admin/support/mark-read', methods=['POST'])
@admin_required
def mark_support_read():
    data = request.json
    message_id = data.get('message_id')
    
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE support_messages SET status='read' WHERE id=?", (message_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ============================================
# MANUAL PAYMENT SYSTEM (ADD THIS ENTIRE BLOCK)
# ============================================

@app.route('/api/payment/request-manual', methods=['POST'])
@login_required
def payment_request_manual():
    """Store payment request for admin approval"""
    data = request.json
    plan = data.get('plan')
    amount = data.get('amount')
    currency = data.get('currency')
    method = data.get('method')
    details = data.get('details', {})
    
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    
    # Create payment_requests table if not exists
    c.execute('''CREATE TABLE IF NOT EXISTS payment_requests
                 (id INTEGER PRIMARY KEY,
                  user_id INTEGER,
                  user_email TEXT,
                  plan TEXT,
                  amount INTEGER,
                  currency TEXT,
                  payment_method TEXT,
                  payment_details TEXT,
                  status TEXT DEFAULT 'pending',
                  created_at TEXT,
                  approved_at TEXT)''')
    
    tid = f"REQ_{session['user_id']}_{int(time.time())}"
    
    c.execute('''INSERT INTO payment_requests 
                 (user_id, user_email, plan, amount, currency, payment_method, payment_details, status, created_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (session['user_id'], session['email'], plan, amount, currency, method, 
               json.dumps(details), 'pending', datetime.now().isoformat()))
    
    # Also add to support messages for admin notification
    admin_msg = f"💰 NEW PAYMENT REQUEST!\nUser: {session['email']}\nPlan: {plan}\nAmount: {amount} {currency}\nMethod: {method}\nDetails: {json.dumps(details)}"
    c.execute('''INSERT INTO support_messages (user_id, message, status, created_at)
                 VALUES (?, ?, ?, ?)''',
              (0, admin_msg, 'unread', datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Payment request submitted'})

@app.route('/api/admin/payment-requests', methods=['GET'])
@admin_required
def get_payment_requests():
    """Get all payment requests for admin"""
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, user_email, plan, amount, currency, payment_method, payment_details, status, created_at
                 FROM payment_requests ORDER BY created_at DESC''')
    requests = c.fetchall()
    conn.close()
    
    return jsonify({'requests': [{
        'id': r[0],
        'user': r[1],
        'plan': r[2],
        'amount': r[3],
        'currency': r[4],
        'method': r[5],
        'details': json.loads(r[6]) if r[6] else {},
        'status': r[7],
        'created_at': r[8]
    } for r in requests]})

@app.route('/api/admin/payment-approve', methods=['POST'])
@admin_required
def approve_payment():
    """Approve a payment request and upgrade user"""
    data = request.json
    request_id = data.get('request_id')
    
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    
    # Get the request details
    c.execute("SELECT user_id, plan FROM payment_requests WHERE id=?", (request_id,))
    req = c.fetchone()
    
    if req:
        user_id, plan = req
        
        # Update user's tier
        now = datetime.now()
        sub_end = now + timedelta(days=30)
        c.execute("UPDATE users SET tier=?, subscription_start=?, subscription_end=? WHERE id=?",
                  (plan, now.isoformat(), sub_end.isoformat(), user_id))
        
        # Update request status
        c.execute("UPDATE payment_requests SET status='approved', approved_at=? WHERE id=?", 
                  (datetime.now().isoformat(), request_id))
        
        conn.commit()
        
        # Notify user via support messages
        c.execute('''INSERT INTO support_messages (user_id, message, status, created_at)
                     VALUES (?, ?, ?, ?)''',
                  (user_id, f"✅ Your {plan} subscription has been activated! Thank you for your payment.", 
                   'unread', datetime.now().isoformat()))
        conn.commit()
    
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/payment-reject', methods=['POST'])
@admin_required
def reject_payment():
    """Reject a payment request"""
    data = request.json
    request_id = data.get('request_id')
    
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE payment_requests SET status='rejected' WHERE id=?", (request_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# ============================================
# MARKET IDEAS ROUTES (ADD THIS)
# ============================================

@app.route('/api/ideas', methods=['GET'])
def get_ideas():
    """Get all market ideas from users"""
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS market_ideas
                 (id INTEGER PRIMARY KEY,
                  user_id INTEGER,
                  user_email TEXT,
                  title TEXT,
                  description TEXT,
                  created_at TEXT)''')
    c.execute("SELECT id, user_email, title, description, created_at FROM market_ideas ORDER BY created_at DESC")
    ideas = c.fetchall()
    conn.close()
    
    return jsonify({'ideas': [{
        'id': i[0],
        'user_email': i[1],
        'title': i[2],
        'description': i[3],
        'created_at': i[4]
    } for i in ideas]})

@app.route('/api/ideas/submit', methods=['POST'])
@login_required
def submit_idea():
    """Submit a new market idea"""
    data = request.json
    title = data.get('title')
    description = data.get('description')
    
    if not title or not description:
        return jsonify({'error': 'Title and description required'}), 400
    
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS market_ideas
                 (id INTEGER PRIMARY KEY,
                  user_id INTEGER,
                  user_email TEXT,
                  title TEXT,
                  description TEXT,
                  created_at TEXT)''')
    
    c.execute('''INSERT INTO market_ideas (user_id, user_email, title, description, created_at)
                 VALUES (?, ?, ?, ?, ?)''',
              (session['user_id'], session['email'], title, description, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# ============================================
# FOR RENDER - COMMENT OUT LOCAL DEVELOPMENT SECTION
# ============================================

# The following section is for LOCAL DEVELOPMENT only
# On Render, gunicorn serves the app directly

# ============================================
# FOR RENDER - FIXED VERSION
# ============================================

if __name__ == '__main__':
    # This code ONLY runs when you execute python directly (local development)
    os.makedirs(config.FRONTEND_DIR, exist_ok=True)
    init_db()
    print("="*70)
    print("🚀 KIM'S TRADE BOT - LOCAL DEVELOPMENT MODE")
    print("="*70)
    print(f"👤 Admin: {config.ADMIN_EMAIL}")
    print(f"🌍 Countries: {', '.join(config.COUNTRIES.keys())}")
    print("="*70)
    print("🌐 http://localhost:5000")
    print("👑 Admin: http://localhost:5000/admin.html")
    print("="*70)
    app.run(host='0.0.0.0', port=port, debug=True)
else:
    # This runs on Render - initialize the database
    print("🚀 Starting on Render - Initializing database...")
    init_db()
    print("✅ Database ready!")
    print("👑 Admin: http://localhost:5000/admin.html")
    print("="*70)
    app.run(host='0.0.0.0', port=5000, debug=True)
