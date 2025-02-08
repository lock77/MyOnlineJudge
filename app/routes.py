from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask import Flask
from app.models import db, Problem, Submission, User, Contest, ContestSubmission
from app.judge.judge_core import docker_judge
from functools import wraps
from datetime import datetime
from datetime import datetime, timezone
# 初始化 Blueprint
main = Blueprint('main', __name__)

# 初始化 LoginManager
login_manager = LoginManager()
login_manager.login_view = 'main.login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# 管理员装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('无管理员权限！', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)

    return decorated_function

@main.route('/')
def firstpage():
    problems = Problem.query.all()
    return render_template('firstpage.html', problems=problems)


@main.route('/index')
def index():
    problems = Problem.query.all()
    return render_template('index.html', problems=problems)




@main.route('/admin_dashboard')
def admin_dashboard():
    problems = Problem.query.all()
    return render_template('admin_dashboard.html', problems=problems)


@main.route('/problem/<int:problem_id>', methods=['GET', 'POST'])
def problem_detail(problem_id):
    problem = Problem.query.get_or_404(problem_id)

    if request.method == 'POST':
        code = request.form['code']
        language = request.form.get('language', 'python')  # 默认语言为 Python
        result = docker_judge(code, problem.test_input, problem.test_output, language)

        submission = Submission(
            user_code=code,
            result=result,
            problem_id=problem_id
        )
        db.session.add(submission)
        db.session.commit()

        return render_template('problem.html', problem=problem, result=result)

    return render_template('problem.html', problem=problem)


# 用户注册路由
@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        is_admin = 'is_admin' in request.form  # 获取复选框的值
        user = User(username=username, is_admin=is_admin)  # 设置 is_admin 属性
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('注册成功！', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html')


# 用户登录路由
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            if user.is_admin:
                # 管理员登录后重定向到管理员专属页面
                return redirect(url_for('main.admin_dashboard'))
            else:
                # 普通用户登录后重定向到普通用户页面
                return redirect(url_for('main.index'))
        flash('用户名或密码错误！', 'danger')
    return render_template('login.html')

# 用户注销路由
@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


# 管理员添加题目路由
@main.route('/admin/problem/add', methods=['GET', 'POST'])
@admin_required
@login_required
def admin_add_problem():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        test_input = request.form['test_input']
        test_output = request.form['test_output']
        problem = Problem(
            title=title,
            description=description,
            test_input=test_input,
            test_output=test_output
        )
        db.session.add(problem)
        db.session.commit()
        flash('题目添加成功！', 'success')
        return redirect(url_for('main.admin_add_problem'))
    return render_template('admin/add_problem.html')


# 管理员创建比赛路由
@main.route('/admin/contest/create', methods=['GET', 'POST'])
@admin_required
@login_required
def admin_create_contest():
    if request.method == 'POST':
        title = request.form['title']
        start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')  # 修改格式字符串
        end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')  # 修改格式字符串
        problem_ids = list(map(int, request.form.getlist('problems')))  # 多选框选中的题目ID

        contest = Contest(
            title=title,
            start_time=start_time,
            end_time=end_time
        )
        # 关联题目
        for pid in problem_ids:
            problem = Problem.query.get(pid)
            contest.problems.append(problem)
        db.session.add(contest)
        db.session.commit()
        flash('比赛创建成功！', 'success')
        return redirect(url_for('main.admin_create_contest'))

    # 获取所有题目供选择
    problems = Problem.query.all()
    return render_template('admin/create_contest.html', problems=problems)


# 比赛列表页面路由
@main.route('/contests')
def contest_list():
    contests = Contest.query.all()
    return render_template('contest/list.html', contests=contests)


@main.route('/contest/<int:contest_id>')
@login_required
def contest_detail(contest_id):
    contest = Contest.query.get_or_404(contest_id)
    now = datetime.now()  # 修改这里，给当前时间加上 UTC 时区信息
    print(now)
    now = now.replace(second=0, microsecond=0)
    # 检查比赛是否在进行中
    is_active = now <= contest.end_time
    return render_template('contest/detail.html', contest=contest, is_active=is_active)


# 比赛提交路由
@main.route('/contest/<int:contest_id>/submit', methods=['POST'])  # 修改路由，去掉 problem_id 参数
@login_required
def contest_submit(contest_id):
    contest = Contest.query.get_or_404(contest_id)
    # 从表单中获取 problem_id
    problem_id = request.form.get('problem_id', type=int)
    problem = Problem.query.get_or_404(problem_id)
    now = datetime.now().replace(second=0, microsecond=0)

    # 检查比赛时间
    if not (contest.start_time <= now <= contest.end_time):
        flash('比赛已结束！', 'danger')
        return redirect(url_for('main.contest_detail', contest_id=contest_id))

    code = request.form['code']
    language = request.form['language']
    result = docker_judge(code, problem.test_input, problem.test_output, language)

    # 记录比赛提交
    submission = ContestSubmission(
        user_id=current_user.id,
        contest_id=contest_id,
        problem_id=problem_id,
        result=result
    )
    db.session.add(submission)
    db.session.commit()

    return redirect(url_for('main.contest_detail', contest_id=contest_id))

# 实时排名接口路由
@main.route('/contest/<int:contest_id>/rank')
def contest_rank(contest_id):
    # 获取所有用户在该比赛中的正确提交数和最新提交时间
    submissions = db.session.query(
        ContestSubmission.user_id,
        ContestSubmission.problem_id,
        db.func.max(ContestSubmission.submission_time).label('last_submit')
    ).filter(
        ContestSubmission.contest_id == contest_id,
        ContestSubmission.result == 'Accepted'
    ).group_by(
        ContestSubmission.user_id,
        ContestSubmission.problem_id
    ).subquery()

    # 计算每个用户的得分和用时
    rank_data = db.session.query(
        User.username,
        db.func.count(submissions.c.problem_id).label('score'),
        db.func.max(submissions.c.last_submit).label('last_submit')
    ).join(
        submissions, User.id == submissions.c.user_id
    ).group_by(
        User.id
    ).order_by(
        db.desc('score'),
        db.asc('last_submit')
    ).all()

    return render_template('contest/rank.html', rank_data=rank_data)