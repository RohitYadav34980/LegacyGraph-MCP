
import mcp.server.fastmcp
import pkgutil
import inspect

print(f"Path: {mcp.server.fastmcp.__path__}")

for loader, name, is_pkg in pkgutil.walk_packages(mcp.server.fastmcp.__path__, mcp.server.fastmcp.__name__ + "."):
    print(f"Found: {name}")
    try:
        module = __import__(name, fromlist=[""])
        for attr in dir(module):
            if "FastMCP" in attr:
                print(f"!!! FOUND FastMCP in {name} !!!")
    except Exception as e:
        print(f"Error importing {name}: {e}")
