"""
MiroFish Backend - Quart应用工厂 (Async)
"""

import os
import warnings

# 抑制 multiprocessing resource_tracker 的警告（来自第三方库如 transformers）
# 需要在所有其他导入之前设置
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from quart import Quart, request
from quart_cors import cors

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Quart应用工厂函数"""
    app = Quart(__name__)
    app.config.from_object(config_class)

    # 设置JSON编码：确保中文直接显示（而不是 \uXXXX 格式）
    app.json.ensure_ascii = False

    # 设置日志
    logger = setup_logger('mirofish')

    # Quart在开发模式下使用QUART_DEBUG或QUART_RUN_MAIN
    is_reloader_process = os.environ.get('QUART_RUN_MAIN') == 'true' or os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process

    if should_log_startup:
        logger.info("=" * 50)
        logger.info("MiroFish Backend 启动中... (Quart Async)")
        logger.info("=" * 50)

    # 启用CORS
    app = cors(app, allow_origin="*")

    # 注册模拟进程清理函数（确保服务器关闭时终止所有模拟进程）
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("已注册模拟进程清理函数")

    # 请求日志中间件
    @app.before_request
    async def log_request():
        logger = get_logger('mirofish.request')
        logger.debug(f"请求: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            data = await request.get_json(silent=True)
            logger.debug(f"请求体: {data}")

    @app.after_request
    async def log_response(response):
        logger = get_logger('mirofish.request')
        logger.debug(f"响应: {response.status_code}")
        return response

    # 注册蓝图
    from .api import graph_bp, simulation_bp, report_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')

    # 健康检查
    @app.route('/health')
    async def health():
        return {'status': 'ok', 'service': 'MiroFish Backend (Async)'}

    if should_log_startup:
        logger.info("MiroFish Backend 启动完成 (Quart Async)")

    return app
