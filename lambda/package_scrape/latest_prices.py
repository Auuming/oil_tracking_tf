import json
import re
import urllib.request
from html.parser import HTMLParser

KAPOOK_URL = 'http://gasprice.kapook.com/gasprice.php'



def normalize_space(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()



def make_thai_key(label: str) -> str:
    return normalize_space(label).replace(' ', '_')



def split_label_price(row_text: str):
    text = normalize_space(row_text)
    match = re.match(r'^(.*?)(\d+(?:\.\d+)?)$', text)
    if not match:
        return text, ''

    label = normalize_space(match.group(1))
    price = match.group(2)
    return label, price


class KapookParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_h2 = False
        self.in_h3 = False
        self.in_li = False
        self.date_text = ''
        self.current_station = None
        self.current_li_text = ''
        self.station_rows = {}

    def handle_starttag(self, tag, attrs):
        if tag == 'h2':
            self.in_h2 = True
        elif tag == 'h3':
            self.in_h3 = True
        elif tag == 'li':
            self.in_li = True
            self.current_li_text = ''

    def handle_endtag(self, tag):
        if tag == 'h2':
            self.in_h2 = False
        elif tag == 'h3':
            self.in_h3 = False
        elif tag == 'li':
            self.in_li = False
            row = normalize_space(self.current_li_text)
            if self.current_station and row:
                self.station_rows.setdefault(self.current_station, []).append(row)

    def handle_data(self, data):
        text = normalize_space(data)
        if not text:
            return

        if self.in_h2:
            self.date_text += f' {text}'

        if self.in_h3:
            match = re.search(r'\(([^)]+)\)', text)
            if match:
                self.current_station = match.group(1).strip().lower()

        if self.in_li:
            self.current_li_text += f' {text}'



def build_payload(html: str):
    parser = KapookParser()
    parser.feed(html)

    date_text = normalize_space(parser.date_text)
    date_match = re.search(r'อัปเดตล่าสุด\s+(.+)$', date_text)
    formatted_date = date_match.group(1).strip() if date_match else ''

    stations = {}
    for station, rows in parser.station_rows.items():
        station_data = {}
        for row in rows:
            label, price = split_label_price(row)
            if not label:
                continue

            station_data[make_thai_key(label)] = {
                'price': price
            }

        stations[station] = station_data

    return {
        'status': 'success',
        'response': {
            'note': 'Retail Prices in Bangkok & Vicinities Unit : Baht/Litre',
            'date': formatted_date,
            'stations': stations,
        },
    }



def lambda_handler(event, context):
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
    }

    try:
        req = urllib.request.Request(
            KAPOOK_URL,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8', errors='replace')

        payload = build_payload(html)

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(payload, ensure_ascii=False),
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps(
                {
                    'status': 'failure',
                    'response': f'Service is unavailable, Please try again later. {str(e)}',
                },
                ensure_ascii=False,
            ),
        }
