import sys
import re
import json
import requests
from bs4 import BeautifulSoup


SITE_URL = "https://bank.gov.ua/ua/markets/exchangerates"
API_URL  = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (HTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def fetch_html(url: str):
    """Завантажити HTML-сторінку та повернути об'єкт BeautifulSoup."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.exceptions.ConnectionError:
        print("  [!] Помилка з'єднання з сервером.")
    except requests.exceptions.Timeout:
        print("  [!] Час очікування відповіді вичерпано.")
    except requests.exceptions.HTTPError as e:
        print(f"  [!] Помилка HTTP: {e}")
    return None


def parse_html(soup):
    """Розбір HTML-таблицю"""
    rates = []
    date  = "невідома дата"

    for tag in soup.find_all(["h2", "h3", "p", "div", "span", "time"]):
        text  = tag.get_text(strip=True)
        match = re.search(r"\d{2}\.\d{2}\.\d{4}", text)
        if match:
            date = match.group(0)
            break

    table = soup.find("table", {"id": "exchangeRates"}) or soup.find("table")
    if table is None:
        return rates, date

    tbody = table.find("tbody")
    rows  = tbody.find_all("tr") if tbody else table.find_all("tr")[1:]

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue
        try:
            code_num = cols[0].get_text(strip=True)
            code_lit = cols[1].get_text(strip=True)
            units    = cols[2].get_text(strip=True)
            name     = cols[3].get_text(strip=True)
            rate     = cols[4].get_text(strip=True)

            if not code_num or not code_lit:
                continue
            if units and units != "1":
                name = f"{name} (за {units} од.)"

            rates.append({"code_num": code_num, "code_lit": code_lit,
                          "name": name, "rate": rate})
        except (IndexError, AttributeError):
            continue

    return rates, date

def fetch_api():
    """Отримати курс"""
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"  [!] API недоступний: {e}")
        return [], "невідома дата"
    except json.JSONDecodeError:
        print("  [!] Отримано некоректний JSON від API.")
        return [], "невідома дата"

    rates = []
    date  = "невідома дата"

    for item in data:
        if date == "невідома дата" and "exchangedate" in item:
            date = item["exchangedate"]

        units    = int(item.get("units", 1))
        name     = item.get("txt", "")
        if units != 1:
            name = f"{name} (за {units} од.)"

        code_num = str(item.get("r030", "")).zfill(3)
        rate_val = item.get("rate", 0)

        rates.append({
            "code_num": code_num,
            "code_lit": item.get("cc", ""),
            "name":     name,
            "rate":     f"{rate_val:.4f}".replace(".", ","),
        })

    return rates, date

def print_table(rates, date):
    """Вивести курси"""
    if not rates:
        print("Дані відсутні.")
        return

    W_NUM  = 14
    W_LIT  = 14
    W_NAME = 38
    W_RATE = 18

    sep = ("+" + "-" * W_NUM + "+" + "-" * W_LIT +
           "+" + "-" * W_NAME + "+" + "-" * W_RATE + "+")

    title = f" Офіційні курси валют НБУ станом на {date} "
    print()
    print(title.center(len(sep), "="))
    print()
    print(sep)
    print(f"|{'Код цифровий':^{W_NUM}}|{'Код літерний':^{W_LIT}}"
          f"|{'Назва валюти':^{W_NAME}}|{'Офіційний курс':^{W_RATE}}|")
    print(sep)

    for r in rates:
        name = r["name"]
        if len(name) > W_NAME - 2:
            name = name[:W_NAME - 5] + "..."
        print(f"| {r['code_num']:<{W_NUM-2}} | {r['code_lit']:<{W_LIT-2}} "
              f"| {name:<{W_NAME-2}} | {r['rate']:>{W_RATE-2}} |")

    print(sep)
    print(f"\n  Всього валют: {len(rates)}")
    print()

def print_table(rates, date):
    """Вивести курси"""
    if not rates:
        print("Дані відсутні.")
        return

    W_NUM  = 14
    W_LIT  = 14
    W_NAME = 38
    W_RATE = 18

    sep = ("+" + "-" * W_NUM + "+" + "-" * W_LIT +
           "+" + "-" * W_NAME + "+" + "-" * W_RATE + "+")

    title = f" Офіційні курси валют НБУ станом на {date} "
    print()
    print(title.center(len(sep), "="))
    print()
    print(sep)
    print(f"|{'Код цифровий':^{W_NUM}}|{'Код літерний':^{W_LIT}}"
          f"|{'Назва валюти':^{W_NAME}}|{'Офіційний курс':^{W_RATE}}|")
    print(sep)

    for r in rates:
        name = r["name"]
        if len(name) > W_NAME - 2:
            name = name[:W_NAME - 5] + "..."
        print(f"| {r['code_num']:<{W_NUM-2}} | {r['code_lit']:<{W_LIT-2}} "
              f"| {name:<{W_NAME-2}} | {r['rate']:>{W_RATE-2}} |")

    print(sep)
    print(f"\n  Всього валют: {len(rates)}")
    print()

def main():
    rates, date = [], "невідома дата"

    print(f"[1/2] Скрапінг сторінки: {SITE_URL}")
    soup = fetch_html(SITE_URL)
    if soup:
        rates, date = parse_html(soup)

    if not rates:
        print(f"[2/2] HTML не дав результату. Використовуємо API: {API_URL}")
        rates, date = fetch_api()

    if rates:
        print_table(rates, date)
    else:
        print("\nНе вдалося отримати курси валют. Перевірте інтернет-з'єднання.")
        sys.exit(1)


if __name__ == "__main__":
    main()
