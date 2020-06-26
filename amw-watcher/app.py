#!/usr/bin/python3

import argparse
import json
import re

import requests

from spamer import Spamer

parser = argparse.ArgumentParser()
parser.add_argument("--gmail-user")
parser.add_argument("--gmail-password")
parser.add_argument("--rcpt")
parser.add_argument("--state-file")
args = parser.parse_args()

spamer = Spamer(args.gmail_user, args.gmail_password, args.rcpt)

urls = [
    ("https://sklep.amw.com.pl/pl/p/Trzewiki-desantowca/117", "Desanty"),
    (
        "https://sklep.amw.com.pl/pl/p/Trzewiki-pilota-wz.-922MON-/216",
        "Trzewiki pilota",
    ),
    ("https://sklep.amw.com.pl/pl/p/Buty-specjalne-928MON-/119", "Buty specjalne"),
]

email = ""

for url, title in urls:
    response = requests.get(url).text
    match = re.search('Shop.values.OptionsConfiguration = "([^"]*)"', response)
    if not match.group(1):
        continue
    available_sizes_keys = json.loads(match.group(1))
    available_sizes = []
    for size in re.finditer('<option value="([^"]+)">([^<]+)</option>', response):
        if int(size.group(1)) in available_sizes_keys:
            available_sizes.append(size.group(2))
    email += "<h1>{}</h1>".format(title)
    email += "<p>{}</p>".format(available_sizes)

try:
    with open(args.state_file) as f:
        previous_state = f.read()
except:
    previous_state = None

if previous_state != email:
    spamer.send(email)

with open(args.state_file, "w") as f:
    f.write(email)
