import time
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from typing import Callable
from twilio.rest import Client
import requests
import datetime
import os


account_sid = os.getenv('ac_sid')
auth_token = os.getenv('auth_token')

today = datetime.datetime.today().strftime('%d-%m-%Y')

header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 '
                  'Safari/537.36'
}

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cowinSMS.db'


class MySQLAlchemy(SQLAlchemy):
    Column: Callable
    Integer: Callable
    String: Callable


db = MySQLAlchemy(app)


class CowinSMS(db.Model):
    phone_number = db.Column(db.Integer, nullable=False, primary_key=True)
    hosp_list = db.Column(db.String(500), unique=True, nullable=False)
    date = db.Column(db.String(20), nullable=False)
    district_id = db.Column(db.Integer, nullable=False)
    dose_number = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '<User%r>' % self.phone_number


db.create_all()

user_data = CowinSMS.query.all()

user_details = {}
users = []
for user in user_data:
    user_details['phone_number'] = user.phone_number
    user_details['hospital_list'] = user.hosp_list.split(",")
    user_details['date'] = user.date
    user_details['district_id'] = user.district_id
    user_details['dose_number'] = user.dose_number
    users.append(user_details)
    user_details = {}

print(f'User list: {users}')

while len(users) != 0:
    time.sleep(5)
    for user in users:
        if today == user['date']:
            print(user['phone_number'])
            URL_APPOINTMENT = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/" \
                                f"calendarByDistrict?district_id={user['district_id']}&" \
                                f"date={today}"
            response = requests.get(URL_APPOINTMENT, headers=header)
            data = response.json()['centers']
            for hospital in data:
                if hospital['name'] in user['hospital_list']:
                    for sessions in hospital['sessions']:
                        if sessions['date'] == today:

                            if user['dose_number'] == 1 and sessions['available_capacity_dose1'] > 0:
                                print(f"User hosp: {user['hospital_list']}")
                                messages = f'Slot opened in {hospital["name"]} for dose {user["dose_number"]}. Book it ASAP.'
                                client = Client(account_sid, auth_token)
                                message = client.messages \
                                         .create(
                                         body=messages,
                                         from_='+14154814323',
                                         to=f'+917378846849')
                                print(message.status)
                                print(messages)
                                print(f"User hosp: {user['hospital_list']}")
                                print(f'Name: {hospital["name"]}')
                                user['hospital_list'].remove(hospital['name'])
                                print(user['hospital_list'])

                            elif user['dose_number'] == 2 and sessions['available_capacity_dose2'] > 0:
                                print(f'Here{user}')
                                messages = f'Slot opened in {hospital["name"]}. Book it ASAP.'
                                client = Client(account_sid, auth_token)

                                message = client.messages \
                                    .create(
                                    body=messages,
                                    from_=' +14154814323',
                                    to=f'+91{user["phone_number"]}')
                                # print(message.status)
                                print(messages)
                                user['hospital_list'].remove(hospital['name'])
                            else:
                                print("No Slots Opened")

                            print(f"Length: {len(user['hospital_list'])} ")
                            print(f'Userlen: {len(user_data)}')
                            if len(user['hospital_list']) == 0:
                                for del_user in user_data:
                                    if del_user.phone_number == user['phone_number']:
                                        db.session.delete(del_user)
                                        db.session.commit()

