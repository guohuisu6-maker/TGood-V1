from flask import Flask, jsonify, request, session, redirect, url_for
import sqlite3
import os
import sys
import requests
import time
from datetime import datetime
from functools import wraps

APP_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(APP_DIR, 'data', 'stock_t.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

API_LICENCE = os.environ.get('API_LICENCE', '9B0EF33E-B966-4B2E-8C4F-D5A3785FBE6C')
API_BASE_URL = 'https://api.biyingapi.com'
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'TGood123.A')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'tgood-secret-key-change-in-production')


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


LOGIN_HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智T盈 - 登录</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        :root { --primary: #0070C0; --success: #00B050; --danger: #C00000; --bg: #F8F9FA; --card: #FFFFFF; }
        body { background: var(--bg); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
        .login-card { background: var(--card); border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); padding: 32px; width: 100%; max-width: 420px; }
        .logo-icon { width: 64px; height: 64px; background: #003366; border-radius: 12px; margin: 0 auto 16px; display: flex; align-items: center; justify-content: center; font-size: 28px; color: white; font-weight: 700; }
        h1 { font-size: 22px; color: #003366; text-align: center; margin-bottom: 4px; }
        p { font-size: 14px; color: #6C757D; text-align: center; margin-bottom: 28px; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; font-weight: 500; margin-bottom: 8px; font-size: 14px; }
        .form-group input { width: 100%; padding: 12px 14px; border: 1px solid #DEE2E6; border-radius: 6px; font-size: 15px; }
        .form-group input:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(0,112,192,0.1); }
        .btn { width: 100%; padding: 12px; border: none; border-radius: 6px; font-size: 15px; font-weight: 500; cursor: pointer; }
        .btn-primary { background: var(--primary); color: white; }
        .btn-primary:hover { background: #005A9E; }
        .btn-primary:disabled { background: #94C0E4; cursor: not-allowed; }
        .loading { display: inline-block; width: 18px; height: 18px; border: 2px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: white; animation: spin 0.8s infinite; vertical-align: middle; margin-right: 8px; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .toast { position: fixed; top: 20px; right: 20px; padding: 12px 20px; border-radius: 6px; color: white; z-index: 1000; display: none; }
        .toast.error { background: var(--danger); }
        .toast.success { background: var(--success); }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="logo-icon">智T</div>
        <h1>智T盈 - 智能做T盈利助手</h1>
        <p>请登录您的账户</p>
        <div class="form-group">
            <label>用户名</label>
            <input type="text" id="username" placeholder="请输入用户名">
        </div>
        <div class="form-group">
            <label>密码</label>
            <input type="password" id="password" placeholder="请输入密码">
        </div>
        <button class="btn btn-primary" id="loginBtn" onclick="handleLogin()">登 录</button>
        <p style="margin-top: 20px; font-size: 13px;">© 2026 智T盈</p>
    </div>
    <div class="toast" id="toast"></div>
    <script>
        async function handleLogin() {
            const u = document.getElementById('username').value.trim();
            const p = document.getElementById('password').value.trim();
            if (!u || !p) { alert('请输入用户名和密码'); return; }
            const btn = document.getElementById('loginBtn');
            btn.disabled = true; btn.innerHTML = '<span class="loading"></span>登录中...';
            try {
                const r = await fetch('/api/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: u, password: p}) });
                const d = await r.json();
                if (d.success) { window.location.href = '/'; }
                else { alert(d.error || '登录失败'); }
            } catch(e) { alert('网络错误'); }
            finally { btn.disabled = false; btn.innerHTML = '登 录'; }
        }
        document.addEventListener('keydown', e => { if (e.key === 'Enter') handleLogin(); });
    </script>
</body>
</html>'''


INDEX_HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智T盈 - 智能做T盈利助手</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        :root { --primary: #0070C0; --dark: #003366; --success: #00B050; --danger: #C00000; --bg: #F8F9FA; --card: #FFFFFF; --border: #DEE2E6; }
        body { background: var(--bg); padding: 20px; }
        .header { background: var(--dark); color: white; padding: 16px 24px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
        .header h1 { font-size: 24px; }
        .nav-buttons { display: flex; gap: 8px; flex-wrap: wrap; }
        .btn { padding: 8px 16px; border: none; border-radius: 4px; font-size: 14px; cursor: pointer; }
        .btn-primary { background: var(--primary); color: white; }
        .btn-outline { background: transparent; color: white; border: 1px solid rgba(255,255,255,0.5); }
        .btn-danger { background: #C00000; color: white; }
        .main-container { display: grid; gap: 20px; }
        .card { background: var(--card); border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
        .card h2 { font-size: 18px; margin-bottom: 16px; color: var(--dark); }
        .stock-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
        .stock-item { border: 1px solid var(--border); border-radius: 6px; padding: 16px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
        .stock-item:hover { border-color: var(--primary); }
        .stock-item.active { background: #D9E1F2; }
        .stock-name { font-size: 16px; font-weight: 600; }
        .stock-code { font-size: 14px; color: #6C757D; }
        .price { font-size: 18px; font-weight: 600; }
        .change { font-size: 14px; padding: 2px 6px; border-radius: 3px; }
        .change.up { background: rgba(220,53,69,0.1); color: #DC3545; }
        .change.down { background: rgba(35,197,94,0.1); color: #23C55E; }
        .profit-board { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
        .board-item { background: var(--bg); border-radius: 6px; padding: 16px; border-left: 4px solid var(--primary); }
        .board-item.success { border-left-color: var(--success); }
        .board-item.danger { border-left-color: var(--danger); }
        .board-label { font-size: 14px; color: #6C757D; margin-bottom: 8px; }
        .board-value { font-size: 22px; font-weight: 600; }
        .board-item.success .board-value { color: var(--success); }
        .board-item.danger .board-value { color: var(--danger); }
        .table-wrapper { overflow-x: auto; border-radius: 6px; border: 1px solid var(--border); }
        .data-table { width: 100%; border-collapse: collapse; }
        .data-table thead { background: var(--primary); color: white; }
        .data-table th, .data-table td { padding: 12px 8px; text-align: center; border-bottom: 1px solid var(--border); }
        .data-table tfoot { background: #D9E1F2; font-weight: 600; }
        .data-table .success { color: var(--success); }
        .data-table .danger { color: var(--danger); }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; }
        .modal-content { background: var(--card); margin: 10% auto; padding: 0; border-radius: 8px; width: 90%; max-width: 500px; }
        .modal-header { padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .modal-header h3 { font-size: 18px; color: var(--dark); }
        .modal-close { background: none; border: none; font-size: 24px; cursor: pointer; }
        .modal-body { padding: 20px; }
        .modal-footer { padding: 16px 20px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 12px; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; font-weight: 500; margin-bottom: 8px; }
        .form-group input, .form-group select { width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 4px; font-size: 14px; }
        .form-group input:focus, .form-group select:focus { outline: none; border-color: var(--primary); }
        .footer { margin-top: 20px; padding: 12px 20px; background: var(--card); border-radius: 8px; display: flex; justify-content: space-between; font-size: 14px; color: #6C757D; }
        .empty-state { text-align: center; padding: 40px; color: #6C757D; }
        .loading { display: inline-block; width: 20px; height: 20px; border: 2px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: white; animation: spin 1s infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="header">
        <h1>智T盈 - 智能做T盈利助手</h1>
        <div class="nav-buttons">
            <button class="btn btn-outline" id="addStockBtn">+ 添加股票</button>
            <button class="btn btn-outline" id="refreshBtn">刷新行情</button>
            <button class="btn btn-outline" id="exportBtn">导出数据</button>
            <button class="btn btn-outline" id="importBtn">导入数据</button>
            <button class="btn btn-primary" id="addTradeBtn" disabled>新增做T</button>
            <button class="btn btn-outline" onclick="fetch('/api/logout',{method:'POST'}).then(()=>window.location.href='/login')">退出登录</button>
        </div>
    </div>
    <div class="main-container">
        <div class="card">
            <h2>持仓总览</h2>
            <div class="profit-board" id="overviewBoard">
                <div class="board-item"><span class="board-label">总成本</span><span class="board-value" id="overviewTotalCost">-</span></div>
                <div class="board-item"><span class="board-label">总市值</span><span class="board-value" id="overviewTotalValue">-</span></div>
                <div class="board-item" id="overviewProfitItem"><span class="board-label">总盈亏</span><span class="board-value" id="overviewTotalProfit">-</span></div>
                <div class="board-item" id="overviewProfitRateItem"><span class="board-label">盈亏率</span><span class="board-value" id="overviewProfitRate">-</span></div>
                <div class="board-item"><span class="board-label">总持仓</span><span class="board-value" id="overviewTotalShares">-</span></div>
                <div class="board-item" id="overviewCostAfterTItem"><span class="board-label">做T后成本</span><span class="board-value" id="overviewCostAfterT">-</span></div>
                <div class="board-item" id="overviewProfitAfterTItem"><span class="board-label">做T后盈亏</span><span class="board-value" id="overviewProfitAfterT">-</span></div>
                <div class="board-item" id="overviewProfitRateAfterTItem"><span class="board-label">做T后盈亏率</span><span class="board-value" id="overviewProfitRateAfterT">-</span></div>
            </div>
        </div>
        <div class="card">
            <h2>我的持仓股票</h2>
            <div class="stock-list" id="stockList"><div class="empty-state"><p>暂无股票，请点击"添加股票"开始使用</p></div></div>
        </div>
        <div class="card">
            <h2>做T交易记录 - <span id="currentStockName">请选择股票</span></h2>
            <div class="table-wrapper" id="tradeTableWrapper" style="display:none;"><table class="data-table" id="tradeTable"><thead><tr><th>轮次</th><th>买入单价</th><th>买入股数</th><th>买入总价</th><th>卖出单价</th><th>卖出股数</th><th>卖出总价</th><th>盈利</th><th>操作</th></tr></thead><tbody id="tradeTableBody"></tbody><tfoot id="tradeTableFoot"></tfoot></table></div>
            <div class="empty-state" id="tradeEmptyState"><p>请先选择一只股票查看交易记录</p></div>
        </div>
        <div class="card">
            <h2>盈亏核心看板 - <span id="boardStockName">请选择股票</span></h2>
            <div class="profit-board" id="profitBoard">
                <div class="board-item"><div class="board-label">总成本</div><div class="board-value" id="totalCost">¥0.00</div></div>
                <div class="board-item"><div class="board-label">现市值</div><div class="board-value" id="currentValue">¥0.00</div></div>
                <div class="board-item" id="profitBoardItem"><div class="board-label">总盈亏</div><div class="board-value" id="totalProfit">¥0.00</div></div>
                <div class="board-item"><div class="board-label">平均成本</div><div class="board-value" id="avgCost">¥0.00</div></div>
                <div class="board-item"><div class="board-label">持仓股数</div><div class="board-value" id="holdShares">0</div></div>
                <div class="board-item" id="profitRateBoardItem"><div class="board-label">盈亏率</div><div class="board-value" id="profitRate">0.00%</div></div>
                <div class="board-item" id="costAfterTBoardItem"><div class="board-label">做T后成本</div><div class="board-value" id="costAfterT">¥0.00</div></div>
                <div class="board-item" id="profitAfterTBoardItem"><div class="board-label">做T后盈亏</div><div class="board-value" id="profitAfterT">¥0.00</div></div>
                <div class="board-item" id="profitRateAfterTBoardItem"><div class="board-label">做T后盈亏率</div><div class="board-value" id="profitRateAfterT">0.00%</div></div>
            </div>
        </div>
    </div>
    <div class="footer"><div id="statusText">就绪</div><div id="updateTime">最后更新：-</div></div>
    <div class="modal" id="addStockModal">
        <div class="modal-content"><div class="modal-header"><h3>添加股票</h3><button class="modal-close" onclick="closeModal('addStockModal')">&times;</button></div>
        <div class="modal-body">
            <div class="form-group"><label>股票代码</label><input type="text" id="stockCode" placeholder="6位代码" maxlength="6"></div>
            <div class="form-group"><label>股票名称</label><input type="text" id="stockName" placeholder="名称"></div>
            <div class="form-group"><label>市场</label><select id="stockMarket"><option value="SZ">深圳 (SZ)</option><option value="SH">上海 (SH)</option></select></div>
        </div>
        <div class="modal-footer"><button class="btn btn-outline" onclick="closeModal('addStockModal')">取消</button><button class="btn btn-primary" onclick="confirmAddStock()">确定</button></div></div>
    </div>
    <div class="modal" id="addTradeModal">
        <div class="modal-content"><div class="modal-header"><h3>新增做T记录 - <span id="addTradeStockName"></span></h3><button class="modal-close" onclick="closeModal('addTradeModal')">&times;</button></div>
        <div class="modal-body">
            <div class="form-group"><label>交易类型</label><select id="tradeType"><option value="base">底仓</option><option value="buy">买入</option><option value="sell">卖出</option></select></div>
            <div class="form-group"><label>价格</label><input type="number" id="tradePrice" step="0.01" min="0"></div>
            <div class="form-group"><label>股数</label><input type="number" id="tradeShares" min="1"></div>
            <div class="form-group"><label>轮次</label><input type="number" id="tradeRound" min="0" value="0"></div>
        </div>
        <div class="modal-footer"><button class="btn btn-outline" onclick="closeModal('addTradeModal')">取消</button><button class="btn btn-primary" onclick="confirmAddTrade()">确定</button></div></div>
    </div>
    <div class="modal" id="confirmDeleteModal">
        <div class="modal-content"><div class="modal-header"><h3>确认删除</h3><button class="modal-close" onclick="closeModal('confirmDeleteModal')">&times;</button></div>
        <div class="modal-body"><p>确定要删除这条记录吗？</p></div>
        <div class="modal-footer"><button class="btn btn-outline" onclick="closeModal('confirmDeleteModal')">取消</button><button class="btn btn-primary" id="confirmDeleteBtn">确定</button></div></div>
    </div>
    <script>
        let currentStockId = null, stocks = [], deleteCallback = null;
        function fmtMoney(n) { return (n||0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
        function fmtShares(n) { return (n||0).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
        function fmtChange(n) { const p = (n||0)>=0 ? '+' : ''; return p + (n||0).toFixed(2) + '%'; }
        function setStatus(t) { document.getElementById('statusText').textContent = t; }
        function updateTime() { document.getElementById('updateTime').textContent = '最后更新：' + new Date().toLocaleString('zh-CN'); }
        async function loadOverview() { const r = await fetch('/api/overview'); const d = await r.json(); renderOverview(d); }
        function renderOverview(d) {
            const p = d.total_profit >= 0 ? 'success' : 'danger';
            document.getElementById('overviewTotalCost').textContent = '¥' + fmtMoney(d.total_cost);
            document.getElementById('overviewTotalValue').textContent = '¥' + fmtMoney(d.total_current_value);
            document.getElementById('overviewTotalProfit').textContent = (d.total_profit>=0?'+' : '') + '¥' + fmtMoney(d.total_profit);
            document.getElementById('overviewProfitRate').textContent = (d.total_profit_rate>=0?'+' : '') + (d.total_profit_rate||0).toFixed(2) + '%';
            document.getElementById('overviewTotalShares').textContent = fmtShares(d.total_hold_shares || 0) + ' 股';
            document.getElementById('overviewCostAfterT').textContent = '¥' + fmtMoney(d.total_cost_after_t);
            document.getElementById('overviewProfitAfterT').textContent = (d.total_profit_after_t>=0?'+' : '') + '¥' + fmtMoney(d.total_profit_after_t);
            document.getElementById('overviewProfitRateAfterT').textContent = (d.total_profit_rate_after_t>=0?'+' : '') + (d.total_profit_rate_after_t||0).toFixed(2) + '%';
            document.getElementById('overviewProfitItem').className = 'board-item ' + p;
            document.getElementById('overviewProfitRateItem').className = 'board-item ' + p;
        }
        async function loadStocks() {
            setStatus('加载中...');
            const r = await fetch('/api/stocks');
            stocks = await r.json();
            const list = document.getElementById('stockList');
            if (!stocks.length) { list.innerHTML = '<div class="empty-state"><p>暂无股票</p></div>'; return; }
            list.innerHTML = stocks.map(s => {
                const a = s.id === currentStockId ? 'active' : '';
                const c = s.change >= 0 ? 'up' : 'down';
                return '<div class="stock-item ' + a + '" onclick="selectStock(' + s.id + ')">' +
                    '<div><span class="stock-name">' + s.name + '</span><br><span class="stock-code">' + s.code + '.' + s.market + '</span></div>' +
                    '<div><span class="price">' + (s.price>0?'¥'+s.price.toFixed(2):'-') + '</span><br><span class="change ' + c + '">' + (s.price>0?fmtChange(s.change):'-') + '</span></div></div>';
            }).join('');
            await loadOverview();
            setStatus('就绪');
            updateTime();
        }
        async function selectStock(id) {
            currentStockId = id;
            loadStocks();
            const s = stocks.find(x => x.id === id);
            if (s) {
                document.getElementById('currentStockName').textContent = s.name;
                document.getElementById('boardStockName').textContent = s.name;
                document.getElementById('addTradeStockName').textContent = s.name;
                document.getElementById('addTradeBtn').disabled = false;
                await loadStockDetail(id);
            }
        }
        async function loadStockDetail(id) {
            setStatus('加载中...');
            const r = await fetch('/api/stocks/' + id + '/summary');
            const d = await r.json();
            renderTradeTable(d.transactions);
            renderProfitBoard(d.summary);
            await loadOverview();
            setStatus('就绪');
            updateTime();
        }
        function renderTradeTable(tx) {
            const w = document.getElementById('tradeTableWrapper');
            const e = document.getElementById('tradeEmptyState');
            const tbody = document.getElementById('tradeTableBody');
            const tfoot = document.getElementById('tradeTableFoot');
            if (!tx || !tx.length) { w.style.display = 'none'; e.style.display = 'block'; return; }
            w.style.display = 'block'; e.style.display = 'none';
            const rounds = {}; tx.forEach(t => { const r = t.round_num; if (!rounds[r]) rounds[r] = {buy:[],sell:[]}; if (t.type==='base'||t.type==='buy') rounds[r].buy.push(t); else rounds[r].sell.push(t); });
            let tb=0, ta=0, ts=0, tsa=0, tp=0;
            tx.forEach(t => { if (t.type==='base'||t.type==='buy') { tb+=t.shares; ta+=t.price*t.shares; } else { ts+=t.shares; tsa+=t.price*t.shares; } });
            const buyMap={}, sellMap={}; tx.forEach(t => { if (t.type==='base'||t.type==='buy') { if (!buyMap[t.round_num]) buyMap[t.round_num]=[]; buyMap[t.round_num].push(t); } else { if (!sellMap[t.round_num]) sellMap[t.round_num]=[]; sellMap[t.round_num].push(t); } });
            Object.keys(buyMap).forEach(r => { const b=buyMap[r], s=sellMap[r]||[]; let i=0,j=0; while(i<b.length&&j<s.length) { const m=Math.min(b[i].shares,s[j].shares); tp+=(s[j].price-b[i].price)*m; b[i].shares-=m; s[j].shares-=m; if(b[i].shares===0)i++; if(s[j].shares===0)j++; } });
            tbody.innerHTML = Object.keys(rounds).sort((a,b)=>a-b).map(r => {
                const d=rounds[r], bl=d.buy.length>0, sl=d.sell.length>0;
                const bp=bl ? d.buy.reduce((s,t)=>s+t.price*t.shares,0)/d.buy.reduce((s,t)=>s+t.shares,0) : null;
                const bs=bl ? d.buy.reduce((s,t)=>s+t.shares,0) : null;
                const ba=bl ? d.buy.reduce((s,t)=>s+t.price*t.shares,0) : 0;
                const sp=sl ? d.sell.reduce((s,t)=>s+t.price*t.shares,0)/d.sell.reduce((s,t)=>s+t.shares,0) : null;
                const ss=sl ? d.sell.reduce((s,t)=>s+t.shares,0) : null;
                const sa=sl ? d.sell.reduce((s,t)=>s+t.price*t.shares,0) : 0;
                const pr=bl&&sl ? sa-ba : null;
                const pc=pr!==null ? (pr>=0?'success':'danger') : '';
                const pt=pr!==null ? (pr>=0?'+':'')+fmtMoney(pr) : '-';
                const fid=bl ? d.buy[0].id : null;
                return '<tr><td>' + (r==0?'底仓':'第'+r+'次') + '</td><td>' + (bp!==null?bp.toFixed(2):'-') + '</td><td>' + (bs!==null?fmtShares(bs):'-') + '</td><td>' + fmtMoney(ba) + '</td><td>' + (sp!==null?sp.toFixed(2):'-') + '</td><td>' + (ss!==null?fmtShares(ss):'-') + '</td><td>' + fmtMoney(sa) + '</td><td class="' + pc + '">' + pt + '</td><td>' + (fid ? '<button class="btn btn-danger btn-sm" onclick="deleteTransaction(' + fid + ')">删除</button>' : '') + '</td></tr>';
            }).join('');
            const hs=tb-ts, tc=ta-tsa, cat=tc-tp, acat=hs>0?cat/hs:0;
            tfoot.innerHTML = '<tr><td>合计</td><td>-</td><td>' + fmtShares(tb) + '</td><td>' + fmtMoney(ta) + '</td><td>-</td><td>' + fmtShares(ts) + '</td><td>' + fmtMoney(tsa) + '</td><td class="' + (tp>=0?'success':'danger') + '">' + (tp>=0?'+':'') + fmtMoney(tp) + '</td><td>-</td></tr><tr><td>做T后成本</td><td colspan="3" class="' + (tp>=0?'success':'danger') + '">¥' + fmtMoney(cat) + '</td><td>-</td><td colspan="2">持仓 ' + fmtShares(hs) + ' 股</td><td colspan="2">均价 ¥' + acat.toFixed(2) + '</td></tr>';
        }
        function renderProfitBoard(s) {
            const p=s.total_profit_final>=0 ? 'success' : 'danger';
            document.getElementById('totalCost').textContent = '¥' + fmtMoney(s.total_cost);
            document.getElementById('currentValue').textContent = '¥' + fmtMoney(s.current_value);
            document.getElementById('totalProfit').textContent = (s.total_profit_final>=0?'+' : '') + '¥' + fmtMoney(s.total_profit_final);
            document.getElementById('avgCost').textContent = '¥' + (s.avg_cost||0).toFixed(2);
            document.getElementById('holdShares').textContent = fmtShares(s.hold_shares||0);
            document.getElementById('profitRate').textContent = (s.profit_rate>=0?'+' : '') + (s.profit_rate||0).toFixed(2) + '%';
            document.getElementById('costAfterT').textContent = '¥' + fmtMoney(s.cost_after_t);
            document.getElementById('profitAfterT').textContent = (s.profit_after_t>=0?'+' : '') + '¥' + fmtMoney(s.profit_after_t);
            document.getElementById('profitRateAfterT').textContent = (s.profit_rate_after_t>=0?'+' : '') + (s.profit_rate_after_t||0).toFixed(2) + '%';
            document.getElementById('profitBoardItem').className = 'board-item ' + p;
            document.getElementById('profitRateBoardItem').className = 'board-item ' + p;
        }
        async function refreshMarket() {
            if (!stocks.length) { setStatus('没有股票'); return; }
            const btn = document.getElementById('refreshBtn'); btn.disabled = true; btn.innerHTML = '<span class="loading"></span>刷新中';
            try {
                const r = await fetch('/api/market/refresh', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({codes: stocks.map(s=>s.code)}) });
                await loadStocks();
                if (currentStockId) await loadStockDetail(currentStockId);
                setStatus('刷新完成');
            } catch(e) { setStatus('刷新失败'); }
            btn.disabled = false; btn.innerHTML = '刷新行情';
        }
        async function exportData() {
            const r = await fetch('/api/export');
            const d = await r.json();
            let csv = '\uFEFF股票代码,股票名称,市场,交易类型,价格,股数,轮次\n';
            d.stocks.forEach(s => { (d.transactions[s.id]||[]).forEach(t => { csv += s.code + ',' + s.name + ',' + s.market + ',' + t.type + ',' + t.price + ',' + t.shares + ',' + t.round_num + '\n'; }); });
            const blob = new Blob([csv], {type:'text/csv'});
            const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'stock_data.csv'; a.click();
        }
        function importData() {
            const i = document.createElement('input'); i.type='file'; i.accept='.json';
            i.onchange = async e => {
                const f = e.target.files[0]; if (!f) return;
                const t = await f.text();
                const r = await fetch('/api/import', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: t });
                const d = await r.json();
                if (d.success) { await loadStocks(); setStatus('导入成功'); }
                else setStatus('导入失败: ' + d.error);
            };
            i.click();
        }
        function openModal(id) { document.getElementById(id).style.display = 'block'; }
        function closeModal(id) { document.getElementById(id).style.display = 'none'; }
        async function confirmAddStock() {
            const c = document.getElementById('stockCode').value.trim();
            const n = document.getElementById('stockName').value.trim();
            const m = document.getElementById('stockMarket').value;
            if (!c || !n) { alert('请填写完整信息'); return; }
            const r = await fetch('/api/stocks', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({code:c,name:n,market:m}) });
            const d = await r.json();
            if (d.success) { closeModal('addStockModal'); await loadStocks(); }
            else alert(d.error);
        }
        async function confirmAddTrade() {
            const t = document.getElementById('tradeType').value;
            const p = parseFloat(document.getElementById('tradePrice').value);
            const s = parseInt(document.getElementById('tradeShares').value);
            const r = parseInt(document.getElementById('tradeRound').value);
            if (!p || !s || isNaN(p) || isNaN(s)) { alert('请填写正确的价格和股数'); return; }
            await fetch('/api/stocks/' + currentStockId + '/transactions', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({type:t,price:p,shares:s,round_num:r}) });
            closeModal('addTradeModal');
            await loadStockDetail(currentStockId);
        }
        function deleteTransaction(id) {
            deleteCallback = async () => {
                await fetch('/api/transactions/' + id, { method: 'DELETE' });
                closeModal('confirmDeleteModal');
                await loadStockDetail(currentStockId);
            };
            openModal('confirmDeleteModal');
        }
        document.getElementById('addStockBtn').onclick = () => openModal('addStockModal');
        document.getElementById('addTradeBtn').onclick = () => openModal('addTradeModal');
        document.getElementById('exportBtn').onclick = exportData;
        document.getElementById('importBtn').onclick = importData;
        document.getElementById('refreshBtn').onclick = refreshMarket;
        document.getElementById('confirmDeleteBtn').onclick = () => deleteCallback && deleteCallback();
        document.getElementById('stockCode').addEventListener('input', async e => {
            const v = e.target.value.replace(/\D/g,'').slice(0,6); e.target.value = v;
            if (v.length === 6) {
                try {
                    const r = await fetch('/api/market/query?code=' + v);
                    const d = await r.json();
                    if (!d.error) { document.getElementById('stockName').value = d.name; document.getElementById('stockMarket').value = d.market||'SZ'; }
                } catch(e) {}
            }
        });
        loadStocks();
    </script>
</body>
</html>'''


@app.route('/')
def index():
    return INDEX_HTML, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/login')
def login_page():
    return LOGIN_HTML, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if data.get('username') == ADMIN_USERNAME and data.get('password') == ADMIN_PASSWORD:
        session['logged_in'] = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '用户名或密码错误'}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    return jsonify({'success': True})


@app.route('/api/check_login', methods=['GET'])
def check_login():
    return jsonify({'logged_in': 'logged_in' in session})


@app.route('/api/stocks', methods=['GET'])
@login_required
def get_stocks():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM stocks ORDER BY id')
    stocks = [dict(row) for row in cursor.fetchall()]
    cursor.execute('SELECT * FROM market_cache')
    market_data = {row['stock_code']: dict(row) for row in cursor.fetchall()}
    for s in stocks:
        m = market_data.get(s['code'], {'price': 0, 'change': 0})
        s['price'] = m.get('price', 0)
        s['change'] = m.get('change', 0)
    conn.close()
    return jsonify(stocks)


@app.route('/api/stocks', methods=['POST'])
@login_required
def add_stock():
    data = request.json
    if not data.get('code') or not data.get('name') or not data.get('market'):
        return jsonify({'success': False, 'error': '参数不完整'}), 400
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO stocks (code, name, market) VALUES (?, ?, ?)', (data['code'], data['name'], data['market']))
        conn.commit()
        return jsonify({'success': True, 'id': cursor.lastrowid})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': '股票已存在'}), 400
    finally:
        conn.close()


@app.route('/api/stocks/<int:stock_id>', methods=['DELETE'])
@login_required
def delete_stock(stock_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM stocks WHERE id = ?', (stock_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': cursor.rowcount > 0})


@app.route('/api/stocks/<int:stock_id>/transactions', methods=['GET'])
@login_required
def get_transactions(stock_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions WHERE stock_id = ? ORDER BY round_num, created_at', (stock_id,))
    tx = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(tx)


@app.route('/api/stocks/<int:stock_id>/transactions', methods=['POST'])
@login_required
def add_transaction(stock_id):
    data = request.json
    if data.get('type') not in ('base', 'buy', 'sell') or data.get('price', 0) <= 0 or data.get('shares', 0) <= 0:
        return jsonify({'success': False, 'error': '参数无效'}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO transactions (stock_id, type, price, shares, round_num) VALUES (?, ?, ?, ?, ?)',
                   (stock_id, data['type'], data['price'], data['shares'], data.get('round_num', 0)))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': cursor.lastrowid})


@app.route('/api/transactions/<int:tx_id>', methods=['DELETE'])
@login_required
def delete_transaction(tx_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT stock_id, round_num FROM transactions WHERE id = ?', (tx_id,))
    row = cursor.fetchone()
    if row:
        cursor.execute('DELETE FROM transactions WHERE stock_id = ? AND round_num = ?', (row['stock_id'], row['round_num']))
    conn.commit()
    conn.close()
    return jsonify({'success': cursor.rowcount > 0})


@app.route('/api/stocks/<int:stock_id>/summary', methods=['GET'])
@login_required
def get_stock_summary(stock_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM stocks WHERE id = ?', (stock_id,))
    stock = dict(cursor.fetchone()) if cursor.fetchone() else None
    if not stock:
        conn.close()
        return jsonify({'error': '股票不存在'}), 404
    cursor.execute('SELECT * FROM transactions WHERE stock_id = ? ORDER BY round_num, created_at', (stock_id,))
    transactions = [dict(row) for row in cursor.fetchall()]
    cursor.execute('SELECT * FROM market_cache WHERE stock_code = ?', (stock['code'],))
    market = dict(cursor.fetchone()) if cursor.fetchone() else {'price': 0, 'change': 0}
    conn.close()
    
    tbs, tba, tss, tsa = 0, 0, 0, 0
    for tx in transactions:
        if tx['type'] in ('base', 'buy'):
            tbs += tx['shares']
            tba += tx['price'] * tx['shares']
        elif tx['type'] == 'sell':
            tss += tx['shares']
            tsa += tx['price'] * tx['shares']
    
    hs = tbs - tss
    tc = tba - tsa
    cp = market.get('price', 0)
    cv = hs * cp if cp > 0 else 0
    tpf = cv - tc
    ac = tc / hs if hs > 0 else 0
    pr = (tpf / tc) * 100 if tc > 0 else 0
    
    rounds = {}
    for tx in transactions:
        rn = tx['round_num']
        if rn not in rounds:
            rounds[rn] = {'buy': None, 'sell': None}
        if tx['type'] in ('base', 'buy'):
            rounds[rn]['buy'] = tx
        elif tx['type'] == 'sell':
            rounds[rn]['sell'] = tx
    
    tp = 0
    for rn in rounds:
        r = rounds[rn]
        if r['buy'] and r['sell']:
            tp += r['sell']['price'] * r['sell']['shares'] - r['buy']['price'] * r['buy']['shares']
    
    cat = tc - tp
    pat = cv - cat
    acat = cat / hs if hs > 0 else 0
    prat = (pat / cat) * 100 if cat > 0 else 0
    
    return jsonify({
        'stock': stock, 'transactions': transactions, 'market': market,
        'summary': {
            'total_buy_shares': tbs, 'total_buy_amount': tba, 'total_sell_shares': tss, 'total_sell_amount': tsa,
            'total_profit': tp, 'hold_shares': hs, 'total_cost': tc, 'current_value': cv,
            'total_profit_final': tpf, 'avg_cost': ac, 'profit_rate': pr,
            'cost_after_t': cat, 'profit_after_t': pat, 'avg_cost_after_t': acat, 'profit_rate_after_t': prat
        }
    })


@app.route('/api/overview', methods=['GET'])
@login_required
def get_overview():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM stocks')
    stocks = [dict(row) for row in cursor.fetchall()]
    
    tc, tcv, tp, tcat, tpat, ths = 0, 0, 0, 0, 0, 0
    
    for stock in stocks:
        cursor.execute('SELECT * FROM transactions WHERE stock_id = ? ORDER BY round_num, created_at', (stock['id'],))
        tx = [dict(row) for row in cursor.fetchall()]
        
        sba, ssa, sp, hs = 0, 0, 0, 0
        for t in tx:
            if t['type'] in ('base', 'buy'):
                sba += t['price'] * t['shares']
                hs += t['shares']
            elif t['type'] == 'sell':
                ssa += t['price'] * t['shares']
                hs -= t['shares']
        
        buyMap, sellMap = {}, {}
        for t in tx:
            if t['type'] in ('base', 'buy'):
                if t['round_num'] not in buyMap: buyMap[t['round_num']] = []
                buyMap[t['round_num']].append(t)
            elif t['type'] == 'sell':
                if t['round_num'] not in sellMap: sellMap[t['round_num']] = []
                sellMap[t['round_num']].append(t)
        
        for rn in buyMap:
            buys = buyMap[rn]
            sells = sellMap.get(rn, [])
            i, j = 0, 0
            while i < len(buys) and j < len(sells):
                m = min(buys[i]['shares'], sells[j]['shares'])
                sp += (sells[j]['price'] - buys[i]['price']) * m
                buys[i]['shares'] -= m
                sells[j]['shares'] -= m
                if buys[i]['shares'] == 0: i += 1
                if sells[j]['shares'] == 0: j += 1
        
        sc = sba - ssa
        tc += sc
        ths += hs
        
        scat = sc - sp
        tcat += scat
        
        cursor.execute('SELECT price FROM market_cache WHERE stock_code = ?', (stock['code'],))
        mp = cursor.fetchone()['price'] if cursor.fetchone() else 0
        
        cv = mp * hs
        tcv += cv
        tp += cv - sc
        tpat += cv - scat
    
    conn.close()
    
    return jsonify({
        'total_cost': tc, 'total_current_value': tcv, 'total_profit': tp,
        'total_profit_rate': (tp / tc * 100) if tc > 0 else 0, 'stock_count': len(stocks),
        'total_hold_shares': ths,
        'total_cost_after_t': tcat, 'total_profit_after_t': tpat,
        'total_profit_rate_after_t': (tpat / tcat * 100) if tcat > 0 else 0
    })


@app.route('/api/market/query', methods=['GET'])
@login_required
def query_stock_info():
    code = request.args.get('code', '')
    try:
        r = requests.get(f'{API_BASE_URL}/hslt/list/{API_LICENCE}', timeout=10)
        if r.status_code == 200:
            for s in r.json():
                if s['dm'] == code or s['dm'] == f'{code}.SH' or s['dm'] == f'{code}.SZ':
                    return jsonify({'code': s['dm'].split('.')[0], 'name': s['mc'], 'market': s['jys'].upper()})
    except Exception:
        pass
    return jsonify({'error': '股票未找到'}), 404


@app.route('/api/market/price', methods=['GET'])
@login_required
def get_stock_price():
    code = request.args.get('code', '')
    try:
        r = requests.get(f'{API_BASE_URL}/hsrl/ssjy/{code}/{API_LICENCE}', timeout=5)
        if r.status_code == 200:
            d = r.json()
            return jsonify({'price': d.get('p', 0), 'change': d.get('pc', 0)})
    except Exception:
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
        try:
            r = requests.get(f'{API_BASE_URL}/hsrl/ssjy/{code}/{API_LICENCE}', timeout=5)
            if r.status_code == 200:
                d = r.json()
                cursor.execute('INSERT OR REPLACE INTO market_cache (stock_code, price, change, update_time) VALUES (?, ?, ?, ?)',
                              (code, d.get('p', 0), d.get('pc', 0), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                results[code] = {'price': d.get('p', 0), 'change': d.get('pc', 0)}
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
    tx_dict = {}
    for s in stocks:
        cursor.execute('SELECT * FROM transactions WHERE stock_id = ? ORDER BY round_num', (s['id'],))
        tx_dict[s['id']] = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'stocks': stocks, 'transactions': tx_dict})


@app.route('/api/import', methods=['POST'])
@login_required
def import_data():
    data = request.json
    if not data or 'stocks' not in data or 'transactions' not in data:
        return jsonify({'success': False, 'error': '数据格式错误'}), 400
    conn = get_db()
    cursor = conn.cursor()
    try:
        for s in data['stocks']:
            cursor.execute('INSERT OR IGNORE INTO stocks (code, name, market) VALUES (?, ?, ?)', (s['code'], s['name'], s['market']))
        for s in data['stocks']:
            cursor.execute('SELECT id FROM stocks WHERE code = ?', (s['code'],))
            row = cursor.fetchone()
            if row:
                sid = row[0]
                for t in data['transactions'].get(s['id'], []):
                    cursor.execute('SELECT id FROM transactions WHERE stock_id = ? AND type = ? AND round_num = ?', (sid, t['type'], t['round_num']))
                    if not cursor.fetchone():
                        cursor.execute('INSERT INTO transactions (stock_id, type, price, shares, round_num) VALUES (?, ?, ?, ?, ?)',
                                      (sid, t['type'], t['price'], t['shares'], t['round_num']))
        conn.commit()
        return jsonify({'success': True, 'message': '数据导入成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


init_db()

if __name__ == '__main__' or getattr(sys, 'frozen', False):
    app.run(host='0.0.0.0', port=5000, debug=False)