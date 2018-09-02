#!/usr/bin/env python

import obd_io
import serial
import platform
import obd_sensors
from datetime import datetime
import time
import getpass
import numpy as np
import csv
import sys
import getopt


from obd_utils import scanSerial

class OBD_Recorder():
    def __init__(self, output_filename, obd2_csv_path, sampling_interval, sensor_codes=None, sensor_names=None):
        self.port = None
        self.log_filename = output_filename
        self.sampling_interval = sampling_interval
        self.obd2_std_PIDs = np.genfromtxt(obd2_csv_path, names=True,delimiter=",",dtype=None)
        self.sensor_codes = sensor_codes if sensor_codes else self.get_all_sensor_codes()
        self.sensor_names = sensor_names if sensor_names else self.get_all_sensor_names()

        self.gear_ratios = [34/13, 39/21, 36/23, 27/20, 26/21, 25/22]

    def get_all_sensor_codes(self):
    	'''
    	Returns a list of all obd2 sensor codes in the format ["0100", "0101", ...]
    	'''
    	codes = []
    	for mode, pid in zip(self.obd2_std_PIDs["Mode_hex"], self.obd2_std_PIDs["PID_hex"]):
    		mode = "0" + str(mode)
    		pid = str(pid.decode("utf-8")) if len(str(pid.decode("utf-8"))) > 1 else "0" + str(pid.decode("utf-8"))
    		code = mode + pid
    		codes.append(code)
    	return codes

    def get_all_sensor_names(self):
    	'''
    	Returns a list of all obd2 sensor names
    	'''
    	return [name.decode("utf-8") for name in self.obd2_std_PIDs["Description"]]
     
    def connect(self):
        portnames = scanSerial()
        #portnames = ['COM10']
        print portnames
        for port in portnames:
            self.port = obd_io.OBDPort(port, None, 2, 2)
            if(self.port.State == 0):
                self.port.close()
                self.port = None
            else:
                break

        if(self.port):
            print "Connected to "+self.port.port.name
            
    def is_connected(self):
        return self.port
        
    def add_log_item(self, item):
        for index, e in enumerate(obd_sensors.SENSORS):
            if(item == e.shortname):
                self.sensorlist.append(index)
                print "Logging item: "+e.name
                break
            
            
    def record_data(self):
        if(self.port is None):
            return None
        
        print("Logging started")
        
        with open(self.log_filename, "w", 128, newline='') as log_file:
        	log_file_writer = csv.writer(log_file, delimiter=',')
        	colnames = ["Timestamp"] + self.sensor_names
        	log_file_writer.writerow(colnames)
        	interval_starttime = time.time()
        	while self.port:
        		curr_timestamp = datetime.now()
        		sensor_vals = [self.port.get_sensor_value(sensor_code) for sensor_code in self.sensor_codes]
        		log_file_writer.writerow([curr_timestamp] + sensor_vals)
        		time_elapsed = time.time() - interval_starttime
        		time.sleep(self.sampling_interval - time_elapsed)
        		interval_starttime = time.time()

            
    def calculate_gear(self, rpm, speed):
        if speed == "" or speed == 0:
            return 0
        if rpm == "" or rpm == 0:
            return 0

        rps = rpm/60
        mps = (speed*1.609*1000)/3600
        
        primary_gear = 85/46 #street triple
        final_drive  = 47/16
        
        tyre_circumference = 1.978 #meters

        current_gear_ratio = (rps*tyre_circumference)/(mps*primary_gear*final_drive)
        
        #print current_gear_ratio
        gear = min((abs(current_gear_ratio - i), i) for i in self.gear_ratios)[1] 
        return gear

def main(argv):
   sampling_interval = 1 # gets data every 1 second
   output_filename = '/collected_data/obd2_data_' + str(datetime.now()) + '.csv'
   obd2_pid_csv = "obd2_std_PIDs.csv" # csv with obd2 PIDs and names
   # below borrowed from https://www.tutorialspoint.com/python/python_command_line_arguments.htm
   try:
      opts, args = getopt.getopt(argv,"hi:o:s:",["obd2_pid_csv=","output_filename=", "sampling_interval="])
   except getopt.GetoptError:
      print 'obd_recorder.py -i <obd2_pid_csv> -o <output_filename> -s <sampling_interval>'
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print 'obd_recorder.py -i <obd2_pid_csv> -o <output_filename> -s <sampling_interval>'
         sys.exit()
      elif opt in ("-i", "--obd2_pid_csv"):
         obd2_pid_csv = arg
      elif opt in ("-o", "--output_filename"):
         output_filename = arg
      elif opt in ("-s", "--sampling_interval"):
      	 sampling_interval = float(arg)
   print("output filename:")
   print(output_filename)
   
   o = OBD_Recorder(output_filename, obd2_pid_csv, sampling_interval)
   o.connect()
   if not o.is_connected():
   	print "Not connected"
   o.record_data()

        
if __name__ == "__main__":
	main(sys.argv[1:])
