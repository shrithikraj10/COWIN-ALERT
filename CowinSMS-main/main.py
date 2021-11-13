from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from typing import Callable
import requests
import datetime

header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 '
                  'Safari/537.36'
}

app = Flask(__name__)
Bootstrap(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cowinSMS.db'
hosp_list = []
checked_list = []
district_id_db = []
dose_number = []


class MySQLAlchemy(SQLAlchemy):
    Column: Callable
    Integer: Callable
    String: Callable


db = MySQLAlchemy(app)


class CowinSMS(db.Model):
    phone_number = db.Column(db.Integer, nullable=False, primary_key=True)
    hosp_list = db.Column(db.String(1000), unique=True, nullable=False)
    date = db.Column(db.String(20), nullable=False)
    district_id = db.Column(db.Integer, nullable=False)
    dose_number = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '<User%r>' % self.id


db.create_all()


@app.route("/")
def home_page():
    url_state_dict = "https://cdn-api.co-vin.in/api/v2/admin/location/states"
    response = requests.get(url_state_dict, headers=header)
    response.raise_for_status()
    data = response.json()['states']
    return render_template('index.html', state_list=data)


@app.route("/district", methods=['POST'])
def district_select():
    state_name = request.form['state_name'].lower()
    url_state_dict = "https://cdn-api.co-vin.in/api/v2/admin/location/states"
    response = requests.get(url_state_dict, headers=header)
    response.raise_for_status()
    data = response.json()['states']

    state_id = [state['state_id'] for state in data if state['state_name'].lower() == state_name][0]

    URL_DISTRICT_DICT = f"https://cdn-api.co-vin.in/api/v2/admin/location/districts/{state_id}"

    response_district_dict = requests.get(URL_DISTRICT_DICT, headers=header)
    district_dict = response_district_dict.json()['districts']

    return render_template('district.html', state_districts=district_dict, state_name=state_name.title())


@app.route('/dose', methods=['POST'])
def dose_page():
    district_id = request.form['district']
    district_id_db.append(district_id)
    under_44 = request.form.get('under_44')
    dose_number.append(request.form['dose'])

    URL_APPOINTMENT = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/" \
                      f"calendarByDistrict?district_id={district_id}&" \
                      f"date={datetime.datetime.today().strftime('%d-%m-%Y')}"

    response_appointment = requests.get(URL_APPOINTMENT, headers=header)
    slots = response_appointment.json()['centers']

    for hosp in slots:
        for session in hosp["sessions"]:
            if under_44 == 'on' and session['min_age_limit'] < 44:
                hosp_list.append(hosp["name"])
                print(session)
                print(f"Age lim: {session['min_age_limit']}")
                break
            elif under_44 is None and session['min_age_limit'] == 45:
                hosp_list.append(hosp["name"])
                break

    print(f'Hospitals: {hosp_list}')
    if len(hosp_list) == 0:
        return render_template('failure.html')
    return render_template('dose.html', hosp_list=hosp_list, length=len(hosp_list))


@app.route('/hospitals', methods=['post'])
def hospital_select():
    checked_dict = {}
    for _ in range(0, len(hosp_list)-1):
        if request.form.get(f'index{_}') == 'on':
            checked_dict[f'{hosp_list[_]}'] = request.form.get(f'index{_}')
            checked_list.append(hosp_list[_])

    return render_template("hospitals.html", check_list=checked_list)


@app.route('/sms', methods=['POST'])
def sms_page():
    date = request.form['day']
    date = date.split('-')
    date.reverse()
    date_str = ''
    for day in date:
        date_str += f'{day}-'
    day_of_vaccination = date_str[:-1]
    phone_number = request.form['phone_num']
    new_register = CowinSMS(phone_number=phone_number,
                            hosp_list=','.join(str(e) for e in checked_list),
                            date=day_of_vaccination,
                            district_id=district_id_db[0],
                            dose_number=dose_number[0])
    db.session.add(new_register)
    db.session.commit()
    return render_template('sms.html')


if __name__ == '__main__':
    app.run(debug=True)
