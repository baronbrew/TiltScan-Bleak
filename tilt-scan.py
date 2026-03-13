import asyncio
import os
import datetime
import time
from bleak import BleakScanner
from beacontools import parse_packet
from aiohttp import web

tiltdatalist = []
tiltdatadict = {}
logging_enabled = True

event_control = asyncio.Event()
restart_scan = asyncio.Event()
scan_active = False
last_csv_log_time = 0
SCAN_DURATION = 3.3
CSV_LOG_INTERVAL = 900  # 15 minutes in seconds

async def handler_data(request):
  global scan_active, restart_scan
  
  # Signal scanner to start a scan
  restart_scan.set()
  
  # Wait for the scan duration to complete
  await asyncio.sleep(SCAN_DURATION)
  
  # Clean up old data
  for i in tiltdatalist:
    # find and remove Tilts not seen in the last 15 minutes
    if i['timeStamp'] + 900000 < time.time() * 1000:
      tiltdatalist.remove(i)
  
  return web.json_response(tiltdatalist)

async def handler_shutdown(request):
  event_control.set()
  return web.Response(text='shutting down')

async def handler_logging_enable(request):
  global logging_enabled
  logging_enabled = True
  return web.Response(text='logging enabled')

async def handler_logging_disable(request):
  global logging_enabled
  logging_enabled = False
  return web.Response(text='logging disabled')

