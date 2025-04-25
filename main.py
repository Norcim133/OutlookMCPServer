# main.py (in root)
from mcpserver import server
import traceback

if __name__ == "__main__":
    try:
        server.run()
    except Exception as e:
        print(f"Error running server: {str(e)}")
        traceback.print_exc()