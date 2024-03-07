import network
import time
import secrets
import ntptime

from machine import Pin
from machine import RTC

ssid = secrets.wifi_name
password = secrets.wifi_pass


def set_time():
    print('\nSetting RTC...')
    print("Local time before synchronization: %s" %str(time.localtime()))
    ntptime.settime()
    print("Local time after synchronization: %s" %str(time.localtime()))


def run():
    print('Scanning for available WiFi networks...')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    for n in wlan.scan():
        print('ssid:', n[0], ' | bssid:', n[1], ' | channel:', n[2], ' | RSSI:', n[3], ' | security:', n[4], ' | hidden:', n[5])
    
    print('\nConnecting to \'', ssid, '\'...')
    wlan.connect(ssid, password)

    max_wait = 20
    while max_wait > 0:
        wlan_status = wlan.status()
        if  wlan_status < 0 or wlan_status >= 3:
            break
        max_wait -= 1
        print('Attemts left: ', max_wait, ' | Wlan status: ', wlan_status, ' | Waiting for connection to ', secrets.wifi_name)
        time.sleep(2)

    if wlan.status() != 3:
        raise RuntimeError('Network connection failed')
    else:
        print('Connected to \'', ssid, '\'')
        status = wlan.ifconfig()
        print('ip = ' + status[0])

    set_time()