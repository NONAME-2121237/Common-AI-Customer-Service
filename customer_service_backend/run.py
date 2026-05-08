import sys
import os
import argparse
import asyncio
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_config_manager
from app.utils import setup_logger

def parse_args():
    parser = argparse.ArgumentParser(description='Customer Service Backend')
    parser.add_argument('--config', '-c', default='config.yaml', help='Config file path')
    parser.add_argument('--port', '-p', type=int, default=8000, help='Main API port')
    parser.add_argument('--admin-port', '-a', type=int, default=8001, help='Admin API port')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind')
    parser.add_argument('--admin-host', default='127.0.0.1', help='Admin host to bind')
    return parser.parse_args()

def main():
    args = parse_args()
    
    os.environ['CONFIG_PATH'] = args.config
    
    logger = setup_logger('main', 'logs/app.log')
    
    try:
        config_manager = get_config_manager(args.config)
        logger.info(f"Configuration loaded from {args.config}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    import uvicorn
    
    from app.main import app as main_app
    from app.admin_main import app as admin_app
    
    def run_main():
        uvicorn.run(main_app, host=args.host, port=args.port, log_level="info")
    
    def run_admin():
        uvicorn.run(admin_app, host=args.admin_host, port=args.admin_port, log_level="info")
    
    import threading
    
    admin_thread = threading.Thread(target=run_admin, daemon=True)
    admin_thread.start()
    
    logger.info(f"Starting main API on {args.host}:{args.port}")
    logger.info(f"Starting admin API on {args.admin_host}:{args.admin_port}")
    
    run_main()

if __name__ == "__main__":
    main()
