import sys

from flask import Flask, render_template, request, redirect, Response
import random, json

import pandas as pd

app = Flask(__name__)

# helper functions
def loadDB(db_path):
    """Loads db into list of entries

    Args:
        db_fname (str): Abs path to the db

    Returns:
        list: List of db values

    """
    curr_db = ""
    with open(db_path, "r") as fconv:
        curr_db = fconv.read()

    db_entries = to_json_format(curr_db)
    return db_entries


def to_json_format(str_db):
    """Convert str db into python list of db values (json format)"""
    import json
    ind_opbrac = str_db.find("(") + 1
    str_db = str_db[ind_opbrac:]

    ind_brac = str_db.find(")")

    str_db = str_db[:ind_brac]
    ind_last_comma = len(str_db) - 2
    str_db = str_db[:ind_last_comma - 1] + str_db[ind_last_comma:]
    return json.loads(str_db)

@app.route("/")
def home():
    return render_template('spcdata.html')

@app.route("/save_gtruth", methods = ['POST'])
def save():

	data = request.get_json(force=True)
	result = ''

	# load in predictions.json
	prediction = pd.read_json("predictions.json")

	# add gtruth values to predictions
	url_to_label = {}
	for image in data:
		name = image["url"]
		name = name[:(len(name) - 5)]
		name = name[13:]
		name = name + ".tif"
		gtruth = image["gtruth"]
		url_to_label[name] = gtruth

	# save the new predictions to the roistore
	# load in database file
	entries = loadDB("./static/js/database.js")

	# update values in the list
	for entry in entries:
		filename = entry['url'][13:]
		filename = filename[:len(filename) - 5]
		filename = filename + ".tif"
		entry["gtruth"] = url_to_label[filename]

	# write a new db from the db template with the updated list
	db_str = json.dumps(entries)
	db_str = "roistore = TAFFY(" + db_str + ");"

	with open("./static/js/database.js", "w") as fconv:
		fconv.write(db_str)

	return result

if __name__ == "__main__":

    app.run()