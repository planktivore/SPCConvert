""" """
# Standard dist imports

# Third party imports

# Project level imports

# Module level constants

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
    st_db = str_db[:ind_last_comma - 1] + str_db[ind_last_comma:]
    return json.loads(str_db)

def to_spc_csv(db, csv_fname='database.csv'):
    """Exports database file to csv

    Args:
    	db (list): List of db values

    Returns:
    	None
    """
    import pandas as pd

    # export database as csv
    df = pd.DataFrame(db[0], index=[0])
    for d_ in db[1:]:
        df = df.append(d_, ignore_index=True)
    df.to_csv(csv_fname, index=False)
