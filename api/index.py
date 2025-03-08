import sys
import os

# Add the parent directory to the path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create a more comprehensive dummy module for dsk
class DummyAPI:
    def __init__(self, *args, **kwargs):
        pass
    
    def create_chat_session(self):
        return "dummy-session-id"
    
    def chat_completion(self, **kwargs):
        yield {"content": "This is a placeholder response. The actual DeepSeek API cannot run in serverless environment."}

# Create the dummy dsk module
sys.modules['dsk'] = type('obj', (object,), {
    'api': type('obj', (object,), {
        'DeepSeekAPI': DummyAPI
    }),
    'bypass': type('obj', (object,), {})
})

# Import the application
from app.main import app

# Export the app for Vercel
handler = app
