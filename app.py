from flask import Flask
from app.models import db
from app.routes import main, login_manager
from config import Config
import os

def create_app():
    template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'templates')
    # 显式指定静态文件路径
    static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app','static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    app.config.from_object(Config)

    db.init_app(app)
    app.register_blueprint(main)

    # 初始化 LoginManager
    login_manager.init_app(app)
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)