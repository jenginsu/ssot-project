from flask import Flask, render_template_string, request, redirect, url_for, flash
import re
import requests

app = Flask(__name__)
app.secret_key = "replace-with-a-secure-random-key"

# Design tokens
TOKENS = {
    "colors": {
        "background": "#FFFFFF",
        "primary": "#0A84FF",
        "primaryText": "#FFFFFF",
        "inputBorder": "#CCCCCC",
        "error": "#FF3B30",
        "link": "#007AFF"
    },
    "fontSizes": {
        "title": 24,
        "label": 14,
        "input": 16,
        "helper": 12
    },
    "spacing": {
        "xs": 4,
        "s": 8,
        "m": 16,
        "l": 24
    },
    "radius": {
        "input": 4,
        "button": 6
    }
}

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>로그인</title>
    <style>
        :root {
            --color-background: {{ tokens.colors.background }};
            --color-primary: {{ tokens.colors.primary }};
            --color-primary-text: {{ tokens.colors.primaryText }};
            --color-input-border: {{ tokens.colors.inputBorder }};
            --color-error: {{ tokens.colors.error }};
            --color-link: {{ tokens.colors.link }};
            --font-size-title: {{ tokens.fontSizes.title }}px;
            --font-size-label: {{ tokens.fontSizes.label }}px;
            --font-size-input: {{ tokens.fontSizes.input }}px;
            --font-size-helper: {{ tokens.fontSizes.helper }}px;
            --spacing-xs: {{ tokens.spacing.xs }}px;
            --spacing-s: {{ tokens.spacing.s }}px;
            --spacing-m: {{ tokens.spacing.m }}px;
            --spacing-l: {{ tokens.spacing.l }}px;
            --radius-input: {{ tokens.radius.input }}px;
            --radius-button: {{ tokens.radius.button }}px;
        }
        body {
            margin: 0;
            background-color: var(--color-background);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen,
                Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            min-height: 100vh;
            padding-top: var(--spacing-l);
        }
        .container {
            width: 100%;
            max-width: 360px;
            padding: var(--spacing-l);
            box-sizing: border-box;
        }
        h1.title {
            font-size: var(--font-size-title);
            margin-bottom: var(--spacing-l);
            text-align: center;
            font-weight: 600;
            color: #000;
        }
        form {
            display: flex;
            flex-direction: column;
            gap: var(--spacing-m);
        }
        label {
            font-size: var(--font-size-label);
            margin-bottom: var(--spacing-xs);
            color: #000;
            font-weight: 500;
            display: block;
        }
        input[type="email"],
        input[type="password"] {
            font-size: var(--font-size-input);
            padding: var(--spacing-s);
            border: 1px solid var(--color-input-border);
            border-radius: var(--radius-input);
            width: 100%;
            box-sizing: border-box;
        }
        input[type="email"]:focus,
        input[type="password"]:focus {
            outline: none;
            border-color: var(--color-primary);
            box-shadow: 0 0 0 2px rgba(10, 132, 255, 0.3);
        }
        .helper-text {
            font-size: var(--font-size-helper);
            color: #666;
            margin-top: -var(--spacing-xs);
            margin-bottom: var(--spacing-s);
        }
        .error-message {
            color: var(--color-error);
            font-size: var(--font-size-helper);
            margin-top: -var(--spacing-xs);
            margin-bottom: var(--spacing-s);
            font-weight: 600;
        }
        button[type="submit"] {
            background-color: var(--color-primary);
            color: var(--color-primary-text);
            font-size: var(--font-size-input);
            padding: var(--spacing-s);
            border: none;
            border-radius: var(--radius-button);
            cursor: pointer;
            font-weight: 600;
            transition: background-color 0.2s ease-in-out;
        }
        button[type="submit"]:hover,
        button[type="submit"]:focus {
            background-color: #0066d6;
            outline: none;
        }
        .signup-link {
            margin-top: var(--spacing-m);
            text-align: center;
            font-size: var(--font-size-label);
        }
        .signup-link a {
            color: var(--color-link);
            text-decoration: none;
            font-weight: 500;
        }
        .signup-link a:hover,
        .signup-link a:focus {
            text-decoration: underline;
            outline: none;
        }
    </style>
