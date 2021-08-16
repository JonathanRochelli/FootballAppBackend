# Football App Backend

## Content

This repository contains a Python server to display the data in MongoDB database. The data saved in the database was collected by this [repository](https://github.com/JonathanRochelli/FootballAppScraper). This repository allows us to run a Flask appplication

## Routes

- /countries : Collect all the countries
- /leagues : Collect all the leagues
- /fixtures : Collect all the fixtures

## How to start?

1. Install dependencies 

```
pip install -r requirements.txt
```

2. Set up the MongoDB database

You can follow the steps available on this [website](https://docs.mongodb.com/manual/installation/)

3. Run the application

**Bash**

```
$ export FLASK_APP=hello
$ flask run
 * Running on http://127.0.0.1:5000/
```

**CMD**

```
> set FLASK_APP=hello
> flask run
 * Running on http://127.0.0.1:5000/
```

**Powershell**

```
> $env:FLASK_APP = "hello"
> flask run
 * Running on http://127.0.0.1:5000/
```
