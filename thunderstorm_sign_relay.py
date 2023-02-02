import RPi.GPIO as GPIO
from time import sleep
import requests

#If code is stopped while the solenoid is active it stays active
#This may produce a warning if the code is restarted and it finds the GPIO Pin, which it defines as non-active in next line, is still active
#from previous time the code was run. This line prevents that warning syntax popping up which if it did would stop the code running.
GPIO.cleanup()
GPIO.setwarnings(True)
#This means we will refer to the GPIO pins
#by the number directly after the word GPIO. A good Pin Out Resource can be found here https://pinout.xyz/

#This sets up the GPIO 18 pin as an output pin
GPIO.setmode(GPIO.BCM)
GPIO.setup(21, GPIO.OUT)

#get bom melbourne forecast
headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36"} 
response = requests.get("http://www.bom.gov.au/vic/forecasts/melbourne.shtml", headers=headers)
web_text = response.text

if "thunderstorm" in web_text:
    #turn on relay
    GPIO.output(21, 1)
else:
    # turn off relay
    GPIO.output(21, 0)

