import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = "smtpout.secureserver.net"
SMTP_PORT = 465 
EMAIL = "info@madiriclet.com"
PASSWORD = "aBhi@12345.ab"

to_email = "abhilashreddy5337@gmail.com"

subject = "Test Email from Madiriclet"
body = "Hello,\n\nTitan SMTP is working successfully!\n\n- Madiriclet Team"

message = MIMEMultipart()
message["From"] = EMAIL
message["To"] = to_email
message["Subject"] = subject
message.attach(MIMEText(body, "plain"))

try:
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    server.ehlo()
    server.starttls()   # 🔐 required for port 587
    server.ehlo()

    server.login(EMAIL, PASSWORD)
    server.send_message(message)

    print("✅ Email sent successfully!")
    server.quit()

except Exception as e:
    print("❌ Error:")
    print(e)