async def handler_logging_status(request):
  return web.json_response({'logging_enabled': logging_enabled})

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
      # only process packets that succesfully parse as Tilts (& exclude disconnected repeaters)
       if tiltcolordict.get(adv.uuid) and float(adv.minor) != 0:
        #print (tiltcolordict.get(adv.uuid))
        """
        print ("Mac: %s" % device.address)
        print ("RSSI: %d" % advertisement_data.rssi)
        print("UUID: %s" % adv.uuid)
        print("Major: %d" % adv.major)
        print("Minor: %d" % adv.minor)
        print("TX Power: %d" % adv.tx_power)
        """
        #Tilt specific processing
        #print("Color: %s" % tiltcolordict.get(adv.uuid))
        majorfloat = float(adv.major)
        minorfloat = float(adv.minor)
        if adv.minor < 5000:
          """
          print("Precision: standard")
          print("TempF: %d" % majorfloat)
          print("SG: %.3f" % (minorfloat / 1000))
          """
          uncalTemp = majorfloat
          uncalSG = minorfloat / 1000
        else:
          """
          print("Precision: high")
          print("TempF: %.1f" % (majorfloat / 10))
          print("SG: %.4f" % (minorfloat / 10000))
          """
          uncalTemp = majorfloat / 10
          uncalSG = minorfloat / 10000
          # Process tx_power byte
        if adv.tx_power == -59:
          #print ("Battery Age in Weeks: Updating...")
          battAgeWeeks = 'pending'
          opStatus = 0
        elif adv.tx_power == -103:
          #print ("Battery Age in Weeks: Waking up...")
          battAgeWeeks = 'pending'
          opStatus = 'wake up'
        elif adv.tx_power < 0:
          #print ("Battery Age in Weeks: %d" % (int(adv.tx_power) + 2 ** 8))
          battAgeWeeks = int(adv.tx_power) + 2 ** 8
          opStatus = 1
        else:
          #print ("Battery Age in Weeks: %d" % (int(adv.tx_power)))
          battAgeWeeks = int(adv.tx_power)
          opStatus = 1
        formatteddate = datetime.datetime.now().strftime('%x %X')
        Timepoint = (time.time() / 60 / 60 / 24 + 25569) - time.timezone / 60 / 60 / 24
        global tiltdatalist
        global tiltdatadict
        try:
         lastLoggedtoCSV = tiltdatadict['lastLoggedtoCSV']
        except:
          lastLoggedtoCSV = 0
        tiltdatadict = {
        "uuid" : adv.uuid.replace('-',''),
        "major" : adv.major,
        "minor" : adv.minor,
        "tx_power" : adv.tx_power,
        "rssi" : advertisement_data.rssi,
        "mac" : device.address,
        "Color" : tiltcolordict.get(adv.uuid),
        "timeStamp" : time.time() * 1000  ,
        "formatteddate" : formatteddate,
        "Timepoint" : (time.time() / 60 / 60 / 24 + 25569) - time.timezone / 60 / 60 / 24,
        "uncalSG" : uncalSG,
        "uncalTemp" : uncalTemp,
        "tempunits" : "°F",
        "battAgeWeeks" : battAgeWeeks,
        "opStatus" : opStatus,
        "lastLoggedtoCSV" : lastLoggedtoCSV
        }
        if not tiltdatalist:
          # log to csv and append to empty list
          if logging_enabled:
            try:
                with open(('TILT-' + (str(tiltcolordict.get(adv.uuid)) + '-' + device.address).replace(':','-')) + '.csv','x') as f:
                  f.write(
                      'Timestamp,Timepoint,SG,Temp,Color,Beer,Comment\n' 
                    + formatteddate + ','
                    + str(Timepoint) + ','
                    + str(uncalSG) + ','
                    + str(uncalTemp) + ','
                    + tiltcolordict.get(adv.uuid) + ':' + device.address + ','
                    + 'Untitled' + ','
                    + '' + '\n'
                    )
                tiltdatadict['lastLoggedtoCSV'] = time.time() * 1000
                tiltdatalist.append(tiltdatadict)
            except:
                with open(('TILT-' + (str(tiltcolordict.get(adv.uuid)) + '-' + device.address).replace(':','-')) + '.csv','a') as f:
                  f.write(
                      formatteddate + ','
                    + str(Timepoint) + ','
                    + str(uncalSG) + ','
                    + str(uncalTemp) + ','
                    + tiltcolordict.get(adv.uuid) + ':' + device.address + ','
                    + 'Untitled' + ','
                    + '' + '\n'
                    )
                tiltdatadict['lastLoggedtoCSV'] = time.time() * 1000
                tiltdatalist.append(tiltdatadict)
          else:
            tiltdatalist.append(tiltdatadict)
        for i in tiltdatalist:
          if i['mac'] == tiltdatadict['mac']:
            # log to csv every 15 minutes and update list regardless
            if tiltdatadict['timeStamp'] - 900000 > i['lastLoggedtoCSV']:
             if logging_enabled:
              try:
                with open(('TILT-' + (str(tiltcolordict.get(adv.uuid)) + '-' + device.address).replace(':','-')) + '.csv','x') as f:
                  f.write(
                      'Timestamp,Timepoint,SG,Temp,Color,Beer,Comment\n' 
                    + formatteddate + ','
                    + str(Timepoint) + ','
                    + str(uncalSG) + ','
                    + str(uncalTemp) + ','
                    + tiltcolordict.get(adv.uuid) + ':' + device.address + ','
                    + 'Untitled' + ','
                    + '' + '\n'
                    )
                tiltdatadict['lastLoggedtoCSV'] = time.time() * 1000
              except:
                with open(('TILT-' + (str(tiltcolordict.get(adv.uuid)) + '-' + device.address).replace(':','-')) + '.csv','a') as f:
                  f.write(
                      formatteddate + ','
                    + str(Timepoint) + ','
                    + str(uncalSG) + ','
                    + str(uncalTemp) + ','
                    + tiltcolordict.get(adv.uuid) + ':' + device.address + ','
                    + 'Untitled' + ','
                    + '' + '\n'
                    )
                tiltdatadict['lastLoggedtoCSV'] = time.time() * 1000
            # Always update the list entry with new data
            tiltdatalist[tiltdatalist.index(i)] = tiltdatadict
            break
          elif tiltdatalist.index(i) == len(tiltdatalist) - 1:
            # log to csv on Tilt's first append
            if logging_enabled:
              try:
                with open(('TILT-' + (str(tiltcolordict.get(adv.uuid)) + '-' + device.address).replace(':','-')) + '.csv','x') as f:
                  f.write(
                      'Timestamp,Timepoint,SG,Temp,Color,Beer,Comment\n' 
                    + formatteddate + ','
                    + str(Timepoint) + ','
                    + str(uncalSG) + ','
                    + str(uncalTemp) + ','
                    + tiltcolordict.get(adv.uuid) + ':' + device.address + ','
                    + 'Untitled' + ','
                    + '' + '\n'
                    )
                tiltdatadict['lastLoggedtoCSV'] = time.time() * 1000
                tiltdatalist.append(tiltdatadict)
              except:
                with open(('TILT-' + (str(tiltcolordict.get(adv.uuid)) + '-' + device.address).replace(':','-')) + '.csv','a') as f:
                  f.write(
                      formatteddate + ','
                    + str(Timepoint) + ','
                    + str(uncalSG) + ','
                    + str(uncalTemp) + ','
                    + tiltcolordict.get(adv.uuid) + ':' + device.address + ','
                    + 'Untitled' + ','
                    + '' + '\n'
                    )
                tiltdatadict['lastLoggedtoCSV'] = time.time() * 1000
                tiltdatalist.append(tiltdatadict)
            else:
              tiltdatalist.append(tiltdatadict) 
            break

