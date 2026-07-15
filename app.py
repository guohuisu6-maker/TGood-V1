from flask import Flask, jsonify, request, session, redirect, url_for
import sqlite3
import os
import sys
import requests
import time
from datetime import datetime
from functools import wraps

if getattr(sys, 'frozen', False):
    RESOURCE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    APP_DIR = os.path.dirname(sys.executable)
else:
    RESOURCE_DIR = os.path.dirname(__file__)
    APP_DIR = os.path.dirname(__file__)

app = Flask(__name__, static_folder=os.path.join(RESOURCE_DIR, 'static'))

app.secret_key = os.environ.get('SECRET_KEY', 'tgood-secret-key-change-in-production')

DB_PATH = os.path.join(APP_DIR, 'data', 'stock_t.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

API_LICENCE = os.environ.get('API_LICENCE', '9B0EF33E-B966-4B2E-8C4F-D5A3785FBE6C')
API_BASE_URL = 'https://api.biyingapi.com'

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'TGood123.A')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return jsonify({'error': '需要登录'}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            market TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('base', 'buy', 'sell')),
            price REAL NOT NULL,
            shares INTEGER NOT NULL,
            round_num INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_cache (
            stock_code TEXT PRIMARY KEY,
            price REAL NOT NULL,
            change REAL NOT NULL DEFAULT 0,
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


def init_sample_data():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM stocks')
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    sample_stocks = [
        ('000001', '奔图科技', 'SZ'),
        ('002368', '太极股份', 'SZ'),
        ('603501', '豪威集团', 'SH')
    ]
    
    sample_transactions = {
        '000001': [
            ('base', 21.80, 9000, 0),
            ('buy', 20.85, 2500, 1),
            ('buy', 16.45, 4000, 2),
            ('buy', 13.71, 4500, 3),
            ('sell', 14.55, 4500, 3),
        ],
        '002368': [
            ('base', 27.28, 3000, 0),
            ('buy', 26.10, 2000, 1),
            ('buy', 16.18, 3600, 2),
            ('sell', 17.04, 3600, 2),
            ('buy', 15.02, 4400, 3),
        ],
        '603501': [
            ('base', 131.4945, 2000, 0),
            ('buy', 124.18, 800, 1),
            ('buy', 125.50, 900, 2),
            ('buy', 92.00, 1000, 3),
            ('buy', 87.70, 600, 4),
            ('sell', 90.20, 600, 4),
        ]
    }
    
    for code, name, market in sample_stocks:
        cursor.execute('INSERT INTO stocks (code, name, market) VALUES (?, ?, ?)', (code, name, market))
        stock_id = cursor.lastrowid
        for tx_type, price, shares, round_num in sample_transactions.get(code, []):
            cursor.execute('INSERT INTO transactions (stock_id, type, price, shares, round_num) VALUES (?, ?, ?, ?, ?)',
                         (stock_id, tx_type, price, shares, round_num))
    
    conn.commit()
    conn.close()


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/login')
def login_page():
    return app.send_static_file('login.html')


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['logged_in'] = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '用户名或密码错误'}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    return jsonify({'success': True})


@app.route('/api/check_login', methods=['GET'])
def check_login():
    if 'logged_in' in session:
        return jsonify({'logged_in': True})
    return jsonify({'logged_in': False})


@app.route('/api/stocks', methods=['GET'])
@login_required
def get_stocks():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM stocks ORDER BY id')
    stocks = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute('SELECT * FROM market_cache')
    market_data = {row['stock_code']: dict(row) for row in cursor.fetchall()}
    
    result = []
    for stock in stocks:
        stock_dict = dict(stock)
        market = market_data.get(stock['code'], {'price': 0, 'change': 0})
        stock_dict['price'] = market.get('price', 0)
        stock_dict['change'] = market.get('change', 0)
        result.append(stock_dict)
    
    conn.close()
    return jsonify(result)


@app.route('/api/stocks', methods=['POST'])
@login_required
def add_stock():
    data = request.json
    code = data.get('code')
    name = data.get('name')
    market = data.get('market')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('INSERT INTO stocks (code, name, market) VALUES (?, ?, ?)', (code, name, market))
        stock_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'id': stock_id})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'success': False, 'error': '股票已存在'}), 400


