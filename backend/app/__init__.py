"""
MiroFish Backend - Flask应用工厂
"""

import os
import warnings

# 抑制 multiprocessing resource_tracker 的警告（来自第三方库如 transformers）
# 需要在所有其他导入之前设置
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 设置JSON编码：确保中文直接显示（而不是 \uXXXX 格式）
    # Flask >= 2.3 使用 app.json.ensure_ascii，旧版本使用 JSON_AS_ASCII 配置
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False
    
    # 设置日志
    logger = setup_logger('mirofish')
    
    # 只在 reloader 子进程中打印启动信息（避免 debug 模式下打印两次）
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process
    
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("MiroFish Backend 启动中...")
        logger.info("=" * 50)
    
    # 启用CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # 注册模拟进程清理函数（确保服务器关闭时终止所有模拟进程）
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("已注册模拟进程清理函数")
    
    # 请求日志中间件
    @app.before_request
    def log_request():
        logger = get_logger('mirofish.request')
        logger.debug(f"请求: {request.method} {request.path}")
        # ZhouYiFish 请求可能含有运行时密钥或出生资料，不记录正文。
    
    @app.after_request
    def log_response(response):
        logger = get_logger('mirofish.request')
        logger.debug(f"响应: {response.status_code}")
        return response
    
    # MiroFish 图谱路由依赖可选组件。失败时仍提供 ZhouYiFish。
    try:
        from .api import graph_bp, simulation_bp, report_bp
        app.register_blueprint(graph_bp, url_prefix='/api/graph')
        app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
        app.register_blueprint(report_bp, url_prefix='/api/report')
    except Exception as exc:  # noqa: BLE001
        logger.warning("MiroFish 路由未注册：%s", exc.__class__.__name__)

    from .zhouyi_app.api import bp as zhouyi_bp
    app.register_blueprint(zhouyi_bp, url_prefix='/api/zhouyi')
    
    # 健康检查
    @app.route('/health')
    def health():
        from .zhouyi_app.settings import runtime
        view = runtime.public_view()
        return {
            'status': 'ok',
            'service': 'ZhouYiFish',
            'mirofish_backend': True,
            'llm_configured': view['key_configured'],
            'zep_configured': view['zep_configured'],
            'zep_required_for_core': False,
        }
    
    if should_log_startup:
        logger.info("MiroFish Backend 启动完成")
    
    return app

