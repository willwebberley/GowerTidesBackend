from flask import Flask, url_for, render_template, request, session, escape, redirect
import json, urllib2, sqlite3, os, time

app = Flask(__name__)
API_KEY = os.environ.get('WEATHER_API_KEY')

# Open connection to database
def connectDB():
    con = sqlite3.connect("tides.db")
    c = con.cursor()
    return (con, c)
    
# Initialise database by creating the necessary table, if it does not exist
def initDB():
    con = sqlite3.connect("tides.db")
    c = con.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tides (
                timestamp REAL,
                year REAL,
                month REAL,
                day REAL,
                max_temp_c REAL,
                max_temp_f REAL,
                min_temp_c REAL,
                min_temp_f REAL,
                wind_speed_miles REAL,
                wind_speed_km REAL,
                wind_direction TEXT,
                wind_angle REAL,
                icon_url TEXT,
                description TEXT,
                precipitation REAL)''')
    con.commit()

# Update the table with new weather data. If last update less than 30 mins ago, exit without making request to API
def updateDB(con, c):
    currentTime = time.time()
    row = c.execute("SELECT timestamp FROM tides").fetchone()
    if not row == None:
        lastUpdate = int(row[0])
        diff = currentTime - lastUpdate
        if diff < 1800:
            return
    # Last update more than 30 mins ago, so refresh weather:
    request = "http://api.worldweatheronline.com/free/v1/weather.ashx?q=llangennith&format=json&num_of_days=5&key="+API_KEY
    response = urllib2.urlopen(request).read()
    jDict = json.loads(response)
    c.execute("DELETE FROM tides")
    for weather in jDict['data']['weather']:
        date = weather['date'].split("-")
        c.execute("INSERT INTO tides VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                    int(currentTime), int(date[0]), int(date[1]), int(date[2]), int(weather['tempMaxC']),
                    int(weather['tempMaxF']), int(weather['tempMinC']), int(weather['tempMinF']),
                    int(weather['windspeedMiles']), int(weather['windspeedKmph']), 
                    weather['winddirection'], int(weather['winddirDegree']),
                    weather['weatherIconUrl'][0]['value'], weather['weatherDesc'][0]['value'],
                    weather['precipMM']))
    con.commit()

# Get dict of currently-stored weather
def getWeather(con, c):
    stuff = []
    result = c.execute("SELECT * FROM tides").fetchall()
    for row in result:
        weather = {}
        weather['weather'] = {}
        weather['weather']['timestamp'] = int(row[0])
        weather['weather']['year'] = int(row[1])
        weather['weather']['month'] = int(row[2])
        weather['weather']['day'] = int(row[3])
        weather['weather']['max_temp_c'] = int(row[4])
        weather['weather']['max_temp_f'] = int(row[5])
        weather['weather']['min_temp_c'] = int(row[6])
        weather['weather']['min_temp_f'] = int(row[7])
        weather['weather']['wind_speed_miles'] = int(row[8])
        weather['weather']['wind_speed_km'] = int(row[9])
        weather['weather']['wind_direction'] = row[10]
        weather['weather']['wind_degree'] = int(row[11])
        weather['weather']['icon_url'] = row[12].replace("\\","")
        weather['weather']['weather_description'] = row[13]
        weather['weather']['precipitation'] = row[14]
        stuff.append(weather)
    return stuff

# Return the currently stored weather. If this is 'stale', then update this from Weather API first/
@app.route('/fetch/')
def fetch():
    creds = connectDB()
    updateDB(creds[0], creds[1])
    weather = getWeather(creds[0], creds[1])
    return json.dumps(weather)

initDB()
# Main code
if __name__ == '__main__':
    app.debug = True # set to true and server will display any errors to the page
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
