import sys
import traceback
sys.path.append("c:\\Users\\USER\\ChatOff")
try:
    from GUI import OfflineChatbot
    # Test regular user instantiation
    app_user = OfflineChatbot(user_name="test", username="test")
    # Test admin role instantiation (runs AdminFrame code)
    app_admin = OfflineChatbot(user_name="admin", username="admin")
    print("Success")
except Exception as e:
    traceback.print_exc()
