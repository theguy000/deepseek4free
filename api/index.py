import sys
import os

# Add the parent directory to the path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create a simple dummy module to prevent import errors from dsk
# This is a workaround for Vercel's issues with the dsk package
sys.modules['dsk'] = type('obj', (object,), {
    'api': type('obj', (object,), {
        'DeepSeekAPI': lambda *args, **kwargs: None
    })
})

from app.main import app
from fastapi.middleware.cors import CORSMiddleware

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Export the app for Vercel
handler = app
