#!/usr/bin/python3
import argparse
import datetime
import re

import requests

parser = argparse.ArgumentParser()
parser.add_argument("phone_number")
parser.add_argument("password")
args = parser.parse_args()

print(datetime.datetime.now())
with requests.Session() as s:
    s.post(
        "https://ssl.plusgsm.pl/ebok-web/basic/loginStep2.action",
        data={"msisdn": args.phone_number, "password": args.password, "brandId": ""},
    )
    html = s.get(
        "https://ssl.plusgsm.pl/ebok-web/spectrum/packages/show.action"
    ).content.decode("utf-8")
    packages = re.findall(
        '<span class="text_12_bold">\\s+(.*)\\s+</span>\\s+</td>\\s+'
        + '<td>\\s+<span class="text_12">\\s+<ul>\\s+<li>\\s+Dla telefonu <[^<]+</li>\\s+</ul>\\s+</span>\\s+</td>\\s+'
        + '<td align="center">\\s+<span class="text_12">\\s+([0-9,]+) GB\\s+',
        html,
    )
    for package in packages:
        print("%s: %.2f GB" % (package[0].strip(), float(package[1].replace(",", "."))))

print()
