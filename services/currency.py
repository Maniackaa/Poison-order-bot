import requests


def get_currency_cny():
    resp = requests.get('https://www.cbr-xml-daily.ru/daily_json.js', timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        currency = data.get('Valute')
        cny = currency.get('CNY')
        value = cny.get('Value')
        return float(value)
