import os
import sys
import subprocess
from flask import jsonify

def refresh_cookies_endpoint():
    try:
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
                return jsonify({
                    "success": True,
                    "message": "Cookies refreshed successfully!"
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "Cookies file was not created.",
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
