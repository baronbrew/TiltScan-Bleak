import asyncio
import os
from bleak import BleakScanner
from beacontools import parse_packet
from aiohttp import web

async def handler(request):
  dir_list = os.listdir()
  filter_object = filter(lambda a: 'TILT-' in a, dir_list)
  tilt_list = list(filter_object)
  lines = ''
  if (tilt_list):
    for i in tilt_list:
      with open(i) as f:
        lines += str(f.readlines())
  else: print("No Tilt data files found.")
  return web.Response(text=str(lines))

tiltcolordict = {
"a495bb10-c5b1-4b44-b512-1370f02d74de" : "RED",
"a495bb20-c5b1-4b44-b512-1370f02d74de" : "GREEN",
"a495bb30-c5b1-4b44-b512-1370f02d74de" : "BLACK",
"a495bb40-c5b1-4b44-b512-1370f02d74de" : "PURPLE",
"a495bb50-c5b1-4b44-b512-1370f02d74de" : "ORANGE",
"a495bb60-c5b1-4b44-b512-1370f02d74de" : "BLUE",
"a495bb70-c5b1-4b44-b512-1370f02d74de" : "YELLOW",
"a495bb80-c5b1-4b44-b512-1370f02d74de" : "PINK"
}

def detection_callback(device, advertisement_data):
    beacondict = advertisement_data.manufacturer_data
    # only process packets with manufacturer data
    if list(beacondict.keys()):
     # only process packets with manufacturer ID 76 (Apple)
     if (list(beacondict.keys())[0]) == 76:
      beaconbytes = b'\x02\x01\x06\x1a\xff\x4c\x00' + beacondict[76]
      adv = parse_packet(beaconbytes)
      # only process packets that succesfully parse as iBeacons
      if adv:
       print ("Mac: %s" % device.address)
       print ("RSSI: %d" % advertisement_data.rssi)
       print("UUID: %s" % adv.uuid)
       print("Major: %d" % adv.major)
       print("Minor: %d" % adv.minor)
       print("TX Power: %d" % adv.tx_power)
       #Tilt specific processing
       print("Color: %s" % tiltcolordict.get(adv.uuid))
       majorfloat = float(adv.major)
       minorfloat = float(adv.minor)
       if adv.minor < 5000:
        print("Precision: standard")
        print("TempF: %d" % majorfloat)
        print("SG: %.3f" % (minorfloat / 1000))
       else:
        print("Precision: high")
        print("TempF: %.1f" % (majorfloat / 10))
        print("SG: %.4f" % (minorfloat / 10000))
       #Process tx_power byte
       if adv.tx_power == -59:
        print ("Battery Age in Weeks: Updating...")
        #stop_event.set()
       elif adv.tx_power == -103:
        print ("Battery Age in Weeks: Waking up...")
       elif adv.tx_power < 0:
         print ("Battery Age in Weeks: %d" % (int(adv.tx_power) + 2 ** 8))
       else:
         print ("Battery Age in Weeks: %d" % (int(adv.tx_power)))
       with open(('TILT-' + (str(tiltcolordict.get(adv.uuid)) + '-' + device.address).replace(':','-')) + '.json','w') as f:
        f.write(device.address)

stop_server = asyncio.Event()

async def startWebServer():
  server = web.Server(handler)
  runner = web.ServerRunner(server)
  await runner.setup()
  site = web.TCPSite(runner, 'localhost', 8080)
  await site.start()
  print("======= Serving on http://127.0.0.1:8080/ ======")
  await stop_server.wait()

async def startTiltScanner():
  scanner = BleakScanner(filters={"scanning_mode":"passive"})
  async with BleakScanner(detection_callback) as scanner:
    await startWebServer()
    await stop_server.wait()

asyncio.run(startTiltScanner())     
