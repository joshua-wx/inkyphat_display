###Melbourne Weather + Train Display for Inkyphat

This script using the PTV API and the DarkSky API to create a display for the
inkphat display that shows the next 3 trains and the forecast weather. Helps
you to decide when to leave for the trian (and if it's late) and if you'll need
an umbrella or hat! Also now includes a soil moisture display for the garden using an ADC

Inkyphat display: https://shop.pimoroni.com/products/inky-phat?variant=12549254217811
PTV API: https://www.ptv.vic.gov.au/footer/data-and-reporting/datasets/ptv-timetable-api/
Darksky API: https://darksky.net/dev
ADC: https://learn.adafruit.com/adafruit-4-channel-adc-breakouts/python-circuitpython
soil moisture probe: https://www.sparkfun.com/products/13322

To run, config the myconfig.example file and rename myconfig.py 
You'll also need to register for PTV and Darksky API keys

You can use crontab to run the script every 10minutes or as needed :)

![inky_image](https://user-images.githubusercontent.com/16043083/68093977-bfcc8000-feef-11e9-8947-e05b4771970b.jpg "you can make this too")