async def startWebServer():
  app = web.Application()
  app.router.add_get('/data', handler_data)
  app.router.add_get('/shutdown', handler_shutdown)
  app.router.add_get('/logging/enable', handler_logging_enable)
  app.router.add_get('/logging/disable', handler_logging_disable)
  app.router.add_get('/logging/status', handler_logging_status)
  runner = web.AppRunner(app)
  await runner.setup()
  site = web.TCPSite(runner, 'localhost', 1880)
  await site.start()
  print("======= Serving on http://127.0.0.1:1880/ =======")
  print("======= /data - get sensor data =======")
  print("======= /logging/enable - enable CSV logging =======")
  print("======= /logging/disable - disable CSV logging =======")
  print("======= /logging/status - check logging status =======")
  print("======= /shutdown - stop server =======")
  await event_control.wait()

async def scanTilt():
  global scan_active, last_csv_log_time, restart_scan
  
  while not event_control.is_set():
    try:
      restart_scan.clear()
      current_time = time.time()
      
      # Check if CSV logging is needed
      needs_csv_scan = (current_time - last_csv_log_time) >= CSV_LOG_INTERVAL
      
      # Create tasks to monitor
      tasks = [
        asyncio.create_task(restart_scan.wait()),
        asyncio.create_task(event_control.wait())
      ]
      
      if needs_csv_scan:
        # Wait for restart, shutdown, or CSV log interval
        csv_wait_time = CSV_LOG_INTERVAL - (current_time - last_csv_log_time)
        tasks.append(asyncio.create_task(asyncio.sleep(max(0, csv_wait_time))))
      
      done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED
      )
      
      # Cancel remaining tasks
      for task in pending:
        task.cancel()
        try:
          await task
        except asyncio.CancelledError:
          pass
      
      # Check for shutdown before starting scan
      if event_control.is_set():
        break
      
      # Start scan
      scan_active = True
      try:
        async with BleakScanner(detection_callback, filters={"scanning_mode":"passive"}) as scanner:
          # Scan for the specified duration
          await asyncio.sleep(SCAN_DURATION)
      finally:
        scan_active = False
        last_csv_log_time = time.time()
        
    except Exception as e:
      print(f"Scanner error: {e}")
      scan_active = False
      if not event_control.is_set():
        await asyncio.sleep(1)

async def startTiltScanner():
  await asyncio.gather(
    startWebServer(),
    scanTilt()
  )

asyncio.run(startTiltScanner())     
