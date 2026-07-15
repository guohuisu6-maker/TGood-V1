# 智T盈 - 智能做T盈利助手

一款帮助投资者管理股票做T交易记录、计算盈利的Web应用。

## 功能特点

- 📊 持仓总览看板
- 📈 实时行情数据查询
- 💹 做T交易记录管理
- 📉 盈亏计算与分析
- 🔐 用户登录认证

## 技术栈

- **后端**: Flask 3.1.3
- **前端**: HTML5 + CSS3 + JavaScript
- **数据库**: SQLite
- **部署**: 支持 Render、Railway、PythonAnywhere 等平台

## 登录信息

- **用户名**: `admin`
- **密码**: `TGood123.A`

---

## 本地运行

### 环境要求

- Python 3.10+
- pip

### 运行步骤

1. 进入项目目录：
```bash
cd TGood-GT
```

2. 创建虚拟环境：
```bash
python -m venv venv
```

3. 激活虚拟环境：
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

4. 安装依赖：
```bash
pip install -r requirements.txt
```

5. 运行应用：
```bash
python web_app.py
```

6. 在浏览器中访问：
```
http://localhost:5000
```

---

## 🚀 部署到互联网（推荐使用 Render）

### 为什么选择 Render？

| 对比项 | Render | Railway | PythonAnywhere |
|--------|--------|---------|----------------|
| **免费额度** | 750小时/月 | $5试用 | 100 CPU秒/天 |
| **无需信用卡** | ✅ | ✅ | ✅ |
| **Flask支持** | ✅ 自动检测 | ✅ | ✅ |
| **部署方式** | GitHub自动部署 | GitHub | 手动上传 |
| **HTTPS** | ✅ 自动配置 | ✅ | ✅ |
| **环境变量** | ✅ | ✅ | ✅ |
| **自定义域名** | ✅ | ✅ | ✅ |
| **可靠性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **冷启动时间** | 30-50秒 | 无 | 无 |

**Render** 是目前最适合个人开发者的免费 Python 部署平台，具有以下优势：

1. **真正免费**：无需信用卡，750小时/月足够日常使用
2. **部署简单**：连接 GitHub 仓库即可自动部署
3. **功能完整**：支持 HTTPS、环境变量、自定义域名等
4. **可靠性高**：生产级基础设施，适合长期使用

---

### 部署步骤

#### 第一步：创建 GitHub 仓库

1. 访问 [GitHub](https://github.com)，登录你的账户
2. 点击 **New** 创建新仓库
3. 仓库名称建议：`TGood` 或 `TGood-GT`
4. 选择 **Public**（公开）或 **Private**（私有）
5. 点击 **Create repository**

#### 第二步：上传代码到 GitHub

打开终端/命令提示符，执行以下命令：

```bash
cd d:\DIYApplication\TGood\TGood-GT

git init
git add .
git commit -m "Initial commit - TGood stock trading assistant"

git remote add origin https://github.com/your-username/your-repo-name.git
git push -u origin main
```

**替换** `your-username` 和 `your-repo-name` 为你的 GitHub 用户名和仓库名。

#### 第三步：在 Render 上部署

1. 访问 [Render](https://render.com)，点击 **Sign Up** 注册账户（支持 GitHub 登录）
2. 登录后，点击右上角 **New +** → **Web Service**
3. 在 **Connect a repository** 下方，选择你的 GitHub 仓库
4. 点击 **Connect**
5. 配置部署选项：
   - **Name**: 输入应用名称（如 `tgood`）
   - **Region**: 选择离你最近的区域（建议选择 `Oregon` 或 `Frankfurt`）
   - **Branch**: `main`
   - **Root Directory**: 留空（默认）
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
6. 点击 **Advanced** 展开高级设置，添加环境变量：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `SECRET_KEY` | 点击旁边的 **Generate** 生成随机密钥 | Flask 会话密钥，必须修改 |
| `ADMIN_PASSWORD` | 输入你自己的密码 | 登录密码，建议修改 |
| `ADMIN_USERNAME` | admin | 登录用户名（可选修改） |
| `API_LICENCE` | 9B0EF33E-B966-4B2E-8C4F-D5A3785FBE6C | 股票API密钥 |

7. 滚动到底部，点击 **Create Web Service**

#### 第四步：等待部署完成

部署过程大约需要 2-5 分钟，你可以在 Render 控制台看到部署日志。

部署成功后，你会获得一个类似这样的 URL：
```
https://tgood.onrender.com
```

打开浏览器访问这个 URL，即可通过互联网访问你的应用！

---

### 部署注意事项

1. **冷启动**：免费版服务在 15 分钟无活动后会自动休眠，下次访问时需要 30-50 秒的冷启动时间
2. **每月额度**：750小时/月，超过后服务会暂停到下个月
3. **数据持久化**：SQLite 数据库文件存储在服务器上，免费版重启后数据可能丢失。如果需要持久化数据，建议使用 Render 的 PostgreSQL 数据库（免费试用30天）或升级到付费版
4. **自定义域名**：在 Render 控制台的 **Settings** → **Custom Domains** 中添加你的域名

---

## 项目结构

```
TGood-GT/
├── web_app.py          # Flask 后端应用
├── requirements.txt    # Python 依赖
├── Procfile            # Gunicorn 进程管理配置
├── runtime.txt         # Python 版本指定（3.12）
├── .gitignore          # Git 忽略文件
├── static/
│   ├── index.html      # 主页面
│   └── login.html      # 登录页面
└── data/               # SQLite 数据库目录（运行时自动创建）
```

---

## 环境变量

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `SECRET_KEY` | ✅ | 随机生成 | Flask 会话密钥，部署时必须修改 |
| `ADMIN_USERNAME` | 否 | admin | 登录用户名 |
| `ADMIN_PASSWORD` | ✅ | TGood123.A | 登录密码，部署时必须修改 |
| `API_LICENCE` | 否 | 9B0EF33E-B966-4B2E-8C4F-D5A3785FBE6C | 股票行情API密钥 |

---

## 安全建议

1. **修改默认密码**：部署后立即通过环境变量修改默认密码
2. **使用 HTTPS**：Render 自动配置 HTTPS，确保数据传输安全
3. **设置 SECRET_KEY**：使用 Render 提供的随机生成功能，不要使用默认值
4. **定期备份**：定期导出数据，避免数据丢失

---

## 常见问题

### Q: 应用无法启动？
A: 检查 Python 版本是否为 3.10+，确保所有依赖已安装。查看 Render 控制台的日志。

### Q: 无法访问应用？
A: 检查防火墙设置，确保端口已开放。查看 Render 控制台的部署状态。

### Q: 行情数据无法获取？
A: 检查网络连接和 API_LICENCE 是否有效。

### Q: 数据丢失？
A: SQLite 数据库文件存储在服务器上，免费版服务重启后数据可能丢失。建议使用 PostgreSQL 数据库或定期导出数据。

### Q: 访问速度慢？
A: 免费版服务有冷启动时间（30-50秒），如果需要更快的响应，可考虑升级到付费版。

---

## License

MIT License