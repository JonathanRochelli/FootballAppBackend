from time import time
from flask import Flask, request
from pymongo import MongoClient
from bson import json_util
from flask_cors import CORS
import json
import os
import pendulum
import requests
from termcolor import colored
from datetime import datetime

with open('conf/conf.json') as f:
    conf = json.load(f)

# MongoDb configuration
client = MongoClient("{}:{}".format("localhost", "27017"))
db=client["football-app-db"]
countries_col = db["Countries"] # Countries collection
leagues_col = db["Leagues"] # Leagues collection
fixtures_col = db["Fixtures"] # Fixtures collection
updates_col = db["Updates"] # Updates collection

with open('conf/key.json') as f:
    key = json.load(f)

# Rapid API account configuration
headers = {
    'x-rapidapi-key': key["key"],
    'x-rapidapi-host': "api-football-v1.p.rapidapi.com"
}

app = Flask(__name__)
CORS(app)

# Route to collect the countries
@app.route("/countries")
def getCountries():
    response = app.response_class(
        response=json_util.dumps(list(countries_col.find({}))), # Return all the countries
        status=200,
        mimetype='application/json'
    )
    return response

# Route to collect the leagues filtered by country
@app.route("/fixtures/<league>")
def getLeagues(league):
    fixtures = [] # Initialize response
    # League fixtures was nerver saved
    if (updates_col.count_documents({"league" : league}) == 0):
        fixtures = getFixtureFromLeague(league) # Get fixture from API
        result  = fixtures_col.insert_many(fixtures) # Save fixtures in local database
        if result : print(colored(f'League n°{league} - Fixtures successfully inserted', 'green')) # Success message
        else : print(colored(f'Error : League n°{league} - Fixtures insertion failed', 'red')) # Fail message
        result = updates_col.insert_one({"league" : league, "timestamp" : int(time())}) # Insert last timestamp update for this league
        if result : print(colored('Timestamp successfully updated', 'green'))
        else : print(colored('Error : Timestamp update failed', 'red'))
    else :
        last_update = updates_col.find_one({"league" : league})["timestamp"] # Get last update
        if (int(time()) - last_update > 15*60): # Update from API every 15 minutes
            fixtures = getFixtureFromLeague(league) # Get fixtures from API
            for fixture in fixtures:
                to_update = fixtures_col.find_one({"fixture.id" : fixture["fixture"]["id"]}) # Find last fixture
                result = fixtures_col.update_one(to_update, { "$set" : fixture }) # Update last fixture with new informations
                if result : print(colored(f'Fixture n°{fixture["fixture"]["id"]} - Fixtures successfully updated', 'green')) # Success message
                else : print(colored(f'Error : Fixture n°{fixture["fixture"]["id"]} - Fixtures update failed', 'red')) # Fail message
                # Update update timestamp
                result = updates_col.update_one({"league" : league, "timestamp" : last_update}, {"$set" : { "league" : league, "timestamp" : int(time()) }})
                if result : print(colored('Timestamp successfully updated', 'green')) #Success message
                else : print(colored('Error : Timestamp update failed', 'red')) # Fail message
        else :
            fixtures = list(fixtures_col.find({"league.id" : int(league)})) # Return fixtures saved in local database
    
    response = app.response_class(
        response=json_util.dumps(fixtures),
        status=200,
        mimetype='application/json'
    )
    return response

# Route to collect all the leagues 
@app.route("/leagues")
def getAllLeagues():
    data = leagues_col.find({}) # Get all leagues
    # Format the message
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
        response=response,
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
        response=json_util.dumps(fixtures_col.find({ "fixture.timestamp" : {"$gte" : next_sunday}})), # Return all the fixture after the next sunday
        status=200,
        mimetype='application/json'
    )
    return response

def getFixtureFromLeague(league):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    querystring = {"league":league,"season":2021}
    fixtures = json.loads(requests.request("GET", url, headers=headers, params=querystring).text)["response"]
    return fixtures

if __name__ == "__main__":
    app.run('0.0.0.0', debug=True, port=5000)