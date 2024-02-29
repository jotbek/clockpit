import network
import time
import secrets
import ntptime

from machine import Pin
from machine import RTC

ssid = secrets.wifi_name
password = secrets.wifi_pass


def set_time():
    print("Local time before synchronization: %s" %str(time.localtime()))
    ntptime.settime()
    print("Local time after synchronization: %s" %str(time.localtime()))


def run():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print(wlan.scan())
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
        raise RuntimeError('network connection failed')
    else:
        print('connected')
        status = wlan.ifconfig()
        print( 'ip = ' + status[0] )

    set_time()
    print("Local time fetched from NTP sever. Onboard RTC set to: ", time.localtime())