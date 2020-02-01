#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import json
import urllib
import requests
from datetime import datetime, timedelta
import hashlib
import hmac
import numpy as np
#GPIO for LED
import RPi.GPIO as GPIO
import myconfig
#I2C bus
import board
import busio
#load libraries for ADC
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

"""
This script using the PTV API and the DarkSky API to create a display for the
inkphat display that shows the next 3 trains and the forecast weather. Helps
you to decide when to leave for the trian (and if it's late) and if you'll need
an umbrella or hat! Also now includes a soil moisture reading from an ADC :)

Inkyphat display: https://shop.pimoroni.com/products/inky-phat?variant=12549254217811
PTV API: https://www.ptv.vic.gov.au/footer/data-and-reporting/datasets/ptv-timetable-api/
Darksky API: https://darksky.net/dev

To run, config the myconfig.example file and rename myconfig.py 
You'll also need to register for PTV and Darksky API keys

You can use crontab to run the script every 10minutes or as needed :)
"""

def get_moisture():
	#initalise I2C bus
	i2c = busio.I2C(board.SCL, board.SDA)
	#initalise ADC
	ads = ADS.ADS1115(i2c)
	
	#read channel 0
	chan = AnalogIn(ads, ADS.P0)
	#get value as a precentage
	max_val = 21827
	val_perc = round(chan.value/max_val*100)
	
	return val_perc

#LED flash loop
def flash_loop(flash_hz, total_time):
		if flash_hz == 0:
			#error mode: always on
		    GPIO.output(18,GPIO.HIGH)
		else:
			#warning mode
		    flash_time = 1/flash_hz
		    flash_loop_range = int(flash_hz*total_time/2)
		    for i in range(flash_loop_range):
		            GPIO.output(18,GPIO.HIGH)
		            time.sleep(flash_time)
		            GPIO.output(18,GPIO.LOW)
		            time.sleep(flash_time)

def get_weather():
	"""
	Dark Sky API Request
	"""
	#config
	baseuri   = 'https://api.darksky.net/forecast/'
	#
	uri = baseuri + myconfig.darksky_apiid + '/' + str(myconfig.lat_coord) \
					+ ',' + str(myconfig.lon_coord) \
					+ '?exclude=currently,minutely,daily&units=si'

	res = requests.get(uri)
	if(res.status_code==200):
		json_data = json.loads(res.text)
		return json_data

	return {}

def get_ptv():
	"""
	PTV API request
	"""
	#config
	ptvbase     = "http://timetableapi.ptv.vic.gov.au"
	preamble    = "/v3/"
	apibase     = 'departures/route_type/0/stop/'
	api_args    = {'max_results':4, 'look_backwards':False, 'direction_id':1}
	
	#build url with signatures
	api_args['devid'] = myconfig.ptv_devid
	call = preamble + apibase + myconfig.stop + "?" + urllib.parse.urlencode(api_args)
	sig  = hmac.new(str.encode(myconfig.ptv_key), str.encode(call), hashlib.sha1).hexdigest().upper()
	url  = ptvbase + call + "&signature=" + sig
	#request
	res = requests.get(url)
	#check output
	if(res.status_code==200):
		json_data = json.loads(res.text)
		json_data = json_data['departures']
		return json_data
	return {}

#########################################################
# Build datasets from API calls
#########################################################

#get mosisture value
try:
	moisture_value = get_moisture()
except:
	moisture_value = -99

#process weather
forecast_steps = [1,3,6]
weather = get_weather()
time_list = []
temp_list = []
cloud_list = []
rain_list = []

