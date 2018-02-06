import os
import sys
import json


with open(os.path.join(sys.path[0],'config.json')) as data_file:    
    data = json.load(data_file)

print(data)
