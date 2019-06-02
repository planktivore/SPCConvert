import sys

from flask import Flask, render_template, request, redirect, Response
import random, json

import pandas as pd

app = Flask(__name__)

@app.route("/")
def home():
    return render_template('spcdata.html')

@app.route("/output")
def output():
    return "test!!"

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

	for i in range(len(prediction['machine_labels'])):
		url = prediction['machine_labels'].iloc[i]['image_id']
		prediction['machine_labels'].iloc[i]['gtruth'] = url_to_label[url]

	# write back to predictions.json
	prediction.to_json("predictions.json")

	return result

if __name__ == "__main__":
    app.run()