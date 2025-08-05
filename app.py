import sqlite3
from flask import Flask, request, redirect, render_template, session, url_for
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, session, flash, get_flashed_messages
import os
from werkzeug.utils import secure_filename
app = Flask(__name__)
app.secret_key = 'supersecret'  # 用于登录状态保持
# 上传文件的保存目录
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 判断文件扩展名是否合法
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS




# 商城券配置
coupon_store = [
    {
        "type": "洗碗券",
        "cost": 50,
        "desc": "洗碗但不包括洗大碗和擦碗等"
    },
    {
        "type": "扫地券",
        "cost": 200,
        "desc": "可帮忙扫地"
    },
    {
        "type": "消毒券",
        "cost": 200,
        "desc": "包括擦碗和消毒"
    },
    {
        "type": "搬东西券",
        "cost": 300,
        "desc": "可帮忙搬东西来回两趟"
    },
    {
        "type": "万能券",
        "cost": 1000,
        "desc": "可以干任何事情"
    },
]

# 🧱 初始化数据库（如果不存在就创建）
def init_db():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    # 创建用户表
    c.execute('''
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            points INTEGER DEFAULT 200
        )
    ''')

    # 创建用户券表
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            coupon_type TEXT NOT NULL,
            status TEXT DEFAULT '未使用',
            expire_date TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS coupons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        points_required INTEGER,
        status TEXT DEFAULT '可用' 
);  
    
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS coupon_store (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        desc TEXT,
        cost INTEGER NOT NULL
);

    
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS sign_in_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            sign_date TEXT NOT NULL
        )
    ''')
    # 添加管理员账号（如果不存在）
    c.execute('SELECT * FROM user WHERE username="admin"')
    if not c.fetchone():
        c.execute('INSERT INTO user (username, password, points) VALUES (?, ?, ?)', ("admin", "admin123", 0))
    # 创建任务表
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            reward_points INTEGER,
            deadline TEXT
        )
    ''')
    c.execute('''
            CREATE TABLE IF NOT EXISTS task_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                task_id INTEGER,
                image_path TEXT,
                status TEXT DEFAULT '待审核',
                submit_time TEXT
            )


        ''')



    conn.commit()
    conn.close()



# 🔹 首页
@app.route('/')
def index():
    if 'username' not in session:
        return redirect('/login')

    username = session['username']
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('SELECT points FROM user WHERE username=?', (username,))
    points = c.fetchone()[0]

    c.execute('SELECT * FROM user_coupons WHERE username=?', (username,))
    coupons = c.fetchall()
    conn.close()

    return render_template('index.html', username=username, points=points, coupons=coupons)




# 🔹 注册
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute('SELECT * FROM user WHERE username=?', (username,))
        existing = c.fetchone()
        if existing:
            flash("用户名已存在", "error")
            conn.close()
            return redirect('/register')

        c.execute('INSERT INTO user (username, password, points) VALUES (?, ?, ?)', (username, password, 200))
        conn.commit()
        conn.close()

        flash("注册成功，请登录", "success")
        return redirect('/login')

    return render_template('register.html')


# 🔹 登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute('SELECT * FROM user WHERE username=? AND password=?', (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['username'] = username
            flash("登录成功！", "success")
            return redirect('/')
        else:
            flash("用户名或密码错误", "error")
            return redirect('/login')
    return render_template('login.html')


# 🔹 退出登录
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/')
#添加这个路由，让用户点击按钮后将券状态更新为“待审核”
@app.route('/use_coupon/<int:coupon_id>', methods=['POST'])
def use_coupon(coupon_id):
    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('UPDATE user_coupons SET status="待审核" WHERE id=?', (coupon_id,))
    conn.commit()
    conn.close()
    return redirect('/')

# 点击签到
@app.route('/sign_in')
def sign_in():
    if 'username' not in session:
        return redirect('/login')

    username = session['username']
    today = datetime.now().strftime('%Y-%m-%d')

    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('SELECT * FROM sign_in_record WHERE username=? AND sign_date=?', (username, today))
    if c.fetchone():
        conn.close()
        flash("你今天已经签到过啦！", "error")  # ❗️重复签到提示
        return redirect('/')

    # 未签到，则添加记录 + 加积分
    c.execute('INSERT INTO sign_in_record (username, sign_date) VALUES (?, ?)', (username, today))
    c.execute('UPDATE user SET points = points + 100 WHERE username=?', (username,))
    conn.commit()
    conn.close()
    flash("签到成功！已获得100积分", "success")
    return redirect('/')


