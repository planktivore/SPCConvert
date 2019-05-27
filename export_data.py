"""Export database to csv file"""
# Standard dist imports
import os
import sys

# Third party imports

# Project level imports
from utils.db_utils import loadDB, to_spc_csv

# Module level constants

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print("Please input the path to the db, aborting.")
    elif len(sys.argv) <= 2:
        db_path = sys.argv[1]
        db = loadDB(db_path)
        html_dir = os.path.abspath(os.path.join(db_path, "../.."))
        csv_fname = os.path.join(html_dir, 'database.csv')
        to_spc_csv(db, csv_fname=csv_fname)
    else:
        print("too many arguments, aborting")