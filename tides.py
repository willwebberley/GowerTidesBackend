from flask import Flask, url_for, render_template, request, session, escape, redirect
import json, urllib2, sqlite3, os, time, datetime

app = Flask(__name__)
API_KEY = os.environ.get('WEATHER_API_KEY')
MSW_KEY = os.environ.get('MSW_API_KEY')

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
    c.execute('''CREATE TABLE IF NOT EXISTS surf (
                timestamp REAL,
                local_time REAL,
                faded_rating REAL,
                solid_rating REAL,
                min_surf REAL,
                abs_min_surf REAL,
                max_surf REAL,
                abs_max_surf REAL,
                swell_height REAL,
                swell_period REAL,
                swell_angle REAL,
                swell_direction TEXT,
                swell_chart_url TEXT,
                period_chart_url TEXT,
                wind_chart_url TEXT,
                pressure_chart_url TEXT,
                sst_chart_url TEXT)''')
    con.commit()

# Update the table with new weather data. If last update less than 30 mins ago, exit without making request to API
def updateWeatherDB(con, c):
    currentTime = time.time()
    row = c.execute("SELECT timestamp FROM tides ORDER BY timestamp DESC").fetchone()
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

# Update the table with new surf data. If last update less than 30 mins ago, exit without new request to MSW API.
def updateSurfDB(con, c):
    currentTime = time.time()
    row = c.execute("SELECT timestamp FROM surf ORDER BY timestamp DESC").fetchone()
    if not row == None:
        lastUpdate = int(row[0])
        diff = currentTime - lastUpdate
        if diff < 1800:
            return
    # Last update more than 30 mins ago, so refresh surf:
    request = "http://magicseaweed.com/api/"+MSW_KEY+"/forecast/?spot_id=32"
    response = urllib2.urlopen(request).read()
    jDict = json.loads(response)
    c.execute("DELETE FROM surf")
    for surf in jDict:
        try:
            c.execute("INSERT INTO surf VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(
            int(currentTime), int(surf['localTimestamp']), int(surf['fadedRating']), int(surf['solidRating']), float(surf['swell']['minBreakingHeight']), float(surf['swell']['absMinBreakingHeight']), float(surf['swell']['maxBreakingHeight']), float(surf['swell']['absMaxBreakingHeight']), float(surf['swell']['components']['combined']['height']), float(surf['swell']['components']['combined']['period']), float(surf['swell']['components']['combined']['direction']), surf['swell']['components']['combined']['compassDirection'], surf['charts']['swell'], surf['charts']['period'], surf['charts']['wind'], surf['charts']['pressure'], surf['charts']['sst']))
        except:
            print surf
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

# Get dict of currently-stored surf
def getSurf(con, c):
    stuff = []
    result = c.execute("SELECT * FROM surf").fetchall()
    for row in result:
        surf = {}
        surf['timestamp'] = int(row[0])
        surf['local_time'] = int(row[1])
        totalDateString = datetime.datetime.fromtimestamp(surf['local_time']).strftime('%Y-%m-%d %H:%M')
        dateString = totalDateString.split(" ")[0]
        timeString = totalDateString.split(" ")[1]
        surf['year'] = dateString.split("-")[0]
        surf['month'] = dateString.split("-")[1]
        surf['day'] = dateString.split("-")[2]      
        surf['hour'] = timeString.split(":")[0]
        surf['minute'] = timeString.split(":")[1] 
        surf['faded_rating'] = int(row[2])
        surf['solid_rating'] = int(row[3])
        surf['min_surf_height'] = float(row[4])
        surf['abs_min_surf_height'] = float(row[5])
        surf['max_surf_height'] = float(row[6])
        surf['abs_max_surf_height'] = float(row[7])
        surf['swell_height'] = float(row[8])
        surf['swell_period'] = float(row[9])
        surf['swell_angle'] = float(row[10])
        surf['swell_direction'] = row[11]
        surf['swell_chart'] = row[12].replace("\\","")
        surf['period_chart'] = row[13].replace("\\","")
        surf['wind_chart'] = row[14].replace("\\","")
        surf['pressure_chart'] = row[15].replace("\\","")
        surf['sst_chart'] = row[16].replace("\\","")
        stuff.append(surf)
    return stuff

# Return the currently stored weather. If this is 'stale', then it will update this from Weather API first.
@app.route('/fetch/')
def fetch():
    creds = connectDB()
    updateWeatherDB(creds[0], creds[1])
    weather = getWeather(creds[0], creds[1])
    return json.dumps(weather)

# Return the currently stored surf. If this is 'stale', then it will update this from surf API first.
@app.route('/fetch/surf/')
def fetch_surf():
    creds = connectDB()
    updateSurfDB(creds[0], creds[1])
    surf = getSurf(creds[0], creds[1])
    return json.dumps(surf)

# Return current data for both datasets. If either is 'stale', then the stale ones will be refreshed first.
@app.route('/fetch/both/')
def fetch_both():
    creds = connectDB()
    try:
        updateWeatherDB(creds[0], creds[1])
    except:
        print "Error updating weather"
    try:
        updateSurfDB(creds[0],creds[1])
    except:
        print "Error updating surf"
    return_stuff = {}
    return_stuff['weather'] = getWeather(creds[0], creds[1])
    return_stuff['surf'] = getSurf(creds[0], creds[1])
    return json.dumps(return_stuff)

initDB()
# Main code
if __name__ == '__main__':
    app.debug = True # set to true and server will display any errors to the page
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
