import os
import sys
import subprocess
import json
import traceback
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/refresh_cookies")
async def refresh_cookies():
    try:
        print("Starting cookie refresh process...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Adjust path to find the bypass script
        bypass_script = os.path.join(script_dir, "..", "dsk", "bypass.py")

        if not os.path.exists(bypass_script):
            print(f"Bypass script not found at {bypass_script}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": f"Bypass script not found at {bypass_script}"
                }
            )

        # Check if the bypass script is executable
        if not os.access(bypass_script, os.X_OK):
            print(f"Bypass script is not executable: {bypass_script}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": f"Bypass script is not executable: {bypass_script}"
                }
            )

        # Run the bypass script as a subprocess
        print(f"Running bypass script: {bypass_script}")
        try:
            result = subprocess.run(
                [sys.executable, bypass_script],
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout
            )
            print(f"Bypass script completed with return code: {result.returncode}")
        except Exception as e:
            print(f"Error running bypass script: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": f"Error running bypass script: {str(e)}"
                }
            )

        # Check the exit code to determine success
        if result.returncode == 0:
            cookie_file = os.path.join(os.path.dirname(bypass_script), "cookies.json")
            if os.path.exists(cookie_file):
                # Verify the cookie file has valid content
                try:
                    with open(cookie_file, 'r') as f:
                        cookie_data = json.load(f)

                    if 'cookies' not in cookie_data:
                        return JSONResponse(
                            status_code=500,
                            content={"success": False, "message": "Cookie file exists but is missing 'cookies' key"}
                        )
                    if 'cf_clearance' not in cookie_data['cookies']:
                        return JSONResponse(
                            status_code=500,
                            content={"success": False, "message": "Cookie file exists but is missing 'cf_clearance' cookie"}
                        )
                    return {"success": True, "message": "Cookies refreshed successfully!"}
                except json.JSONDecodeError:
                    print("Cookie file contains invalid JSON")
                    return JSONResponse(
                        status_code=500,
                        content={"success": False, "message": "Cookie file exists but contains invalid JSON"}
                    )
            else:
                print("Cookies file was not created")
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "message": "Cookies file was not created",
                        "output": result.stdout
                    }
                )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Bypass script failed",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            )

    except subprocess.TimeoutExpired:
        return JSONResponse(
            status_code=504,
            content={
                "success": False,
                "message": "Operation timed out. The bypass process may still be running in the background."
            }
        )
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"An error occurred: {str(e)}\n{error_trace}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"An error occurred: {str(e)}"
            }
        )
