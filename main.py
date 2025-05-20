# main.py (in root)
from mcpserver.server import mcp
import traceback

if __name__ == "__main__":
    try:
        mcp.run()
    except Exception as e:
        print(f"Error running server: {str(e)}")
        traceback.print_exc()