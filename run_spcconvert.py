import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import glob
import os
import sys
import time
import shutil
import spcconvert
import logging
from logging.handlers import RotatingFileHandler
from logging import handlers

# settings
max_look_back = 100*24*3600 # max time to look backwards for new data
spcconvert_dir = r'c:\Users\paul\Desktop\SPCConvert' # location of the SPCConvert code
input_data_dir = r'c:\Users\paul\Desktop\test_input'
proc_data_dir = r'c:\Users\paul\Desktop\proc_output'
raw_data_dir = r'c:\Users\paul\Desktop\raw_output' # where to output processed data
proc_dir_db = r'proc_dir.txt' # the name of the database for saving processed dirs
send_email = True


# append a line to the list of processed dirs
def update_proc_dir(proc_dir_path,data_dir_name,status):

    with open(proc_dir_path,"a+") as f:
        
        f.write(data_dir_name + "," + str(time.time()) + "," + status + "\n")
    

# test if a directory seems to have the right stuff in it
def data_dir_is_okay(lgr,dir_path):

    # check that it has at least one tar file
    tar_files = glob.glob(os.path.join(dir_path,"*.tar"))
    if len(tar_files) < 1:
        lgr.info(dir_path + " has no tar archives!")
        return False
    
    # check that it has a shrink.tar.bz2 file to indicate the end of recording 
    if not os.path.exists(os.path.join(dir_path,"shrink.tar.bz2")):
        lgr.info(dir_path + " has no shrink.tar.bz2!")
        return False
        
    # check that the log file has more than a few kb
    log_file = glob.glob(os.path.join(dir_path,"*.log"))
    if not os.path.getsize(log_file[0]) > 2000:
        lgr.info(dir_path + " has log file with less than 2 kB")
        return False
    
    # check that it has a config.xml file
    if not os.path.exists(os.path.join(dir_path,"config.xml")):
        lgr.info(dir_path + " has no config.xml")
        return False
    
    return True
    
# return the last modified time of all sub dirs and files
def log_file_modified_time(dir_path):

    log_file = glob.glob(os.path.join(dir_path,"*.log"))
    if len(log_file) == 1:
        return os.path.getmtime(log_file[0])
    else:
        return 0

def last_modified(dir_path):

    return max(os.path.getmtime(root) for root,_,_ in os.walk(dir_path))
    
def process_data_dir(lgr,dir_path,camera_mag):

    try:

        settings_path = os.path.join(spcconvert_dir,'settings_'+camera_mag+'.xml')
        proc_path = os.path.join(proc_data_dir,camera_mag)

        res = spcconvert.batch_process_directory(lgr,dir_path,[],cfg_path=settings_path,output_path=proc_path)
        
        return res

        
    except:
    
        return False
        
# Send a simple email with subject and message 
def send_email_notice(toaddr,fromaddr,subject,message,serv='smtp.ucsd.edu'): 
 
    if not send_email:
        return
 
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = subject
     
    body = message
    msg.attach(MIMEText(body, 'plain'))
     
    server = smtplib.SMTP(serv, 587)
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()

# Test sending an email
def test_send_email_notice():

    if send_email:
        send_email_notice('plroberts@ucsd.edu','plroberts@ucsd.edu','this is a test','test')
    else:
        print("Email not enabled, change settings")
        
# loop over the data dir and process new, complete directories
def run_spcconvert(lgr,camera_mag='0p5x'):

    # get the list of directories from the last max_look_back seconds
    dir_list = glob.glob(os.path.join(input_data_dir,camera_mag,"[0-9]"*10))
    
    current_time = time.time()
    
    for dl in dir_list:
    
        skip_dir = False
        
        lgr.info("Checking " + dl + "...")

    
        # check is dir has already been processed
        if os.path.exists(proc_dir_db) and dl in open(proc_dir_db).read():
            lgr.info(dl + " has already been processed, skipping.")
            continue
    
        # Check time
        dir_time = log_file_modified_time(dl)
        if abs(dir_time - current_time) < max_look_back:
        
            # check for completion (dir not changing for more than a few seconds
            for ind in range(0,3):
                dir_time = log_file_modified_time(dl)
                if dir_time > current_time:
                    # files are still being saved so skip
                    skip_dir = True
                    break
                time.sleep(1) # sleep one second
                
            if skip_dir:
                lgr.info(dl + " is still being recorded, skipping.")
                continue
            
            # check for valid dir
            if data_dir_is_okay(lgr,dl):
                lgr.info(dl + " running spcconvert...")
                if process_data_dir(lgr,dl,camera_mag):
                    update_proc_dir(proc_dir_db,dl,'okay')
                    raw_output_path = os.path.join(raw_data_dir,camera_mag)
                    if not os.path.exists(raw_output_path):
                        os.makedirs(raw_output_path)
                    shutil.move(dl,raw_output_path)
                else:
                    lgr.info(dl + " spcconvert failed with error.")
                    send_email_notice(
                        'plroberts@ucsd.edu',
                        'plroberts@ucsd.edu',
                        'Problem with SPC Data Proessing: ' + os.path.basename(dl),
                        'SPC Data Proessing failed for ' + dl
                        )
                    
            else:
                lgr.info(dl + " has directory validation error.")
                send_email_notice(
                    'plroberts@ucsd.edu',
                    'plroberts@ucsd.edu',
                    'Problem with SPC Data Dir: ' + os.path.basename(dl),
                    'Directory validation failed for ' + dl
                    )
        
        else:
        
            print(dl + " was recorded more than " + str(max_look_back) + " seconds ago.")
    
if __name__ == "__main__":

    # setup logging
    log = logging.getLogger('')
    log.setLevel(logging.DEBUG)
    format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(format)
    log.addHandler(ch)

    fh = handlers.RotatingFileHandler(os.path.join('logs',str(int(time.time()))) + '.log', maxBytes=(1048576*5),backupCount=7)
    fh.setFormatter(format)
    log.addHandler(fh)
    
    if len(sys.argv) > 1:
        run_spcconvert(log,camera_mag=sys.argv[1])
    else:
        run_spcconvert(log)