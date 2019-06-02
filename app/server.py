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

    # take ground truth values

    return result

if __name__ == "__main__":
    app.run()