for i in forecast_steps:
	#extract weather step
	weather_step = weather['hourly']['data'][i]
	#convert unix time to dt
	unix_dt = weather_step["time"] 
	dt      = datetime.fromtimestamp(unix_dt)
	#append into lists
	time_list.append(dt.strftime('%H'))
	temp_list.append(str(int(weather_step["temperature"])))
	if "cloudCover" in weather_step:
		cloud = str(int(weather_step["cloudCover"]*100))
		if cloud == '0':
			cloud = ''
	else:
		cloud = ''
	cloud_list.append(cloud)
	if "precipIntensity" in weather_step:
		rain = str(np.round(weather_step["precipIntensity"], decimals=1))
		if rain == '0.0':
			rain = ''
	else:
		rain = ''
	rain_list.append(rain)
wx_labels = ['LTS',u' °C',' %','mm']


#process ptv
train = get_ptv()
departures_list = []
for i in range(len(train)):
    depart_dts  = train[i]['estimated_departure_utc']
    depart_type = 'E'
    if depart_dts is None:
        depart_dts  = train[i]['scheduled_departure_utc']
        depart_type = 'S'
    depart_dt = datetime.strptime(depart_dts, '%Y-%m-%dT%H:%M:%SZ')
    offset    = datetime.now() - datetime.utcnow()
    local_dt  = depart_dt + offset
    departures_list.append(depart_type + ': ' + local_dt.strftime('%H:%M'))

#########################################################
# Build inkyphat display
#########################################################

import inkyphat
from PIL import Image, ImageFont

inkyphat.set_colour('yellow')
inkyphat.set_border(inkyphat.BLACK)
inkyphat.set_rotation(180)
inkyphat.set_image(Image.open("/home/pi/inky_display/clouds.png"))
inkyphat.line((7, 27, 203, 27)) #horizontal top line
inkyphat.line((133, 29, 133, 96)) #vertical top line


data_font  = ImageFont.truetype(inkyphat.fonts.FredokaOne, 16)
label_font = ImageFont.truetype(inkyphat.fonts.FredokaOne, 14)
moisture_font = ImageFont.truetype(inkyphat.fonts.FredokaOne, 12)
#set data plotting config
wx_col_loc    = [10,40,70,100]
ptv_col_loc   = 140
data_row_loc  = [30,50,70]
label_row_loc = 10
#plot data
for i, row_loc in enumerate(data_row_loc):
	inkyphat.text((wx_col_loc[0], row_loc), time_list[i],  inkyphat.BLACK, font=data_font)
	inkyphat.text((wx_col_loc[1], row_loc), temp_list[i],  inkyphat.BLACK, font=data_font)
	inkyphat.text((wx_col_loc[2], row_loc), cloud_list[i], inkyphat.BLACK, font=data_font)
	inkyphat.text((wx_col_loc[3], row_loc), rain_list[i],  inkyphat.BLACK, font=data_font)
for i, row_loc in enumerate(data_row_loc):
	try:
		inkyphat.text((ptv_col_loc, row_loc), departures_list[i],  inkyphat.BLACK, font=data_font)
	except:
		print('failure on inkphat text ptv')
		continue
#plot labels
for i, col_loc in enumerate(wx_col_loc):
	inkyphat.text((col_loc, label_row_loc), wx_labels[i],  inkyphat.BLACK, font=label_font)
inkyphat.text((ptv_col_loc, label_row_loc), '   Train',  inkyphat.BLACK, font=label_font)

#moisture value
inkyphat.text((90, 90), 'Soil Moisture: ' + str(moisture_value) + '%',  inkyphat.BLACK, font=moisture_font)

# And show it!
inkyphat.show()

#####################################
#moisture alarm LED
#####################################

#LED config
#gentle warning
water_now_val = 50
water_now_flash_hz = 2
#emergency warning
water_emergency_val = 35
water_emergency_flash_hz = 8
#total time
total_time_sec = 540
#initalise LED
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(18,GPIO.OUT)

#call loop if needed
if moisture_value == -99:
	flash_loop(0, total_time_sec)
if moisture_value < water_emergency_val:
	flash_loop(water_emergency_flash_hz, total_time_sec)
elif moisture_value < water_now_val:
	flash_loop(water_now_flash_hz, total_time_sec)

