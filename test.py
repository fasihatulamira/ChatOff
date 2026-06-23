"""Quick GUI import smoke test (used by setup.ps1)."""
import sys
import traceback

from paths import load_env

load_env()

try:
    from GUI import OfflineChatbot

    app_user = OfflineChatbot(user_name="test", username="test")
    app_user.destroy()
    app_admin = OfflineChatbot(user_name="admin", username="admin")
    app_admin.destroy()
    print("Success")
except Exception:
    traceback.print_exc()
    sys.exit(1)
