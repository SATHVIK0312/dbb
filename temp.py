# REMOVE broken main stub
import re
cleaned = re.sub(r"if __name__\s*==\s*['\"]__main__['\"]\s*:\s*$", "", cleaned, flags=re.MULTILINE)


# --- no enhanced context in Azure version ---
await websocket.send_text(json.dumps({
    "status": "AUTO_HEALING",
    "log": "Execution failed. Starting auto-healing..."
}))


