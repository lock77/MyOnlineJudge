from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin  # 导入 UserMixin

db = SQLAlchemy()

# 用户表（新增）
class User(db.Model, UserMixin):  # 继承 UserMixin
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # 管理员标记

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
# 比赛表（新增）
class Contest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    # 比赛与题目多对多关系（新增中间表）
    problems = db.relationship('Problem', secondary='contest_problem', backref='contests')

# 比赛-题目关联表（新增）
contest_problem = db.Table(
    'contest_problem',
    db.Column('contest_id', db.Integer, db.ForeignKey('contest.id'), primary_key=True),
    db.Column('problem_id', db.Integer, db.ForeignKey('problem.id'), primary_key=True)
)

# 比赛提交表（新增）
class ContestSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'), nullable=False)
    result = db.Column(db.String(50))
    submission_time = db.Column(db.DateTime, default=db.func.now())

class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    test_input = db.Column(db.Text)
    test_output = db.Column(db.Text)

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_code = db.Column(db.Text, nullable=False)
    result = db.Column(db.String(50))
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))