user_id = "jenginsu"
user_pwd = "1234"

def login_check(user_id, user_pwd):
    if user_id == "jenginsu" and user_pwd == "1234":
        print(f"user_id={user_id}, user_pwd={user_pwd} login success")
    else:
        print(f"user_id={user_id}, user_pwd={user_pwd} login failed")

if __name__ == "__main__":
    login_check(user_id, user_pwd)