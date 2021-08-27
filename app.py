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
import threading

with open('conf/conf.json') as f:
    conf = json.load(f)

# MongoDb configuration
client = MongoClient("{}:{}".format("localhost", "27017"))
db=client["football-app-db"]
countries_col = db["Countries"] # Countries collection
leagues_col = db["Leagues"] # Leagues collection
fixtures_col = db["Fixtures"] # Fixtures collection
updates_col = db["Updates"] # Updates collection
odds_col = db["Odds"] # Updates collection

# Status API
fixture_status = {
    "finished" : ["FT", "AET", "PEN", "CANC", "ABD", "AWD", "WO"],
    "live" : ["1H", "HT", "2H", "ET", "P", "BT", "LIVE", "INT"],
    "not_started" : ["TBD", "NS", "PST", "SUSP"]
}

leagues_selected = [61, 71, 94, 140, 39, 78, 2, 3, 1, 4]

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
        response=json_util.dumps(response),
        status=200,
        mimetype='application/json'
    )
    return response

# Route to collect the fixtures
@app.route("/fixtures/sunday")
def getFixtures():
    # Find next sunday
    next_sunday = pendulum.now().next(pendulum.SUNDAY).timestamp()
    fixtures = fixtures_col.find({"$and": [{ "fixture.timestamp" : {"$gte" : next_sunday}}, {"league.id" : { "$in" : leagues_selected}}]})
    response = app.response_class(
        response=json_util.dumps(fixtures), # Return all the fixture after the next sunday
        status=200,
        mimetype='application/json'
    )
    return response

# Route to collect the fixtures filtered by league
@app.route("/fixtures/<league>/<status>")
def getFixturesByLeague(league, status):
    # League fixtures was nerver saved
    if (updates_col.count_documents({"league" : league}) == 0):
        insertFixture(league)
    else :
        last_update = updates_col.find_one({"league" : league})["timestamp"] # Get last update
        if (int(time()) - last_update > 15*60) : # Update very 15 minutes
            updateFixture(league, last_update)

    fixtures = list(fixtures_col.find({"$and" : [{"league.id" : int(league)}, {"fixture.status.short" : { "$in" : fixture_status[status] }}]})) # Return fixtures saved in local database
    # Sort by timestamp
    fixtures.sort(key=lambda f: f["fixture"]["timestamp"])
    response = app.response_class(
        response=json_util.dumps(fixtures),
        status=200,
        mimetype='application/json'
    )
    return response

# Route to collect the fixtures filtered by league
@app.route("/fixtures/<fixture>/odds")
def getOdds(fixture):
    # League fixtures was nerver saved
    if (updates_col.count_documents({"odds" : fixture}) == 0):
        insertOdds(fixture)
    else :
        last_update = updates_col.find_one({"odds" : fixture})["timestamp"] # Get last update
        if (int(time()) - last_update > 60*60) : # Update very hours
            updateOdds(fixture, last_update)

    odds = list(odds_col.find({"fixture.id" : int(fixture)})) # Return odds saved in local database
    response = app.response_class(
        response=json_util.dumps(odds),
        status=200,
        mimetype='application/json'
    )
    return response

############################### Odds ###############################
def getOddsForFixture(fixture):
    url = "https://api-football-v1.p.rapidapi.com/v3/odds"
    querystring = {"fixture":fixture}
    odds = json.loads(requests.request("GET", url, headers=headers, params=querystring).text)["response"]
    return odds

# Insert the odds in the local database for one fixture
def insertOdds(fixture):
    # Get odds from API
    odds = getOddsForFixture(fixture) 
    # Save fixtures in local database
    result  = odds_col.insert_many(odds) 
    # Success message
    if result : print(colored(f'Fixture n°{fixture} - Odds successfully inserted', 'green')) 
    # Fail message
    else : print(colored(f'Error : Fixture n°{fixture} - Odds insertion failed', 'red')) 
    # Insert last timestamp update for this league
    result = updates_col.insert_one({"odds" : fixture, "timestamp" : int(time())}) 
    if result : print(colored('Timestamp successfully updated', 'green'))
    else : print(colored('Error : Timestamp update failed', 'red'))
    return True

# Update all the odds for one fixture in the local database
def updateOdds (fixture, last_update):
     # Get odds from API
    odds = getOddsForFixture(fixture) 
    for odd in odds:
        # Find the odd to update
        to_update = odds_col.find_one({"fixture.id" : fixture}) 
        # Update odd with new informations
        result = odds_col.update_one(to_update, odd) 
        # Success message
        if result : print(colored(f'Fixture n°{fixture} - Odds successfully updated', 'green')) 
        # Fail message
        else : print(colored(f'Error : Fixture n°{fixture} - Odds update failed', 'red')) 
        # Update update timestamp
        result = updates_col.update_one({"odds" : fixture, "timestamp" : last_update}, {"$set" : { "odds" : fixture, "timestamp" : int(time()) }})
        if result : print(colored('Timestamp successfully updated', 'green'))
        else : print(colored('Error : Timestamp update failed', 'red'))
    return True

############################### Fixtures ###############################
# Get all the fixtures for one league in the API database football-api
def getFixtureFromLeague(league):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    querystring = {"league":league,"season":2021}
    fixtures = json.loads(requests.request("GET", url, headers=headers, params=querystring).text)["response"]
    return fixtures

# Update all the fixtures for one league in the local database
def updateFixture (league, last_update):
    # Get fixtures from API
    fixtures = getFixtureFromLeague(league) 
    for fixture in fixtures:
        # Find the fixture to update
        to_update = fixtures_col.find_one({"fixture.id" : fixture["fixture"]["id"]}) 
        # Update fixture with new informations
        result = fixtures_col.update_one(to_update, { "$set" : fixture }) 
        # Success message
        if result : print(colored(f'Fixture n°{fixture["fixture"]["id"]} - Fixtures successfully updated', 'green')) 
        # Fail message
        else : print(colored(f'Error : Fixture n°{fixture["fixture"]["id"]} - Fixtures update failed', 'red')) 
        # Update update timestamp
        result = updates_col.update_one({"league" : league, "timestamp" : last_update}, {"$set" : { "league" : league, "timestamp" : int(time()) }})
        if result : print(colored('Timestamp successfully updated', 'green'))
        else : print(colored('Error : Timestamp update failed', 'red'))
    return True

# Insert the fixtures in the local database for one league
def insertFixture(league):
    # Get fixture from API
    fixtures = getFixtureFromLeague(league) 
    # Save fixtures in local database
    result  = fixtures_col.insert_many(fixtures) 
    # Success message
    if result : print(colored(f'League n°{league} - Fixtures successfully inserted', 'green')) 
    # Fail message
    else : print(colored(f'Error : League n°{league} - Fixtures insertion failed', 'red')) 
    # Insert last timestamp update for this league
    result = updates_col.insert_one({"league" : league, "timestamp" : int(time())}) 
    if result : print(colored('Timestamp successfully updated', 'green'))
    else : print(colored('Error : Timestamp update failed', 'red'))
    return True

if __name__ == "__main__":
    app.run('0.0.0.0', debug=True, port=5000)