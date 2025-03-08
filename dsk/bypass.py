# run_and_get_cookies.py
import subprocess
import os
import sys
import time
import requests
import json

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_cookies(cookies_data):
    """Validate that cf_clearance cookie is present and not empty"""
    cookies = cookies_data.get('cookies', {})
    return 'cf_clearance' in cookies and cookies['cf_clearance'].strip() != ''

def get_and_save_cookies(server_url, cookie_file_path, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(server_url)
            response.raise_for_status()
            cookies_data = response.json()

            if not validate_cookies(cookies_data):
                logger.info(f"Attempt {attempt + 1}: cf_clearance cookie not found, retrying...")
                time.sleep(5)
                continue

            cookies_to_save = {
                'cookies': cookies_data.get('cookies', {}),
                'user_agent': cookies_data.get('user_agent', '')
            }

            os.makedirs(os.path.dirname(cookie_file_path), exist_ok=True)
            with open(cookie_file_path, 'w', encoding='utf-8') as f:
                json.dump(cookies_to_save, f, indent=4, ensure_ascii=False)
            logger.info("Successfully obtained and saved cookies with cf_clearance!")
            return True

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                logger.error("Max retries reached. Failed to get valid cookies.")
                return False

    logger.error("Failed to obtain valid cf_clearance cookie after all attempts")
    return False

def run_server_background():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.abspath(os.path.join(script_dir, "server.py"))
    server_dir = os.path.dirname(server_script)

    os.makedirs(server_dir, exist_ok=True)

    try:
        process = subprocess.Popen(
            [sys.executable, server_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=server_dir,
            start_new_session=True
        )
        return process
    except Exception:
        return None

if __name__ == "__main__":
    logger.info("Getting the cookies...")
    server_process = run_server_background()

    if server_process:
        # Increase initial wait time to ensure server is fully started
        time.sleep(5)
        server_url = "http://localhost:9000/cookies?url=https://chat.deepseek.com"
        cookie_file = "dsk/cookies.json"

        # Increase max retries for more reliability
        success = get_and_save_cookies(server_url, cookie_file, max_retries=3)

        if not success:
            logger.error("Failed to obtain valid cookies.")
            server_process.terminate()
            sys.exit(1)
        server_process.terminate()
    else:
        logger.error("Failed to start server.")
        sys.exit(1)
