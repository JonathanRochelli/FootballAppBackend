from flask import Flask
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
        response=json_util.dumps(countries.find()),
        status=200,
        mimetype='application/json'
    )
    return response

# Route to collect the leagues
@app.route("/leagues")
def getLeagues():
    response = app.response_class(
        response=json_util.dumps(leagues.find()),
        status=200,
        mimetype='application/json'
    )
    return response

# Route to collect the fixtures
@app.route("/fixtures")
def getFixtures():
    response = app.response_class(
        response=json_util.dumps(fixtures.find()),
        status=200,
        mimetype='application/json'
    )
    return response