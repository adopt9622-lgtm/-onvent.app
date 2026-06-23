import os
import requests
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change_this_secret")

CACHE = {
    "rates": {},
    "base": "USD",
    "updated": None,
    "timestamp": None,
}
HISTORY = []
SUPPORTED_CURRENCIES = [
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "RUB", "TRY", "INR", "BRL",
]
BASE_CURRENCY = "USD"
API_URL = "https://open.er-api.com/v6/latest/USD"


def fetch_rates():
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("result") != "success":
            error_message = data.get("error-type") or "API response indicated failure"
            raise ValueError(error_message)

        rates = data.get("rates", {})
        supported_rates = {code: rates.get(code) for code in SUPPORTED_CURRENCIES if code in rates}
        supported_rates[BASE_CURRENCY] = 1.0

        return {
            "rates": supported_rates,
            "base": BASE_CURRENCY,
            "updated": data.get("time_last_update_utc") or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "timestamp": data.get("time_last_update_unix"),
            "error": None,
        }
    except Exception as error:
        return {
            "rates": CACHE.get("rates", {}),
            "base": CACHE.get("base", BASE_CURRENCY),
            "updated": CACHE.get("updated"),
            "timestamp": CACHE.get("timestamp"),
            "error": str(error) or "Не удалось получить курсы из API.",
        }


def convert_amount(amount, rate_from, rate_to):
    if rate_from is None or rate_to is None:
        return None
    return amount / rate_from * rate_to


def update_cache():
    data = fetch_rates()
    if data.get("rates"):
        CACHE.update(data)
    return data