</head>
<body>
    <main class="container" role="main" aria-labelledby="login-title">
        <h1 id="login-title" class="title">로그인</h1>
        {% with messages = get_flashed_messages(category_filter=["error"]) %}
          {% if messages %}
            <div class="error-message" role="alert" aria-live="assertive">{{ messages[0] }}</div>
          {% endif %}
        {% endwith %}
        <form method="post" novalidate>
            <label for="input_email">아이디(이메일)</label>
            <input
                type="email"
                id="input_email"
                name="email"
                placeholder="example@domain.com"
                required
                autocomplete="username"
                value="{{ request.form.email | default('') }}"
                aria-describedby="email_error"
            />
            {% if errors.email %}
                <div id="email_error" class="error-message" role="alert">{{ errors.email }}</div>
            {% endif %}

            <label for="input_password">비밀번호</label>
            <input
                type="password"
                id="input_password"
                name="password"
                placeholder="비밀번호를 입력하세요"
                required
                autocomplete="current-password"
                aria-describedby="password_helper password_error"
            />
            <div id="password_helper" class="helper-text">대소문자+숫자+특수기호 8자리 이상</div>
            {% if errors.password %}
                <div id="password_error" class="error-message" role="alert">{{ errors.password }}</div>
            {% endif %}

            <button type="submit" id="btn_login">로그인</button>
        </form>
        <div class="signup-link">
            <a href="{{ url_for('signup') }}" id="link_signup">회원가입</a>
        </div>
    </main>
</body>
</html>
"""

# Validation helpers
EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
PASSWORD_REGEX = re.compile(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*]).{8,}$")

def validate_email(email: str) -> str | None:
    if not email:
        return "필수 입력 항목입니다."
    if len(email) > 255:
        return "이메일은 255자 이하여야 합니다."
    if not EMAIL_REGEX.match(email):
        return "유효한 이메일 형식이 아닙니다."
    return None

def validate_password(password: str) -> str | None:
    if not password:
        return "필수 입력 항목입니다."
    if len(password) < 8:
        return "비밀번호는 8자 이상이어야 합니다."
    if not PASSWORD_REGEX.match(password):
        return "대문자/소문자/숫자/특수문자를 모두 포함해야 합니다."
    return None

@app.route("/login", methods=["GET", "POST"])
def login():
    errors = {}
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # Validate inputs
        email_error = validate_email(email)
        password_error = validate_password(password)
        if email_error:
            errors["email"] = email_error
        if password_error:
            errors["password"] = password_error

        if not errors:
            # Call backend login API
            try:
                resp = requests.post(
                    url=request.url_root.rstrip("/") + "/api/login_api",
                    json={"email": email, "password": password},
                    timeout=5,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("result") == "success":
                        return redirect(url_for("home"))
                    else:
                        error_code = data.get("errorCode", "")
                        if error_code == "LOGIN_FAILED":
                            flash("로그인에 실패했습니다. 이메일과 비밀번호를 확인하세요.", "error")
                        elif error_code == "ACCOUNT_LOCKED":
                            flash("계정이 잠금 상태입니다. 관리자에게 문의하세요.", "error")
                        else:
                            flash("알 수 없는 오류가 발생했습니다.", "error")
                else:
                    flash("서버와 통신 중 오류가 발생했습니다.", "error")
            except Exception:
                flash("서버와 통신 중 오류가 발생했습니다.", "error")

    return render_template_string(LOGIN_TEMPLATE, tokens=TOKENS, errors=errors)

@app.route("/")
def home():
    return "<h1>홈페이지</h1>"

@app.route("/signup")
def signup():
    return "<h1>회원가입 페이지</h1>"

if __name__ == "__main__":
    app.run(debug=True)