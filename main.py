from flask import Flask, jsonify
from pymongo import MongoClient
from pprint import pprint
from time import strftime
from bson import json_util
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

@app.route("/countries")
def getCountries():
    response = app.response_class(
        response=json_util.dumps(countries.find()),
        status=200,
        mimetype='application/json'
    )
    return response