import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class Spamer:
    def __init__(self, gmail_user, gmail_pass, rcpt):
        self.gmail_user = gmail_user
        self.gmail_pass = gmail_pass
        self.recipients = [rcpt]

    def send(self, content):
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Nowe buty od AMW!"
        msg["From"] = "AMW watcher"
        msg["To"] = self.recipients[0]
        part1 = MIMEText(content, "html", "utf-8")
        msg.attach(part1)

        smtpserver = smtplib.SMTP("smtp.gmail.com", 587)
        smtpserver.ehlo()
        smtpserver.starttls()
        smtpserver.login(self.gmail_user, self.gmail_pass)
        smtpserver.sendmail(self.recipients[0], self.recipients, msg.as_string())
        smtpserver.close()
