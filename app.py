from paths import load_env

load_env()

from change_password import ChangePasswordWindow
from GUI import OfflineChatbot
from login import LoginWindow

if __name__ == "__main__":
    while True:
        login = LoginWindow()
        login.mainloop()

        if not getattr(login, "logged_in_username", None):
            break

        username = login.logged_in_username
        user_name = login.logged_in_user

        if getattr(login, "must_change_password", False):
            pw_win = ChangePasswordWindow(username, required=True)
            pw_win.mainloop()
            if not pw_win.success:
                continue

        app = OfflineChatbot(user_name=user_name, username=username)
        app.mainloop()

        if not getattr(app, "logged_out", False):
            break
