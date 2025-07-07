# Local Development Setup Guide

## Quick Setup (Recommended)

Run the automated setup script:

```bash
./setup_local_dev.sh
```

This script will:
- Create a virtual environment
- Install all dependencies (including PyKiteConnect)
- Test imports
- Create .env file from template

## Manual Setup

If you prefer to set up manually or encounter issues:

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install pydantic (compatible with Python 3.13)
pip install "pydantic>=2.6.0"

# Install PyKiteConnect from GitHub source
pip install git+https://github.com/zerodhatech/pykiteconnect.git

# Install remaining dependencies
pip install fastapi uvicorn python-multipart python-dotenv passlib bcrypt
```

### 3. Test Installation

```bash
python3 -c "from kiteconnect import KiteConnect; print('✅ kiteconnect import successful!')"
python3 -c "import main; print('✅ main.py imports successfully!')"
```

### 4. Configure Environment

```bash
cp env.example .env
# Edit .env file with your configuration
```

## Common Issues & Solutions

### Issue: "Import kiteconnect could not be resolved"

**Cause**: PyKiteConnect is not installed in your Python environment.

**Solutions**:

1. **Virtual Environment Not Activated**:
   ```bash
   source venv/bin/activate  # Make sure virtual environment is active
   ```

2. **PyKiteConnect Not Installed**:
   ```bash
   pip install git+https://github.com/zerodhatech/pykiteconnect.git
   ```

3. **IDE/Editor Issue**:
   - **VS Code**: Select the correct Python interpreter (Ctrl/Cmd + Shift + P → "Python: Select Interpreter" → Choose `./venv/bin/python`)
   - **PyCharm**: Go to Settings → Project → Python Interpreter → Select the venv interpreter
   - **Other IDEs**: Point your IDE to use the virtual environment's Python interpreter

### Issue: "externally-managed-environment" Error

**Cause**: macOS/Homebrew Python environment restrictions.

**Solution**: Always use a virtual environment (which we've set up above).

### Issue: Pydantic Build Errors with Python 3.13

**Cause**: Older pydantic versions aren't compatible with Python 3.13.

**Solution**: Install newer pydantic version first:
```bash
pip install "pydantic>=2.6.0"
```

## Running the Application

### Start Local Development Server

```bash
# Activate virtual environment
source venv/bin/activate

# Start the server
python run.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Environment Variables

Create a `.env` file with your configuration:

```bash
# Required: Generate encryption key
ENCRYPTION_KEY=your_encryption_key_here

# Optional: Server configuration
HOST=127.0.0.1
PORT=8000
DEBUG=true
LOG_LEVEL=INFO

# Optional: CORS configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8501

# Database
DATABASE_PATH=trading_app.db
```

To generate an encryption key:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## IDE Configuration

### VS Code

1. **Install Python Extension**: Make sure the Python extension is installed
2. **Select Interpreter**: 
   - Press `Ctrl/Cmd + Shift + P`
   - Type "Python: Select Interpreter"
   - Choose `./venv/bin/python` or `./venv/bin/python3`
3. **Reload Window**: Press `Ctrl/Cmd + Shift + P` and run "Developer: Reload Window"

### PyCharm

1. **Open Project**: Open the project folder in PyCharm
2. **Configure Interpreter**:
   - Go to File → Settings (or PyCharm → Preferences on macOS)
   - Navigate to Project → Python Interpreter
   - Click the gear icon → Add
   - Choose "Existing environment"
   - Select `./venv/bin/python`
3. **Apply and OK**

### Other Editors

For other editors, ensure they're configured to use the Python interpreter from the virtual environment:
- **Path**: `./venv/bin/python` (or `./venv/Scripts/python.exe` on Windows)

## Testing Your Setup

### 1. Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs  # macOS
# or visit http://localhost:8000/docs in your browser
```

### 2. Test Imports in Python

```python
# Test all main imports
from kiteconnect import KiteConnect
from fastapi import FastAPI
import main
print("✅ All imports successful!")
```

## Development Workflow

1. **Activate Environment**: Always start by activating the virtual environment
   ```bash
   source venv/bin/activate
   ```

2. **Make Changes**: Edit your code files

3. **Test Locally**: Run the application and test your changes
   ```bash
   python run.py
   ```

4. **Commit Changes**: When ready, commit to git
   ```bash
   git add .
   git commit -m "Your changes"
   git push
   ```

5. **Auto-Deploy**: Changes pushed to main branch will automatically deploy to Railway

## Production vs Development

- **Local Development**: http://localhost:8000
- **Production**: https://web-production-de0bc.up.railway.app

Both environments use the same codebase, but different configurations:
- Local uses DEBUG=true, different CORS settings
- Production uses encrypted environment variables, production CORS settings

## Troubleshooting

### Import Errors
- Ensure virtual environment is activated
- Verify Python interpreter in your IDE
- Reinstall dependencies if needed

### Port Conflicts
- If port 8000 is busy, change PORT in .env file
- Or kill the process using the port: `lsof -ti:8000 | xargs kill`

### Database Issues
- Delete `trading_app.db` to reset database
- Ensure ENCRYPTION_KEY is set in .env

### CORS Issues
- Update ALLOWED_ORIGINS in .env for your frontend URL
- Use "*" for development (not recommended for production)

## Need Help?

1. Check the logs when running `python run.py`
2. Verify all dependencies are installed: `pip list`
3. Test individual components: `python -c "import kiteconnect"`
4. Check the production API is working: https://web-production-de0bc.up.railway.app/health

Your local environment should now mirror the production setup! 🚀 