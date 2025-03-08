from flask import Flask, render_template, jsonify
import subprocess
import os
import sys
import time

app = Flask(__name__, template_folder=os.path.dirname(os.path.abspath(__file__)))

@app.route('/')
def index():
    return render_template('refresh_cookies.html')

@app.route('/refresh_cookies', methods=['POST'])
def refresh_cookies():
    try:
        # Get the path to the bypass.py script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        bypass_script = os.path.join(script_dir, "bypass.py")
        
        # Run the bypass script as a subprocess
        result = subprocess.run(
            [sys.executable, bypass_script],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Check if cookies.json exists after running the script
        cookie_file = os.path.join(script_dir, "cookies.json")
        if os.path.exists(cookie_file):
            return jsonify({
                "success": True,
                "message": "Cookies have been successfully refreshed!"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Cookies file was not created",
                "output": result.stdout
            }), 500
            
    except subprocess.CalledProcessError as e:
        return jsonify({
            "success": False,
            "message": "Failed to run bypass script",
            "stdout": e.stdout,
            "stderr": e.stderr
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"An error occurred: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080)