@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    conversion = None
    selected_from = "USD"
    selected_to = "EUR"
    amount_value = "1"

    if request.method == "POST":
        selected_from = request.form.get("from_currency", "USD")
        selected_to = request.form.get("to_currency", "EUR")
        amount_value = request.form.get("amount", "1")

        try:
            amount = float(amount_value)
            if amount < 0:
                raise ValueError("Сумма должна быть положительной")
            data = update_cache()

            from_rate = data["rates"].get(selected_from)
            to_rate = data["rates"].get(selected_to)

            if from_rate is None or to_rate is None:
                raise ValueError("Выбранная валюта недоступна")

            result = convert_amount(amount, from_rate, to_rate)
            conversion = {
                "amount": f"{amount:.2f}",
                "from": selected_from,
                "to": selected_to,
                "result": f"{result:.2f}",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            HISTORY.insert(0, conversion)
            if len(HISTORY) > 10:
                HISTORY.pop()
        except ValueError as error:
            message = str(error)
        except Exception:
            message = "Произошла ошибка при конвертации. Попробуйте снова."
    else:
        update_cache()

    if not CACHE.get("rates"):
        update_cache()

    return render_template_string(
        TEMPLATE,
        rates=CACHE.get("rates", {}),
        base=CACHE.get("base", "USD"),
        updated=CACHE.get("updated", "-"),
        error=CACHE.get("error", None),
        history=HISTORY,
        currencies=SUPPORTED_CURRENCIES,
        conversion=conversion,
        message=message,
        selected_from=selected_from,
        selected_to=selected_to,
        amount_value=amount_value,
    )


TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Конвертер валют</title>
    <style>
        :root {
            color-scheme: dark;
            font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #01040f;
            color: #e9f0ff;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            min-height: 100vh;
            overflow-x: hidden;
            background: radial-gradient(circle at top left, rgba(48, 131, 255, 0.24), transparent 28%),
                        radial-gradient(circle at 20% 80%, rgba(255, 74, 147, 0.18), transparent 20%),
                        radial-gradient(circle at 80% 35%, rgba(44, 239, 175, 0.16), transparent 24%),
                        linear-gradient(180deg, #070b18 0%, #02050e 100%);
        }
        .page {
            position: relative;
            width: min(1200px, 100%);
            margin: 0 auto;
            padding: 32px 24px 60px;
        }
        .glass {
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            background: rgba(10, 18, 35, 0.72);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 30px;
            box-shadow: 0 40px 120px rgba(0,0,0,0.24);
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 24px;
            margin-bottom: 28px;
            padding: 24px;
        }
        header h1 {
            margin: 0;
            font-size: clamp(2rem, 3vw, 3.4rem);
            letter-spacing: -0.04em;
        }
        header p {
            margin: 12px 0 0;
            max-width: 540px;
            line-height: 1.7;
            color: #b8c4d9;
        }
        .grid {
            display: grid;
            grid-template-columns: 1.4fr 1fr;
            gap: 24px;
        }
        .panel {
            padding: 28px;
        }
        .panel h2 {
            margin-top: 0;
            font-size: 1.35rem;
            letter-spacing: -0.02em;
        }
        .control-group {
            display: grid;
            gap: 16px;
            margin: 22px 0 0;
        }
        label {
            display: grid;
            gap: 10px;
            font-size: 0.96rem;
            color: #c8d4eb;
        }
        input[type="number"], select {
            width: 100%;
            min-height: 54px;
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.08);
            background: rgba(21, 33, 61, 0.82);
            color: #f4f9ff;
            padding: 16px 18px;
            font-size: 1rem;
            outline: none;
            transition: border 0.24s ease, transform 0.24s ease;
        }
        input[type="number"]:focus,
        select:focus {
            border-color: rgba(77, 182, 255, 0.85);
            transform: translateY(-1px);
        }
        button {
            margin-top: 14px;
            border: none;
            cursor: pointer;
            border-radius: 16px;
            padding: 16px 22px;
            width: 100%;
            font-size: 1rem;
            letter-spacing: 0.01em;
            color: #fff;
            background: linear-gradient(135deg, #5c99ff 0%, #4bc1ff 100%);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            box-shadow: 0 18px 30px rgba(77, 182, 255, 0.16);
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 22px 38px rgba(77, 182, 255, 0.22);
        }
        .status {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 10px 16px;
            border-radius: 14px;
            background: rgba(255,255,255,0.06);
            color: #d8e6ff;
            font-size: 0.94rem;
            margin-top: 18px;
        }
        .status span {
            display: inline-flex;
            width: 10px;
            height: 10px;
            border-radius: 999px;
            background: #52d489;
        }
        .rates, .history, .conversion-result {
            margin-top: 20px;
            display: grid;
            gap: 16px;
        }
        .rate-card, .history-item {
            padding: 18px 20px;
            border-radius: 22px;
            background: rgba(16, 29, 51, 0.85);
            border: 1px solid rgba(255,255,255,0.05);
        }
        .rate-card strong {
            display: block;
            font-size: 1rem;
            margin-bottom: 8px;
            color: #e8f7ff;
        }
        .rate-card small {
            color: #aac9f6;
        }
        .history-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
        }
        .history-list {
            max-height: 400px;
            overflow: auto;
            display: grid;
            gap: 12px;
            padding-right: 4px;
        }
        .conversion-result {
            padding: 16px 20px;
            border-radius: 22px;
            background: rgba(25, 40, 71, 0.9);
            border: 1px solid rgba(255,255,255,0.08);
        }
        .conversion-result strong {
            display: block;
            font-size: 1.2rem;
            margin-bottom: 8px;
            letter-spacing: -0.03em;
        }
        .message {
            margin-top: 14px;
            padding: 14px 18px;
            border-radius: 18px;
            background: rgba(255, 71, 99, 0.12);
            color: #ffd3d9;
            border: 1px solid rgba(255, 71, 99, 0.18);
        }
        .grid-secondary {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 18px;
            margin-top: 18px;
        }
        .metric {
            padding: 18px 20px;
            border-radius: 22px;
            background: rgba(20, 31, 53, 0.86);
            border: 1px solid rgba(255,255,255,0.05);
        }
        .metric span {
            display: block;
            margin-top: 10px;
            color: #9abcf3;
        }
        @media (max-width: 950px) {
            .grid { grid-template-columns: 1fr; }
        }
        @media (max-width: 700px) {
            .page { padding: 18px 16px 48px; }
            header { flex-direction: column; }
        }
    </style>
</head>
<body>
    <div class="page">
        <div class="glass">
            <header>
                <div>
                    <h1>Конвертер валют</h1>
                    <p>Актуальные курсы, история операций и удобный конвертер в одной странице. Все данные получены из открытого API exchangerate.host в реальном времени.</p>
                </div>
                <div class="status" aria-live="polite">
                    <span></span>
                    <div>Обновлено: {{ updated }}</div>
                </div>
            </header>
            <div class="grid">
                <section class="panel">
                    <h2>Панель конвертации</h2>
                    <form method="post">
                        <div class="control-group">
                            <label>
                                Сумма
                                <input type="number" name="amount" step="0.01" min="0" value="{{ amount_value }}" required />
                            </label>
                            <label>
                                Из валюты
                                <select name="from_currency">
                                    {% for code in currencies %}
                                        <option value="{{ code }}" {% if code == selected_from %}selected{% endif %}>{{ code }}</option>
                                    {% endfor %}
                                </select>
                            </label>
                            <label>
                                В валюту
                                <select name="to_currency">
                                    {% for code in currencies %}
                                        <option value="{{ code }}" {% if code == selected_to %}selected{% endif %}>{{ code }}</option>
                                    {% endfor %}
                                </select>
                            </label>
                            <button type="submit">Конвертировать</button>
                        </div>
                    </form>

                    {% if message %}
                        <div class="message">{{ message }}</div>
                    {% endif %}

                    {% if conversion %}
                    <div class="conversion-result">
                        <strong>{{ conversion.amount }} {{ conversion.from }} = {{ conversion.result }} {{ conversion.to }}</strong>
                        <div>Время выполнения: {{ conversion.time }}</div>
                    </div>
                    {% endif %}

                    <div class="grid-secondary">
                        <div class="metric">
                            <strong>База курсов</strong>
                            <span>{{ base }}</span>
                        </div>
                        <div class="metric">
                            <strong>Сохранено операций</strong>
                            <span>{{ history|length }} последних</span>
                        </div>
                    </div>
                </section>

                <section class="panel">
                    <h2>Текущие курсы</h2>
                    <div class="rates">
                        {% if error %}
                            <div class="message">API error: {{ error }}</div>
                        {% endif %}
                        {% for code, rate in rates.items() %}
                            <div class="rate-card">
                                <strong>{{ code }} / {{ base }}</strong>
                                <small>1 {{ base }} = {{ '%.4f'|format(rate) }} {{ code }}</small>
                            </div>
                        {% endfor %}
                    </div>

                    <div class="history">
                        <div class="history-header">
                            <h2>История конвертаций</h2>
                        </div>
                        <div class="history-list">
                            {% if history %}
                                {% for item in history %}
                                    <div class="history-item">
                                        <strong>{{ item.amount }} {{ item.from }} → {{ item.result }} {{ item.to }}</strong>
                                        <small>{{ item.time }}</small>
                                    </div>
                                {% endfor %}
                            {% else %}
                                <div class="rate-card">История пуста. Выполните первую конвертацию.</div>
                            {% endif %}
                        </div>
                    </div>
                </section>
            </div>
        </div>
    </div>
    <script>
        const body = document.body;
        let hue = 210;
        function animateBackground() {
            hue = (hue + 0.35) % 360;
            body.style.background = `radial-gradient(circle at top left, hsla(${hue}, 85%, 55%, 0.18), transparent 28%),
                radial-gradient(circle at 20% 80%, hsla(${(hue + 90) % 360}, 93%, 72%, 0.16), transparent 20%),
                radial-gradient(circle at 80% 35%, hsla(${(hue + 190) % 360}, 74%, 65%, 0.14), transparent 24%),
                linear-gradient(180deg, #070b18 0%, #02050e 100%);`;
            requestAnimationFrame(animateBackground);
        }
        requestAnimationFrame(animateBackground);
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
