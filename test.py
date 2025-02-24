from flask import Flask
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import mysql.connector
import pandas as pd
import datetime
import schedule
import time
from dotenv import dotenv_values
import smtplib

config = dotenv_values("key.env")

# Load credentials from .env file
EMAIL_CONFIG = {
    "email": config["EMAIL_USER"],
    "password": config["EMAIL_PASS"]
}

DB_CONFIG = {
    "host": config["DB_HOST"],
    "user": config["DB_USER"],
    "password": config["DB_PASS"],
    "database": config["DB_NAME"],
    "port": int(config["DB_PORT"])
}
# Load environment variables

# Database Connection Function
def connect_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None  # Return None if connection fails


def send_email(to_email, subject, message):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_CONFIG["email"]
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "html"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_CONFIG["email"], EMAIL_CONFIG["password"])
        server.sendmail(EMAIL_CONFIG["email"], to_email, msg.as_string())
        server.quit()

        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Error sending email to {to_email}: {e}")


mail_data = ["nishantmehra604@gmail.com"]

# Function to Fetch Data and Send Emails
def mail_sender_for_due():
    print("Running scheduled task at", datetime.datetime.now())

    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(oi.car_status, 'Unknown') AS car_status, 
                       d.car_no, d.city, d.car_name, 
                       d.delivered_date as Last_service_date, d.final_service as service_type
                FROM detail AS d  
                LEFT JOIN owner_insert AS oi ON d.car_no = oi.car_no
                WHERE DATE_ADD(d.delivered_date, INTERVAL 150 DAY) 
                      BETWEEN DATE_SUB(CURDATE(), INTERVAL 1 DAY)  
                          AND DATE_ADD(CURDATE(), INTERVAL 1 DAY)
                ORDER BY DATE_ADD(d.delivered_date, INTERVAL 150 DAY), d.delivered_date;
            """)

            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df_due_service = pd.DataFrame(data, columns=columns)

            df_due_service['Last_service_date'] = df_due_service['Last_service_date'].astype(str)
            data_list = df_due_service.to_dict(orient='records')

            # Enhanced Email Content
            email_body = """
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 15px; }
                    .container { background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0px 0px 10px #cccccc; }
                    .header { background: linear-gradient(135deg, #ff6a00, #ee0979); color: white; text-align: center; padding: 12px; font-size: 16px; font-weight: bold; border-radius: 8px 8px 0 0; }
                    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                    th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
                    th { background-color: #ff6a00; color: white; }
                    tr:nth-child(even) { background-color: #f9f9f9; }
                    tr:hover { background-color: #f1f1f1; }
                    .footer { margin-top: 20px; text-align: center; font-size: 14px; color: #555; }
                </style>
            </head>
            <body>
                <div class='container'>
                    <div class='header'>🔧 Due Service Reminder 🔧</div>
                    <p>Hello,</p>
                    <p>This is a friendly reminder that the following vehicles are due for service:</p>
                    <table>
                        <tr>""" + "".join([f"<th>{col.replace('_', ' ').title()}</th>" for col in columns]) + "</tr>"

            for row in data_list:
                email_body += "<tr>" + "".join([f"<td>{row[col]}</td>" for col in columns]) + "</tr>"

            email_body += """
                    </table>
                    <p>Thank you for choosing our service! If you have any questions, feel free to contact us.</p>
                    <div class='footer'>
                        🚗 GoMechanic
                    </div>
                </div>
            </body>
            </html>
            """

            # Send emails to all admin users
            for email in mail_data:
                send_email(email, "🚗 Due Service Reminder", email_body)

    except Exception as e:
        print(f"Error in mail_sender_for_due: {e}")


# Schedule the Task to Run at 10 AM
schedule.every().day.at("12:30").do(mail_sender_for_due)


