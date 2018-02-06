import os
import sys
import json

cfg = xmlsettings.XMLSettings(os.path.join(sys.path[0],'settings.xml'))

with open(os.path.join(sys.path[0],'config.json')) as data_file:    
    data = json.load(data_file)

