import os
import sys
import subprocess
import json
from flask import jsonify, Blueprint

refresh_bp = Blueprint('refresh', __name__)

@refresh_bp.route('/refresh_cookies', methods=['POST'])
def refresh_cookies():
    try:
        print("Starting cookie refresh process...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        bypass_script = os.path.join(script_dir, "bypass.py")
        
        # Run the bypass script as a subprocess
        result = subprocess.run(
            [sys.executable, bypass_script],
            capture_output=True,
            text=True,
            timeout=180  # 3 minute timeout
        )
        
        # Check the exit code to determine success
        if result.returncode == 0:
            cookie_file = os.path.join(script_dir, "cookies.json")
            if os.path.exists(cookie_file):
                # Verify the cookie file has valid content
                try:
                    with open(cookie_file, 'r') as f:
                        cookie_data = json.load(f)
                        
                    if 'cookies' in cookie_data and 'cf_clearance' in cookie_data['cookies']:
                        return jsonify({
                            "success": True,
                            "message": "Cookies refreshed successfully!"
                        })
                    else:
                        return jsonify({
                            "success": False,
                            "message": "Cookie file exists but is missing required cookies"
                        }), 500
                except json.JSONDecodeError:
                    return jsonify({
                        "success": False,
                        "message": "Cookie file exists but contains invalid JSON"
                    }), 500
            else:
                return jsonify({
                    "success": False,
                    "message": "Cookies file was not created",
                    "output": result.stdout
                }), 500
        else:
            return jsonify({
                "success": False,
                "message": "Bypass script failed",
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "message": "Operation timed out. The bypass process may still be running in the background."
        }), 504
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"An error occurred: {str(e)}"
        }), 500