@app.route('/admin')
def admin():
    if 'username' not in session or session['username'] != 'admin':
        return "<h3>只有管理员可以访问这个页面。</h3><a href='/'>返回首页</a>"

    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    # 找出所有“非未使用”的券（即需审核的）
    c.execute('SELECT id, username, coupon_type, expire_date, status FROM user_coupons WHERE status != "未使用"')
    pending = c.fetchall()
    conn.close()

    return render_template('admin.html', pending_coupons=pending)

# 审核
@app.route('/approve_coupon/<int:coupon_id>', methods=['POST'])
def approve_coupon(coupon_id):
    if 'username' not in session or session['username'] != 'admin':
        return "权限不足"
    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    # 查用户名
    c.execute('SELECT username FROM user_coupons WHERE id=?', (coupon_id,))
    user = c.fetchone()
    if user:
        uname = user[0]
        # 更新券状态
        c.execute('UPDATE user_coupons SET status="已失效" WHERE id=?', (coupon_id,))
        # 添加通知
        c.execute('INSERT INTO notifications (username, message) VALUES (?, ?)', (uname, "你申请的券已审核通过并已失效"))
    conn.commit()
    conn.close()
    return redirect('/admin')

# 增添拒绝
@app.route('/reject_coupon/<int:coupon_id>', methods=['POST'])
def reject_coupon(coupon_id):
    if 'username' not in session or session['username'] != 'admin':
        return "权限不足"
    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    c.execute('SELECT username FROM user_coupons WHERE id=?', (coupon_id,))
    user = c.fetchone()
    if user:
        uname = user[0]
        # 拒绝并恢复券为“未使用”
        c.execute('UPDATE user_coupons SET status="未使用" WHERE id=?', (coupon_id,))
        # 添加通知
        c.execute('INSERT INTO notifications (username, message) VALUES (?, ?)', (uname, "你申请的券被拒绝，券已恢复为可使用状态"))
    conn.commit()
    conn.close()
    return redirect('/admin')

#增添恢复
@app.route('/restore_coupon/<int:coupon_id>', methods=['POST'])
def restore_coupon(coupon_id):
    if 'username' not in session or session['username'] != 'admin':
        return "权限不足"
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('UPDATE user_coupons SET status="未使用" WHERE id=?', (coupon_id,))
    conn.commit()
    conn.close()
    return redirect('/admin')
def init_notifications():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            message TEXT,
            read INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
@app.route('/shop')
def shop():
    if 'username' not in session:
        return redirect('/login')

    username = session['username']
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row  # ✅ 让你可以用 item.id 访问字段
    c = conn.cursor()

    # 当前用户积分
    c.execute('SELECT points FROM user WHERE username=?', (username,))
    row = c.fetchone()
    points = row['points'] if row else 0

    # ✅ 查询所有可用券
    c.execute('SELECT * FROM coupon_store')
    coupon_store = c.fetchall()

    conn.close()

    return render_template('shop.html',
                           username=username,
                           points=points,
                           coupon_store=coupon_store)




@app.route('/redeem_coupon', methods=['POST'])
def redeem_coupon():
    if 'username' not in session:
        return redirect('/login')

    coupon_type = request.form['coupon_type']
    username = session['username']

    # ✅ 查询券信息（根据 type）
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('SELECT * FROM coupon_store WHERE type=?', (coupon_type,))
    coupon_info = c.fetchone()

    if not coupon_info:
        conn.close()
        flash("非法券类型", "error")
        return redirect('/shop')

    # 获取当前用户积分
    c.execute('SELECT points FROM user WHERE username=?', (username,))
    row = c.fetchone()
    if not row:
        conn.close()
        flash("用户信息异常，请重新登录", "error")
        return redirect('/logout')

    points = row['points']

    # 积分不够
    if points < coupon_info['cost']:
        conn.close()
        flash(f"积分不足，兑换 {coupon_type} 需要 {coupon_info['cost']} 分！", "error")
        return redirect('/shop')

    # 扣分并发券
    c.execute('UPDATE user SET points = points - ? WHERE username=?', (coupon_info['cost'], username))

    from datetime import datetime, timedelta
    expire = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')

    c.execute('INSERT INTO user_coupons (username, coupon_type, expire_date, status) VALUES (?, ?, ?, ?)',
              (username, coupon_type, expire, '未使用'))

    conn.commit()
    conn.close()

    flash(f"成功兑换 {coupon_type}！", "success")
    return redirect('/shop')

