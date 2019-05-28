import pandas as pd
import sys
import math
import pystache
import numpy as np
import os
import json

# Project Level Imports
from utils.db_utils import to_json_format

# Annotation
# getting predicted labels on the static page
def loadDB(db_path, json_path):

	# load in database file
	curr_db = ""
	with open(db_path, "r") as fconv:
		curr_db = fconv.read()

	# load prediction data
	prediction_df = pd.read_json(json_path)

	# convert curr_db into valid json string
	ind_opbrac = curr_db.find("(") + 1
	curr_db = curr_db[ind_opbrac:]

	ind_brac = curr_db.find(")")
	curr_db = curr_db[:ind_brac]

	ind_last_comma = len(curr_db) - 2
	curr_db = curr_db[:ind_last_comma-1] + curr_db[ind_last_comma:]

	#print(curr_db)
	# create a python list from the db values
	entries = json.loads(curr_db)

	# create a dict of all labels, and URLs
	url_to_label = {}
	for i in range(len(prediction_df['machine_labels'])):
		data = {}
		url = prediction_df['machine_labels'].iloc[i]['image_id']
		data['pred'] = prediction_df['machine_labels'].iloc[i]['pred']
		data['prob'] = prediction_df['machine_labels'].iloc[i]['prob']

		url_to_label[url] = data

	# update values in the list
	for entry in entries:
		filename = entry['url'][13:]
		filename = filename[:len(filename) - 5]
		filename = filename + ".tif"
		entry["pred"] = url_to_label[filename]['pred']
		entry["prob_non_proro"] = url_to_label[filename]['prob'][0]
		entry["prob_proro"] = url_to_label[filename]['prob'][1]

	# write a new db from the db template with the updated list
	db_str = json.dumps(entries)
	db_str = "roistore = TAFFY(" + db_str + ");"

	with open(db_path, "w") as fconv:
		fconv.write(db_str)

# Visualisation
# go through prediction data and count the classes
def count_pred(json_path):
	prediction_df = pd.read_json(json_path)
	num_pred_1 = 0
	num_pred_0 = 0

	for i in range(len(prediction_df['machine_labels'])):
		if prediction_df['machine_labels'].iloc[i]['pred'] == 1:
			num_pred_1 += 1
		else:
			num_pred_0 += 1

	return (num_pred_0, num_pred_1)

# re-render the html with the data
def update_preds(html_path, json_path):

	context = {}

	template = ""
	with open(html_path,"r") as fconv:
		template = fconv.read()

	context['num_pred_0'], context['num_pred_1'] = count_pred(json_path) 

	# render the html page and save to disk
	page = pystache.render(template,context)

	with open(html_path,"w") as fconv:
		fconv.write(page)

# Entry point
if __name__ == '__main__':

	if len(sys.argv) <= 3:
		print ("Please input the path to the current html, the predictions json, and path to the db, aborting.")
	elif len(sys.argv) <= 4:
		html_path = sys.argv[1]
		json_path = sys.argv[2]
		db_path = sys.argv[3]
		update_preds(html_path, json_path)
		loadDB(db_path, json_path)
	else:
		print("too many arguments, aborting")