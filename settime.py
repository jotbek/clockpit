import network
import socket
import time
import struct
import secrets

from machine import Pin
from machine import RTC

NTP_DELTA = 2208988800
host = "pool.ntp.org"

ssid = secrets.wifi_name
password = secrets.wifi_pass

def set_time():
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    addr = socket.getaddrinfo(host, 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(1)
        res = s.sendto(NTP_QUERY, addr)
        msg = s.recv(48)
    finally:
        s.close()
    val = struct.unpack("!I", msg[40:44])[0]
    t = val - NTP_DELTA    
    tm = time.gmtime(t)
    RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))


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