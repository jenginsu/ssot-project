import sqlite3
conn = sqlite3.connect('test.db')
cursor = conn.cursor()

def login_check(user_id, user_pwd):
    if user_id == "jenginsu" and user_pwd == "1234":
        print(f"user_id={user_id}, user_pwd={user_pwd} login success")
    else:
        print(f"user_id={user_id}, user_pwd={user_pwd} login failed")

def get_admin_pwd():
    get_admin_pwd_query = "SELECT password FROM users WHERE user_id='admin'"
    cursor.execute(get_admin_pwd_query)
    admin_pwd = cursor.fetchone()
    print(f"admin_pwd={admin_pwd}")

if __name__ == "__main__":
    user_id = "jenginsu"
    user_pwd = "1234"
    login_check(user_id, user_pwd)
    get_admin_pwd()