@app.route('/api/stocks/<int:stock_id>', methods=['DELETE'])
@login_required
def delete_stock(stock_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM stocks WHERE id = ?', (stock_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return jsonify({'success': affected > 0})


@app.route('/api/stocks/<int:stock_id>/transactions', methods=['GET'])
@login_required
def get_transactions(stock_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions WHERE stock_id = ? ORDER BY round_num, created_at', (stock_id,))
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(transactions)


@app.route('/api/stocks/<int:stock_id>/transactions', methods=['POST'])
@login_required
def add_transaction(stock_id):
    data = request.json
    tx_type = data.get('type')
    price = data.get('price')
    shares = data.get('shares')
    round_num = data.get('round_num')
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO transactions (stock_id, type, price, shares, round_num)
        VALUES (?, ?, ?, ?, ?)
    ''', (stock_id, tx_type, price, shares, round_num))
    
    conn.commit()
    tx_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'success': True, 'id': tx_id})


@app.route('/api/transactions/<int:tx_id>', methods=['DELETE'])
@login_required
def delete_transaction(tx_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transactions WHERE id = ?', (tx_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return jsonify({'success': affected > 0})


@app.route('/api/stocks/<int:stock_id>/summary', methods=['GET'])
@login_required
def get_stock_summary(stock_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM stocks WHERE id = ?', (stock_id,))
    stock_row = cursor.fetchone()
    if not stock_row:
        conn.close()
        return jsonify({'error': '股票不存在'}), 404
    stock = dict(stock_row)
    
    cursor.execute('SELECT * FROM transactions WHERE stock_id = ? ORDER BY round_num, created_at', (stock_id,))
    transactions = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute('SELECT * FROM market_cache WHERE stock_code = ?', (stock['code'],))
    market_row = cursor.fetchone()
    if market_row:
        market = dict(market_row)
    else:
        market = {'price': 0, 'change': 0}
    
    conn.close()
    
    total_buy_shares = 0
    total_buy_amount = 0
    total_sell_shares = 0
    total_sell_amount = 0
    total_profit = 0
    
    for tx in transactions:
        if tx['type'] in ('base', 'buy'):
            total_buy_shares += tx['shares']
            total_buy_amount += tx['price'] * tx['shares']
        elif tx['type'] == 'sell':
            total_sell_shares += tx['shares']
            total_sell_amount += tx['price'] * tx['shares']
            
            for buy_tx in transactions:
                if buy_tx['round_num'] == tx['round_num'] and buy_tx['type'] in ('base', 'buy'):
                    total_profit += (tx['price'] * tx['shares']) - (buy_tx['price'] * buy_tx['shares'])
                    break
    
    hold_shares = total_buy_shares - total_sell_shares
    total_cost = total_buy_amount - total_sell_amount
    current_price = market.get('price', 0)
    current_value = hold_shares * current_price if current_price > 0 else 0
    total_profit_final = current_value - total_cost
    avg_cost = total_cost / hold_shares if hold_shares > 0 else 0
    profit_rate = (total_profit_final / total_cost) * 100 if total_cost > 0 else 0
    
    cost_after_t = total_cost - total_profit
    profit_after_t = current_value - cost_after_t
    avg_cost_after_t = cost_after_t / hold_shares if hold_shares > 0 else 0
    profit_rate_after_t = (profit_after_t / cost_after_t) * 100 if cost_after_t > 0 else 0
    
    return jsonify({
        'stock': stock,
        'transactions': transactions,
        'market': market,
        'summary': {
            'total_buy_shares': total_buy_shares,
            'total_buy_amount': total_buy_amount,
            'total_sell_shares': total_sell_shares,
            'total_sell_amount': total_sell_amount,
            'total_profit': total_profit,
            'hold_shares': hold_shares,
            'total_cost': total_cost,
            'current_value': current_value,
            'total_profit_final': total_profit_final,
            'avg_cost': avg_cost,
            'profit_rate': profit_rate,
            'cost_after_t': cost_after_t,
            'profit_after_t': profit_after_t,
            'avg_cost_after_t': avg_cost_after_t,
            'profit_rate_after_t': profit_rate_after_t
        }
    })


@app.route('/api/overview', methods=['GET'])
@login_required
def get_overview():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM stocks')
    stocks = [dict(row) for row in cursor.fetchall()]
    
    total_cost = 0
    total_current_value = 0
    total_profit = 0
    total_cost_after_t = 0
    total_profit_after_t = 0
    
    for stock in stocks:
        cursor.execute('SELECT * FROM transactions WHERE stock_id = ?', (stock['id'],))
        transactions = [dict(row) for row in cursor.fetchall()]
        
        stock_total_buy_amount = 0
        stock_total_sell_amount = 0
        stock_total_profit = 0
        hold_shares = 0
        
        for tx in transactions:
            if tx['type'] in ('base', 'buy'):
                stock_total_buy_amount += tx['price'] * tx['shares']
                hold_shares += tx['shares']
            elif tx['type'] == 'sell':
                stock_total_sell_amount += tx['price'] * tx['shares']
                hold_shares -= tx['shares']
        
        rounds = {}
        for tx in transactions:
            round_num = tx['round_num']
            if round_num not in rounds:
                rounds[round_num] = {'buy': None, 'sell': None}
            if tx['type'] in ('base', 'buy'):
                rounds[round_num]['buy'] = tx
            elif tx['type'] == 'sell':
                rounds[round_num]['sell'] = tx
        
        for round_num in rounds:
            round_data = rounds[round_num]
            if round_data['buy'] and round_data['sell']:
                buy_amount = round_data['buy']['price'] * round_data['buy']['shares']
                sell_amount = round_data['sell']['price'] * round_data['sell']['shares']
                stock_total_profit += sell_amount - buy_amount
        
        stock_total_cost = stock_total_buy_amount - stock_total_sell_amount
        total_cost += stock_total_cost
        
        stock_cost_after_t = stock_total_cost - stock_total_profit
        total_cost_after_t += stock_cost_after_t
        
        cursor.execute('SELECT price FROM market_cache WHERE stock_code = ?', (stock['code'],))
        market_row = cursor.fetchone()
        market_price = market_row['price'] if market_row else 0
        
        current_value = market_price * hold_shares
        total_current_value += current_value
        total_profit += current_value - stock_total_cost
        total_profit_after_t += current_value - stock_cost_after_t
    
    conn.close()
    
    total_profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else 0
    total_profit_rate_after_t = (total_profit_after_t / total_cost_after_t * 100) if total_cost_after_t > 0 else 0
    
    return jsonify({
        'total_cost': total_cost,
        'total_current_value': total_current_value,
        'total_profit': total_profit,
        'total_profit_rate': total_profit_rate,
        'stock_count': len(stocks),
        'total_cost_after_t': total_cost_after_t,
        'total_profit_after_t': total_profit_after_t,
        'total_profit_rate_after_t': total_profit_rate_after_t
    })


@app.route('/api/market/query', methods=['GET'])
@login_required
def query_stock_info():
    code = request.args.get('code', '')
    url = f'{API_BASE_URL}/hslt/list/{API_LICENCE}'
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            stock_list = response.json()
            for stock in stock_list:
                if stock['dm'] == code or stock['dm'] == f'{code}.SH' or stock['dm'] == f'{code}.SZ':
                    return jsonify({
                        'code': stock['dm'].split('.')[0],
                        'name': stock['mc'],
                        'market': stock['jys'].upper()
                    })
    except Exception as e:
        pass
    return jsonify({'error': '股票未找到'}), 404


@app.route('/api/market/price', methods=['GET'])
@login_required
def get_stock_price():
    code = request.args.get('code', '')
    url = f'{API_BASE_URL}/hsrl/ssjy/{code}/{API_LICENCE}'
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'price': data.get('p', 0),
                'change': data.get('pc', 0),
                'update_time': data.get('t', '')
            })
    except Exception as e:
        pass
    return jsonify({'error': '获取价格失败'}), 500


@app.route('/api/market/refresh', methods=['POST'])
@login_required
def refresh_market():
    codes = request.json.get('codes', [])
    
    conn = get_db()
    cursor = conn.cursor()
    
    results = {}
    for code in codes:
        url = f'{API_BASE_URL}/hsrl/ssjy/{code}/{API_LICENCE}'
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                price = data.get('p', 0)
                change = data.get('pc', 0)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO market_cache (stock_code, price, change, update_time)
                    VALUES (?, ?, ?, ?)
                ''', (code, price, change, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                
                results[code] = {'price': price, 'change': change}
        except Exception:
            pass
        time.sleep(0.5)
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'data': results})


@app.route('/api/export', methods=['GET'])
@login_required
def export_data():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM stocks ORDER BY id')
    stocks = [dict(row) for row in cursor.fetchall()]
    
    transactions_dict = {}
    for stock in stocks:
        cursor.execute('SELECT * FROM transactions WHERE stock_id = ? ORDER BY round_num', (stock['id'],))
        transactions_dict[stock['id']] = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'stocks': stocks,
        'transactions': transactions_dict
    })


if __name__ == '__main__' or getattr(sys, 'frozen', False):
    init_db()
    init_sample_data()
    app.run(host='0.0.0.0', port=5000, debug=False)