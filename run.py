import sys
import os
import subprocess

# Check if we are running from the virtual environment
if 'venv' not in sys.executable.lower():
    venv_python = os.path.join(os.path.dirname(__file__), 'venv', 'Scripts', 'python.exe')
    if os.path.exists(venv_python):
        print(f"Auto-switching to virtual environment: {venv_python}")
        # Relaunch this exact script using the virtual environment's python
        subprocess.run([venv_python, __file__] + sys.argv[1:])
        sys.exit(0)
    else:
        print("Error: Virtual environment not found.")
        sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

from streamlit.web import cli as stcli

if __name__ == '__main__':
    port = os.getenv("PORT", "8501")
    # Equivalent to running: streamlit run app_streamlit.py --server.address=0.0.0.0 --server.port=<port>
    sys.argv = ["streamlit", "run", "app_streamlit.py", "--server.address", "0.0.0.0", "--server.port", port]
    sys.exit(stcli.main())
