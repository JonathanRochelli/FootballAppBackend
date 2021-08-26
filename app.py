from flask import Flask, request
from pymongo import MongoClient
from bson import json_util
from flask_cors import CORS
import json
import os
import pendulum

with open('conf/conf.json') as f:
    conf = json.load(f)

# MongoDb configuration
client = MongoClient("{}:{}".format(os.environ["host"], os.environ["port"]))
db=client[os.environ["db"]]
countries_col = db["Countries"] # Countries collection
leagues_col = db["Leagues"] # Leagues collection
fixtures_col = db["Fixtures"] # Fixtures collection

app = Flask(__name__)
CORS(app)

# Route to collect the countries
@app.route("/countries")
def getCountries():
    response = app.response_class(
        response=json_util.dumps(list(countries_col.find({}))),
        status=200,
        mimetype='application/json'
    )
    return response

# Route to collect the leagues filtered by country
@app.route("/leagues")
def getLeagues():
    country = request.args.get('country')
    response = app.response_class(
        response=json_util.dumps(leagues_col.find({"country.name" : country})),
        status=200,
        mimetype='application/json'
    )
    return response

# Route to collect all the leagues 
@app.route("/leagues/all")
def getAllLeagues():
    data = leagues_col.find({})
    response = {
        "France" : [],
        "Italy" : [],
        "Portugal" : [],
        "Germany" : [],
        "Belgium" : [],
        "England" : [],
        "World" : [],
        "Spain" : []
    }
    for league in data:
        response[league["country"]["name"]].append(league["league"])
    response = app.response_class(
        response=json.dumps(response),
        status=200,
        mimetype='application/json'
    )
    return response


# Route to collect the fixtures
@app.route("/fixtures/sunday")
def getFixtures():
    # Find next sunday
    next_sunday = pendulum.now().next(pendulum.SUNDAY).timestamp()
    response = app.response_class(
        response=json_util.dumps(fixtures_col.find({ "fixture.timestamp" : {"$gte" : next_sunday}})),
        status=200,
        mimetype='application/json'
    )
    return response

if __name__ == "__main__":
    app.run('0.0.0.0', debug=True, port=5000)