@app.route('/coupon/add', methods=['GET', 'POST'])
def add_coupon():
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/login')

    if request.method == 'POST':
        type_ = request.form['type']
        desc = request.form['desc']
        cost = int(request.form['cost'])

        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute("INSERT INTO coupon_store (type, desc, cost) VALUES (?, ?, ?)", (type_, desc, cost))
        conn.commit()
        conn.close()

        flash('新券已添加', 'success')
        return redirect('/shop')

    return render_template('add_coupon.html')
@app.route('/coupon/edit/<int:coupon_id>', methods=['GET', 'POST'])
def edit_coupon(coupon_id):
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/login')

    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    if request.method == 'POST':
        type_ = request.form['type']
        desc = request.form['desc']
        cost = int(request.form['cost'])

        c.execute("UPDATE coupon_store SET type=?, desc=?, cost=? WHERE id=?", (type_, desc, cost, coupon_id))
        conn.commit()
        conn.close()
        flash('券信息已更新', 'success')
        return redirect('/shop')

    c.execute("SELECT * FROM coupon_store WHERE id=?", (coupon_id,))
    coupon = c.fetchone()
    conn.close()

    if not coupon:
        flash('未找到该券', 'error')
        return redirect('/shop')

    return render_template('edit_coupon.html', coupon=coupon)
@app.route('/coupon/delete/<int:coupon_id>', methods=['POST'])
def delete_coupon(coupon_id):
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/login')

    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute("DELETE FROM coupon_store WHERE id=?", (coupon_id,))
    conn.commit()
    conn.close()

    flash('券已删除', 'warning')
    return redirect('/shop')

@app.route('/admin/create_task', methods=['GET', 'POST'])
def create_task():
    if 'username' not in session or session['username'] != 'admin':
        return "<h3>只有管理员可以访问该页面</h3><a href='/'>返回首页</a>"

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        reward = int(request.form['reward'])
        deadline = request.form['deadline']

        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute('INSERT INTO tasks (title, description, reward_points, deadline) VALUES (?, ?, ?, ?)',
                  (title, description, reward, deadline))
        conn.commit()
        conn.close()

        flash("任务创建成功", "success")
        return redirect('/admin/create_task')

    return render_template('create_task.html')
@app.route('/tasks')
def browse_tasks():
    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('SELECT id, title, description, reward_points, deadline FROM tasks ORDER BY id DESC')
    tasks = c.fetchall()
    conn.close()

    return render_template('task.html', tasks=tasks)


@app.route('/submit_task/<int:task_id>', methods=['GET', 'POST'])
def submit_task(task_id):
    if 'username' not in session:
        return redirect('/login')

    username = session['username']

    if request.method == 'POST':
        if 'proof_image' not in request.files:
            flash('未找到上传文件', 'error')
            return redirect(request.url)

        file = request.files['proof_image']
        if file.filename == '':
            flash('请选择文件', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # ✅ 生成安全文件名
            filename = secure_filename(f"{username}_task{task_id}_{file.filename}")

            # ✅ 创建保存路径（static/uploads/文件名）
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # ✅ 保存文件到本地
            file.save(save_path)

            # ✅ 保存提交记录到数据库（只保存文件名 filename，不是完整路径）
            conn = sqlite3.connect('data.db')
            c = conn.cursor()
            c.execute('INSERT INTO task_submissions (username, task_id, image_path, status) VALUES (?, ?, ?, ?)',
                      (username, task_id, filename, '待审核'))
            conn.commit()
            conn.close()

            flash("任务提交成功，等待管理员审核", "success")
            return redirect('/tasks')

    # GET 显示表单
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('SELECT title, description FROM tasks WHERE id=?', (task_id,))
    task = c.fetchone()
    conn.close()

    if not task:
        return "任务不存在"

    return render_template('submit_task.html', task=task, task_id=task_id)


@app.route('/my_submissions')
def my_submissions():
    if 'username' not in session:
        return redirect('/login')
    username = session['username']

    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('''
        SELECT task_submissions.id, tasks.title, task_submissions.image_path, task_submissions.status
        FROM task_submissions
        JOIN tasks ON task_submissions.task_id = tasks.id
        WHERE task_submissions.username=?
    ''', (username,))
    submissions = c.fetchall()
    conn.close()

    return render_template('my_submissions.html', submissions=submissions)
@app.route('/cancel_submission/<int:submission_id>', methods=['POST'])
def cancel_submission(submission_id):
    if 'username' not in session:
        return redirect('/login')
    username = session['username']

    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    # 只允许撤回自己的“待审核”提交
    c.execute('SELECT image_path FROM task_submissions WHERE id=? AND username=? AND status="待审核"',
              (submission_id, username))
    row = c.fetchone()
    if row:
        # 删除记录
        c.execute('DELETE FROM task_submissions WHERE id=?', (submission_id,))
        # 也可以删除上传的文件（可选）
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], row[0])
        if os.path.exists(image_path):
            os.remove(image_path)
        flash("提交已撤回", "success")
    else:
        flash("无法撤回该任务", "error")

    conn.commit()
    conn.close()
    return redirect('/my_submissions')

