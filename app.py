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
        if (int(time()) - last_update > 15) : # Update very 15 minutes
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

def getData(url, query):
    data = json.loads(requests.request("GET", url, headers=headers, params=query).text)["response"]
    return data

def insertData(collection, data, update_query):
    # Save fixtures in local database
    insert = collection.insert_many(data) 
    # Insert last timestamp update for this league
    log = updates_col.insert_one(update_query) 
    return (insert, log)

def updateData(collection, data, find_query, update_query, printMessage):
    for elt in data:
        to_update = collection.find_one(find_query) 
        update = odds_col.update_one(to_update, elt)
        log = collection.update_one(update_query)
        printResult(update, log, printMessage)

def printResult(insert, log, message):
    # Insertion feedback
    if insert : print(colored(f'{message} successed', 'green')) 
    else : print(colored(f'Error : {message} failed', 'red')) 
    # Update feedback
    if log : print(colored('Timestamp successfully updated', 'green'))
    else : print(colored('Error : Timestamp update failed', 'red'))

############################### Odds ###############################
def getOddsForFixture(fixture):
    url = "https://api-football-v1.p.rapidapi.com/v3/odds"
    querystring = {"fixture":fixture}
    return getData(url, querystring)

# Insert the odds in the local database for one fixture
def insertOdds(fixture):
    insert_status, log_status =insertData(odds_col, getOddsForFixture(fixture), {"odds" : fixture, "timestamp" : int(time())})
    printResult(insert_status, log_status, f"Fixture n°{fixture} - Odds insertion")
    return True

# Update all the odds for one fixture in the local database
def updateOdds (fixture, last_update):
    update_query = {"odds" : fixture, "timestamp" : last_update}, {"$set" : { "odds" : fixture, "timestamp" : int(time()) }}
    updateData(odds_col, getOddsForFixture(fixture), {"fixture.id" : fixture}, update_query, f'Fixture n°{fixture} - Odds update')
    return True

############################### Fixtures ###############################
# Get all the fixtures for one league in the API database football-api
def getFixtureFromLeague(league):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    querystring = {"league":league,"season":2021}
    return getData(url, querystring)

# Insert the fixtures in the local database for one league
def insertFixture(league):
    insert_status, log_status = insertData(fixtures_col, getFixtureFromLeague(league), {"league" : league, "timestamp" : int(time())})
    printResult(insert_status, log_status, f'League n°{league} - Fixtures insertion')

# Update all the fixtures for one league in the local database
def updateFixture (league, last_update):
    # Get fixtures from API
    fixtures = getFixtureFromLeague(league) 
    for fixture in fixtures:
        # Find the fixture to update
        to_update = fixtures_col.find_one({"fixture.id" : fixture["fixture"]["id"]}) 
        # Update fixture with new informations
        update = fixtures_col.update_one(to_update, { "$set" : fixture }) 
        log = updates_col.update_one({"league" : league, "timestamp" : last_update}, {"$set" : { "league" : league, "timestamp" : int(time()) }})
        printResult(update, log, f'Fixture n°{fixture["fixture"]["id"]} - Fixture update')
    return True

if __name__ == "__main__":
    app.run('0.0.0.0', debug=True, port=5000)