import sys
import traceback
sys.path.append("c:\\Users\\USER\\ChatOff")
try:
    from GUI import OfflineChatbot
    app = OfflineChatbot(user_name="test", username="test")
    print("Success")
except Exception as e:
    traceback.print_exc()