@app.route('/task_review')
def task_review():
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/login')

    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('''
        SELECT ts.id, ts.username, t.title, ts.image_path, ts.status
        FROM task_submissions ts
        JOIN tasks t ON ts.task_id = t.id
        ORDER BY ts.id DESC
    ''')
    submissions = c.fetchall()
    conn.close()
    return render_template('task_review.html', submissions=submissions)

@app.route('/task_review/<int:submission_id>/approve', methods=['POST'])
def approve_submission(submission_id):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    # 获取用户名和任务积分
    c.execute('''
            SELECT ts.username, t.reward_points
            FROM task_submissions ts
            JOIN tasks t ON ts.task_id = t.id
            WHERE ts.id = ?
        ''', (submission_id,))
    result = c.fetchone()

    if result:
        username, points = result

        if username is not None and isinstance(points, int):
            # 更新状态
            c.execute("UPDATE task_submissions SET status = '已通过' WHERE id = ?", (submission_id,))
            # 更新积分
            c.execute("UPDATE user SET points = points + ? WHERE username = ?", (points, username))
            conn.commit()
        else:
            flash("数据格式有误，审核失败", "error")
    else:
        flash("找不到该任务提交记录", "error")

    conn.close()
    flash('审核通过，积分已发放', 'success')
    return redirect('/task_review')


@app.route('/task_review/<int:submission_id>/return', methods=['POST'])
def return_submission(submission_id):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('UPDATE task_submissions SET status="已退回" WHERE id=?', (submission_id,))
    conn.commit()
    conn.close()
    flash('任务已退回，用户可重新提交', 'info')
    return redirect('/task_review')


@app.route('/task_review/<int:submission_id>/delete', methods=['POST'])
def delete_submission(submission_id):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    # 可选：删除文件（如果你愿意的话）
    c.execute('SELECT image_path FROM task_submissions WHERE id=?', (submission_id,))
    row = c.fetchone()
    if row:
        filename = row[0]
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    c.execute('DELETE FROM task_submissions WHERE id=?', (submission_id,))
    conn.commit()
    conn.close()
    flash('提交记录已删除', 'warning')
    return redirect('/task_review')
@app.route('/resubmit_task/<int:submission_id>', methods=['GET', 'POST'])
def resubmit_task(submission_id):
    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    # 获取旧提交数据
    c.execute('''
        SELECT ts.task_id, t.title, t.description
        FROM task_submissions ts
        JOIN tasks t ON ts.task_id = t.id
        WHERE ts.id = ? AND ts.username = ?
    ''', (submission_id, session['username']))
    task = c.fetchone()

    if not task:
        conn.close()
        return "任务不存在或你无权修改"

    task_id, title, description = task

    if request.method == 'POST':
        file = request.files.get('proof_image')
        if not file or file.filename == '':
            flash('请上传图片文件', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(f"{session['username']}_task{task_id}_{file.filename}")
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            # 更新数据库
            c.execute('''
                UPDATE task_submissions
                SET image_path = ?, status = '待审核'
                WHERE id = ?
            ''', (filename, submission_id))
            conn.commit()
            conn.close()

            flash("重新提交成功，等待管理员审核", "success")
            return redirect('/my_submissions')

    conn.close()
    return render_template('resubmit_task.html', task_id=task_id, title=title, description=description)


# 第一次运行 app.py 时执行初始化
init_notifications()


if __name__ == "__main__":
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))


