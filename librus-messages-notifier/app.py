#!/usr/bin/env python3

import argparse
import sys
from difflib import Differ

from librus import LibrusSession

from spamer import Spamer

parser = argparse.ArgumentParser()
parser.add_argument("--librus-user")
parser.add_argument("--librus-password")
parser.add_argument("--gmail-user")
parser.add_argument("--gmail-password")
parser.add_argument("--rcpt")
parser.add_argument("--state-file")
args = parser.parse_args()


session = LibrusSession()
session.login(args.librus_user, args.librus_password)

current_state = []
for message in session.list_messages(get_content=True):
    current_state.extend(
        [
            f"Nadawca: {message.sender}",
            f"Temat: {message.subject}",
            f"Wysłano: {message.sent_at}",
            "Wiadomość:" + message.content.replace("\n", "<br/>"),
            "<hr/>",
        ]
    )

if len(current_state) == 0:  # No messages, librus issue
    print("No messages returned, skipping")
    sys.exit(1)

last_message_ts = str(next(session.list_messages()).sent_at)

try:
    with open(args.state_file) as f:
        previous_state = f.read()
except:
    previous_state = None

if previous_state != last_message_ts:
    email = "<br />\n".join(current_state)
    print(email)
    spamer = Spamer(args.gmail_user, args.gmail_password, args.rcpt)
    spamer.send(email)
else:
    print("No change")

with open(args.state_file, "w") as f:
    f.write(last_message_ts)
