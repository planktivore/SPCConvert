import pandas as pd
import sys
import math
import pystache
import numpy as np
import os

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

def update_preds(html_dir, json_path):

	context = {}

	template = ""
	with open(html_path,"r") as fconv:
		template = fconv.read()

	context['num_pred_0'], context['num_pred_1'] = count_pred(json_path) 

	# render the html page and save to disk
	page = pystache.render(template,context)

	with open(html_path,"w") as fconv:
		fconv.write(page)


if __name__ == '__main__':

	if len(sys.argv) <= 2:
		print ("Please input the path to the current html, and the predictions json, aborting.")
	elif len(sys.argv) <= 3:
		html_path = sys.argv[1]
		json_path = sys.argv[2]
		update_preds(html_path, json_path)
	else:
		print("too many arguments, aborting")