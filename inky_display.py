#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import uuid
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
#temp sensor
import bme680

"""
This script using the PTV API and the DarkSky API to create a display for the
inkphat display that shows the next 3 trains and the forecast weather. Helps
you to decide when to leave for the trian (and if it's late) and if you'll need
an umbrella or hat!

Inkyphat display: https://shop.pimoroni.com/products/inky-phat?variant=12549254217811
PTV API: https://www.ptv.vic.gov.au/footer/data-and-reporting/datasets/ptv-timetable-api/
Darksky API: https://darksky.net/dev

To run, config the myconfig.example file and rename myconfig.py 
You'll also need to register for PTV and Darksky API keys

You can use crontab to run the script every 10minutes or as needed :)
"""

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
	
def query_bme():
	"""
	Query BME sensor for meteorological information
	#https://github.com/pimoroni/bme680-python/blob/master/examples/temperature-pressure-humidity.py
	"""
	try:
		sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
	except (RuntimeError, IOError):
		sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)
	
	# These oversampling settings can be tweaked to
	# change the balance between accuracy and noise in
	# the data.

	sensor.set_humidity_oversample(bme680.OS_2X)
	sensor.set_pressure_oversample(bme680.OS_4X)
	sensor.set_temperature_oversample(bme680.OS_8X)
	sensor.set_filter(bme680.FILTER_SIZE_3)
	
	while True:
		if sensor.get_sensor_data():
			temp = sensor.data.temperature
			pres = round(sensor.data.pressure)
			rh = round(sensor.data.humidity)
			break
	return temp, rh, pres
#########################################################
# Build datasets from API calls
#########################################################

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
wx_labels = ['LTS',u' °C','c%','mm']


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

import inky
from inky.auto import auto
from PIL import Image, ImageFont, ImageDraw
from font_fredoka_one import FredokaOne

inky_disp = auto(ask_user=True, verbose=True)
inky_disp.set_border(inky.BLACK)
inky_disp.h_flip = True
inky_disp.v_flip = True

img = Image.open("/home/pi/inky_display/clouds.png")
draw = ImageDraw.Draw(img)
draw.line((7, 17, 203, 17)) #top horizontal top line
draw.line((133, 17, 133, 80)) #vertical top line
draw.line((7, 80, 203, 80)) #bottom horizontal top line

data_font  = ImageFont.truetype(FredokaOne, 16)
label_font = ImageFont.truetype(FredokaOne, 14)
bme_font = ImageFont.truetype(FredokaOne, 14)

#set data plotting config
wx_col_loc    = [10,40,70,100]
ptv_col_loc   = 140
data_row_loc  = [20,40,60]
label_row_loc = 0
#plot data
for i, row_loc in enumerate(data_row_loc):
	draw.text((wx_col_loc[0], row_loc), time_list[i],  inky.BLACK, font=data_font)
	draw.text((wx_col_loc[1], row_loc), temp_list[i],  inky.BLACK, font=data_font)
	draw.text((wx_col_loc[2], row_loc), cloud_list[i], inky.BLACK, font=data_font)
	draw.text((wx_col_loc[3], row_loc), rain_list[i],  inky.BLACK, font=data_font)
for i, row_loc in enumerate(data_row_loc):
	try:
		draw.text((ptv_col_loc, row_loc), departures_list[i],  inky.BLACK, font=data_font)
	except:
		print('failure on inkphat text ptv')
		continue
#plot labels
for i, col_loc in enumerate(wx_col_loc):
	draw.text((col_loc, label_row_loc), wx_labels[i],  inky.BLACK, font=label_font)
draw.text((ptv_col_loc, label_row_loc), '   Train',  inky.BLACK, font=label_font)

#met data
temp, rh, pres = query_bme()
met_text = f'T: {temp:.1f}°C RH: {rh}% P: {pres}hPa'
draw.text((10, 82), met_text,  inky.BLACK, font=bme_font)

# And show it!
inky_disp.set_image(img)
inky_disp.show()

