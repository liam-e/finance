import datetime as dt
import smtplib
from email.message import EmailMessage

import data_loader

with open("data/email_auth.txt", "r") as f:
    lines = f.readlines()
    email_address = lines[0].strip()
    email_password = lines[0].strip()

msg = EmailMessage()

start = dt.datetime(2018, 12, 1)
now = dt.datetime.now()

stock = "QQQ"
target_price = 180

msg["Subject"] = f"Alert on {stock}"
msg["From"] = email_address
msg["To"] = email_address

alerted = False

df = data_loader.load_price_history(stock, start, now)

current_close = df["Adj Close"][-1]

condition = current_close > target_price

if not alerted and condition:
    message = f"{stock} has activated the alert price of {target_price:.2f}\nCurrent price: {current_close:.2f}"

    print(message)

    msg.set_content(message)

    files = ["old/all_stocks.xlsx"]

    for file in files:
        with open(file, "rb") as f:
            file_data = f.read()
            file_name = file.split("/")[-1]

            msg.add_attachment(file_data, maintype="application", subtype="ocetet-stream", filename=file_name)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(email_address, email_password)
        smtp.send_message(msg)

        print("Completed.")

    alerted = True
