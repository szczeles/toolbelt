#!/usr/bin/env python3.6

import argparse
from spamer import Spamer
from librus import LibrusSession
from difflib import Differ

parser = argparse.ArgumentParser()
parser.add_argument('--librus-user')
parser.add_argument('--librus-password')
parser.add_argument('--gmail-user')
parser.add_argument('--gmail-password')
parser.add_argument('--rcpt')
parser.add_argument('--state-file')
args = parser.parse_args()


session = LibrusSession()
session.login(args.librus_user, args.librus_password)

current_state = []
for message in session.list_messages(get_content=True):
    current_state.extend([
        f'Nadawca: {message.sender}',
        f'Temat: {message.subject}',
        f'Wysłano: {message.sent_at}',
        f'Wiadomość: ' + message.content.replace("\n", "<br/>"),
        '<hr/>'
    ])

try:
    with open(args.state_file) as f:
        previous_state = [line.strip() for line in f.readlines()]
except:
    previous_state = []

if previous_state != current_state:
    diff = list(Differ().compare(previous_state, current_state))
    email = '<br />\n'.join(diff)
    print(email)
    spamer = Spamer(args.gmail_user, args.gmail_password, args.rcpt)
    spamer.send(email)
else:
    print("No change")

with open(args.state_file, 'w') as f:
    for line in current_state:
        f.write(f'{line}\n')
