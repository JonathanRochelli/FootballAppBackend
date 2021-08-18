from flask import Flask, request
from pymongo import MongoClient
from bson import json_util
from flask_cors import CORS
import json

with open('conf/conf.json') as f:
    conf = json.load(f)

# MongoDb configuration
client = MongoClient("{}:{}".format(conf["host"], conf["port"]))
db=client[conf["db"]]
countries = db["Countries"] # Countries collection
leagues = db["Leagues"] # Leagues collection
fixtures = db["Fixtures"] # Fixtures collection

app = Flask(__name__)
CORS(app)

# Route to collect the countries
@app.route("/countries")
def getCountries():
    response = app.response_class(
        response=json_util.dumps(list(countries.find())[0]),
        status=200,
        mimetype='application/json'
    )
    return response

# Route to collect the leagues filtered by country
@app.route("/leagues")
def getLeagues():
    country = request.args.get('country')
    response = app.response_class(
        response=json_util.dumps(leagues.find({"country.name" : country})),
        status=200,
        mimetype='application/json'
    )
    return response

# Route to collect all the leagues 
@app.route("/leagues/all")
def getAllLeagues():
    data = leagues.find({ "$or" : [{"country.name" : "France"}, {"country.name" : "Germany"}, {"country.name" : "Italy"}, {"country.name" : "Portugal"}, {"country.name" : "Spain"}, {"country.name" : "England"}, {"country.name" : "Belgium"}, {"country.name" : "World"}] })
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
@app.route("/fixtures")
def getFixtures():
    league = request.args.get('league')
    response = app.response_class(
        response=json_util.dumps(fixtures.find({"league.name" : league})),
        status=200,
        mimetype='application/json'
    )
    return response