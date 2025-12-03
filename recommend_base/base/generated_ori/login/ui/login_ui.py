from flask import Flask, render_template_string, request, redirect, url_for, flash
import re
import requests

app = Flask(__name__)
app.secret_key = "replace-with-secure-random-key"

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
            padding: var(--spacing-l);
        }
        .container {
            max-width: 400px;
            width: 100%;
        }
        h1.title {
            font-size: var(--font-size-title);
            margin-top: var(--spacing-l);
            margin-bottom: var(--spacing-l);
            font-weight: 600;
            color: #000;
            text-align: center;
        }
        form {
            display: flex;
            flex-direction: column;
        }
        label {
            font-size: var(--font-size-label);
            margin-bottom: var(--spacing-xs);
            color: #000;
            font-weight: 500;
        }
        input[type="email"],
        input[type="password"] {
            font-size: var(--font-size-input);
            padding: var(--spacing-s);
            border: 1px solid var(--color-input-border);
            border-radius: var(--radius-input);
            margin-bottom: var(--spacing-m);
            outline-offset: 2px;
            outline-color: transparent;
            transition: outline-color 0.2s ease-in-out;
            width: 100%;
            box-sizing: border-box;
        }
        input[type="email"]:focus,
        input[type="password"]:focus {
            outline-color: var(--color-primary);
            border-color: var(--color-primary);
        }
        .helper-text {
            font-size: var(--font-size-helper);
            color: #666;
            margin-top: calc(var(--spacing-xs) * -1);
            margin-bottom: var(--spacing-m);
            user-select: none;
        }
        button.primary {
            background-color: var(--color-primary);
            color: var(--color-primary-text);
            font-size: var(--font-size-input);
            font-weight: 600;
            padding: var(--spacing-s);
            border: none;
            border-radius: var(--radius-button);
            cursor: pointer;
            transition: background-color 0.2s ease-in-out;
            margin-bottom: var(--spacing-l);
        }
        button.primary:hover,
        button.primary:focus {
            background-color: #0066d6;
        }
        .link-signup {
            text-align: center;
            font-size: var(--font-size-label);
        }
        .link-signup a {
            color: var(--color-link);
            text-decoration: none;
            font-weight: 500;
        }
        .link-signup a:hover,
        .link-signup a:focus {
            text-decoration: underline;
        }
        .error-message {
            color: var(--color-error);
            font-size: var(--font-size-helper);
            margin-bottom: var(--spacing-m);
            font-weight: 600;
            text-align: center;
        }
    </style>
</head>
<body>
    <main class="container" role="main">
        <h1 class="title">로그인</h1>
        {% if error_message %}
        <div class="error-message" role="alert">{{ error_message }}</div>
        {% endif %}
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
            />

            <label for="input_password">비밀번호</label>
            <input
                type="password"
                id="input_password"
                name="password"
                placeholder="비밀번호를 입력하세요"
                required
                autocomplete="current-password"
                aria-describedby="password_helper"
            />
            <div id="password_helper" class="helper-text">대소문자+숫자+특수기호 8자리 이상</div>

            <button type="submit" class="primary" id="btn_login">로그인</button>
        </form>
        <div class="link-signup">
            <a href="{{ url_for('signup') }}" id="link_signup">회원가입</a>
        </div>
    </main>
</body>
</html>
"""

EMAIL_REGEX = re.compile(
    r"^(?:(?:[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*)|"
    r"(?:\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|"
    r"\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")"
    r")@(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?|\["
    r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|"
    r"[a-zA-Z0-9-]*[a-zA-Z0-9]:"
    r"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|"
    r"\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)])$"
)

PASSWORD_COMPLEXITY_REGEX = re.compile(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*]).{8,}$")

def validate_input(email: str, password: str):
    if not email or not EMAIL_REGEX.match(email):
        return False, "유효하지 않은 이메일 형식입니다."
    if not password or len(password) < 8:
        return False, "비밀번호는 8자리 이상이어야 합니다."
    if not PASSWORD_COMPLEXITY_REGEX.match(password):
        return False, "비밀번호는 대문자, 소문자, 숫자, 특수기호를 각각 최소 1자 이상 포함해야 합니다."
    return True, None

@app.route("/login", methods=["GET", "POST"])
def login():
    error_message = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        valid, validation_msg = validate_input(email, password)
        if not valid:
            error_message = validation_msg
        else:
            # Call backend login API
            try:
                resp = requests.post(
                    url=request.url_root.rstrip("/") + "/api/login_api",
                    json={"email": email, "password": password},
                    timeout=5,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("errorCode") == "LOGIN_FAILED":
                        error_message = "이메일 또는 비밀번호가 일치하지 않습니다."
                    else:
                        # login_success assumed
                        return redirect(url_for("home"))
                else:
                    error_message = "로그인 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            except requests.RequestException:
                error_message = "서버와 연결할 수 없습니다. 네트워크 상태를 확인하세요."

    return render_template_string(LOGIN_TEMPLATE, tokens=TOKENS, error_message=error_message, request=request)

@app.route("/")
def home():
    return "<h1>홈페이지</h1>"

@app.route("/signup")
def signup():
    return "<h1>회원가입 페이지</h1>"

if __name__ == "__main__":
    app.run(debug=True)