import sys

from flask import Flask, render_template, request, redirect, Response
import random, json

import pandas as pd

app = Flask(__name__)

@app.route("/")
def home():
    return render_template('spcdata.html')

@app.route("/save_gtruth", methods = ['POST'])
def save():

	data = request.get_json(force=True)
	print(data[0])
	result = ''

	# write a new db from the db template with the updated list
	db_str = json.dumps(data)
	db_str = "roistore = TAFFY(" + db_str + ");"

	with open("./static/js/database.js", "w") as fconv:
		fconv.write(db_str)

	return result

if __name__ == "__main__":

    app.run()