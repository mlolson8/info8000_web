# Flask note matthew Olson
# 3/26/24

from flask import Flask, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
import sqlite3
import bcrypt
import secrets
import string
import requests
import datetime
import os
cwd = os.getcwd() # Change working directory to this one

# Functions
def generate_api_key(length=32):
    # Characters to choose from for generating the API key
    characters = string.ascii_letters + string.digits

    # Generate a random API key
    api_key = ''.join(secrets.choice(characters) for _ in range(length))
    
    return api_key

def dbConnection():
    con = sqlite3.connect("data.db")
    return con

def getSqlEntry(filter_col,filter_data,result_col,table="users"):
    with dbConnection() as con:
        cur = con.execute(f"SELECT {result_col} FROM {table} WHERE {filter_col}=?",(filter_data,))
        hashed_password = cur.fetchone()
        if hashed_password:
            return(hashed_password[0])
        else:
            print("Data not found")
            return None

def HashPassword(password):
    salt = bcrypt.gensalt() 
    hashed_password = bcrypt.hashpw(password.encode('utf-8'),salt)
    return hashed_password

def get_location(lat,long):
    locate_url = f'https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={long}&format=json'
    res = requests.get(locate_url).json()
    data = [res['address']['state'], res['address']['country']]
    return data

def get_weather(lat,long):
    url = "https://api.open-meteo.com/v1/forecast"
    parameters = {
        "latitude":lat,
        "longitude":long,
        "current": "temperature_2m",
        "temperature_unit": "fahrenheit",
	    "timezone": "GMT"
    }
    res = requests.get(url, params=parameters)
    data = res.json()
    return data

def get_seniment(description):
    prompt = f"Is the sentiment of this description bad, neutral, or good? Return the result in a one-word answer: {description}"
    host = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    apikey = open("gemini_apikey.txt").read() # Need to direct to your own api key
    parameter = {"key":apikey}
    body = {"contents":[{"parts":[{"text":f'{prompt}'}]}]}
    res = requests.post(host,params=parameter,json=body)
    res.json()
    gem_res = res.json()['candidates'][0]['content']['parts'][0]['text']
    return gem_res

def get_valid_filepath(f):
    if f:
        file_name = secure_filename(f.filename)
        if os.path.exists(f'./uploads/{file_name}'):
            # If the file exists, generate a new name by appending a number to the filename
            name, extension = os.path.splitext(file_name)
            count = 1
            new_filename = f"{name}({count}){extension}"
            file_name = new_filename
            while os.path.exists(f'./uploads/{new_filename}'):
                count += 1
                new_filename = f"{name}({count}){extension}"
                file_name = new_filename
        file_path = f"./uploads/{file_name}"
    else:
        file_path = "No File Uploaded"
    return file_path

# FLASK APP
app = Flask(__name__,static_folder="static",template_folder="templates") #creates flask app/object
CORS(app)
auth = HTTPBasicAuth()




@auth.verify_password
def verify_password(username,password):
    if username == "admin" and password == 'admin':
        return username
    else:
        return False


@app.route('/',methods=['GET','POST']) 
def root():
    if request.method == "POST":
        if request.form.get('action') == 'register':
            register_username = request.form.get("register_username",default="")
            register_password = request.form.get("register_password",default="")
            with dbConnection() as con:
                cursor =  con.execute("SELECT Username FROM users WHERE Username=?",(register_username,))
                existing_user = cursor.fetchone()
                if existing_user: # Fails if the username exists already
                    error_message = "Username not available."
                    print(error_message)
                    return render_template("root.html",error_msg=error_message)
                else: # Hashes the password and assigns an API_key
                    hashed_reg_password = HashPassword(register_password)
                    random_api_key = generate_api_key()
                    # print("Random API Key:", random_api_key)
                    con.execute("INSERT INTO users(Username,Password,API_Key) values (?,?,?);",(register_username,hashed_reg_password,random_api_key))
                    success_message = "Username Registered!"
                    return render_template("root.html",success_msg=success_message) 
        elif request.form.get('action') == 'login':
            login_username = request.form.get("login_username",default="")
            login_password = request.form.get("login_password",default="")
            saved_hashed_password = getSqlEntry("Username",login_username,"Password")
            if saved_hashed_password != None:
                if bcrypt.checkpw(login_password.encode('utf-8'),saved_hashed_password):
                    return redirect(url_for("home",user=login_username))
                else:
                    not_found_message = "Password incorrect."
                    return render_template("root.html",not_found_message = not_found_message) 
            else:
                not_found_message = "Username not found."
                return render_template("root.html",not_found_message = not_found_message) 
    return render_template("root.html")






@app.route('/home/<user>', methods=["GET","POST"])
def home(user):
    user_api_key = getSqlEntry("Username",user,"API_Key")
    # if request.method == "POST":
    #     return redirect(url_for("report",user=user))
  
    return render_template("home.html",user_msg = user, api_key_msg = user_api_key)

@app.route('/report', methods=['POST'])
def report():
    # Gather all information to save in the database
    user = request.form.get("username")
    print(f"username:{user}")
    user_api_key = getSqlEntry("Username",user,"API_Key")
    user_id = getSqlEntry("Username",user,"ID")
    GPS = request.form.get("GPS",default="").split(",")
    lat = GPS[0].strip()
    long = GPS[1].strip()
    print(f"lat:{lat}, long:{long}")
    date_time = datetime.datetime.now(datetime.timezone.utc)
    print(date_time)
    temperature = get_weather(lat,long)['current']['temperature_2m']
    file_description = request.form.get("description",default="")
    loc = get_location(lat,long)
    state = loc[0]
    country = loc[1]
    IP_addr = request.form.get("visitor_ip",default="")
    sentiment = get_seniment(file_description)
    f = request.files.get("file1",default=None)
    print(f"File:{f}")
    file_path = get_valid_filepath(f)
    f.save(file_path) 
    print(f"File Path: {file_path}")
    # Save all the data to the databases
    with dbConnection() as con:
        con.execute("INSERT INTO report(User_ID,Username,DateTime,Latitude,Longitude,State,Country,Temperature,IP,Description,Sentiment,FilePath)\
                    values (?,?,?,?,?,?,?,?,?,?,?,?);",(user_id,user,date_time,lat,long,state,country,temperature,IP_addr,file_description,sentiment,file_path))
    # Get report ID
    report_id = getSqlEntry("DateTime",date_time,"Report_ID",table="report")
    return render_template("report.html", report_id_msg = report_id, user_id_msg = user_id, username_msg = user, date_time_msg = date_time,\
                            lat_msg = lat, long_msg = long, state_msg = state, country_msg = country, temp_msg = temperature, \
                                ip_addr_msg = IP_addr,desc_msg = file_description, sentiment_msg = sentiment, file_path_msg = file_path)


@app.route('/data', methods=['GET'])
def data():
    with dbConnection() as con:
        cur = con.execute("SELECT * FROM report")
        data = cur.fetchall()
    return render_template('data.html', data_msg = data)


if __name__=="__main__":
    app.run(debug=True,port=8080)