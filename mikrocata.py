#!/usr/bin/env python3

import ssl
import os
import socket
import re
from time import sleep
from datetime import datetime as dt
import pyinotify
import ujson
import json
import librouteros
from librouteros import connect
from librouteros.query import Key
import requests

# ------------------------------------------------------------------------------
################# START EDIT SETTINGS

#Set Mikrotik login information
USERNAME = "mikrocata2selks"
PASSWORD = "password"
ROUTER_IP = "192.168.0.1"
TIMEOUT = "1d"
USE_SSL = False  # Set to True to use SSL connection
PORT = 8728  # Default port for non-SSL connection. Will use 8729 if USE_SSL is True
BLOCK_LIST_NAME = "Suricata"

#Set Telegram information
enable_telegram = False
TELEGRAM_TOKEN = "TOKEN"
TELEGRAM_CHATID = "CHATID"

# You can add your WAN IP, so it doesn't get mistakenly blocked (don't leave empty string)
WAN_IP = "yourpublicip"
LOCAL_IP_PREFIX = "192.168."
WHITELIST_IPS = (WAN_IP, LOCAL_IP_PREFIX, "127.0.0.1", "1.1.1.1", "8.8.8.8", "fe80:")
COMMENT_TIME_FORMAT = "%-d %b %Y %H:%M:%S.%f"  # See datetime strftime formats.
ENABLE_IPV6 = False

#Set comma separated value of suricata alerts severity which will be blocked in Mikrotik. All severity values are ("1","2","3")
SEVERITY=("1","2")

# Allow self-signed certificates
# WARNING: These settings bypass certificate verification and should only be used
# with self-signed certificates in trusted environments
ALLOW_SELF_SIGNED_CERTS = False

################# END EDIT SETTINGS
# ------------------------------------------------------------------------------
LISTEN_INTERFACE=("tzsp0")

# Suricata log file
SELKS_CONTAINER_DATA_SURICATA_LOG="/root/SELKS/docker/containers-data/suricata/logs/"
FILEPATH = os.path.abspath(SELKS_CONTAINER_DATA_SURICATA_LOG + "eve.json")

# Save Mikrotik address lists to a file and reload them on Mikrotik reboot.
# You can add additional list(s), e.g. [BLOCK_LIST_NAME, "blocklist1", "list2"]
SAVE_LISTS = [BLOCK_LIST_NAME]

# (!) Make sure you have privileges (!)
SAVE_LISTS_LOCATION = os.path.abspath("/var/lib/mikrocata/savelists-tzsp0.json")
SAVE_LISTS_LOCATION_V6 = os.path.abspath("/var/lib/mikrocata/savelists-tzsp0_v6.json")
# Location for Mikrotik's uptime. (needed for re-adding lists after reboot)
UPTIME_BOOKMARK = os.path.abspath("/var/lib/mikrocata/uptime-tzsp0.bookmark")

# Ignored rules file location - check ignore.conf for syntax.
IGNORE_LIST_LOCATION = os.path.abspath("/var/lib/mikrocata/ignore-tzsp0.conf")

# Add all alerts from alerts.json on start?
# Setting this to True will start reading alerts.json from beginning
# and will add whole file to firewall when pyinotify is triggered.
# Just for testing purposes, i.e. not good for systemd service.
ADD_ON_START = False

# global vars
last_pos = 0
api = None
ignore_list = []
last_save_time = 0
SAVE_INTERVAL = 300  # Save lists every 5 minutes

class EventHandler(pyinotify.ProcessEvent):
    def process_IN_MODIFY(self, event):
        if event.pathname == FILEPATH:
            try:
                add_to_tik(read_json(FILEPATH))
            except ConnectionError:
                connect_to_tik()

    def process_IN_CREATE(self, event):
        if event.pathname == FILEPATH:
            print(f"[Mikrocata] New eve.json detected. Resetting last_pos.")
            global last_pos
            last_pos = 0
            self.process_IN_MODIFY(event)

    def process_IN_DELETE(self, event):
        if event.pathname == FILEPATH:
            print(f"[Mikrocata] eve.json deleted. Monitoring for new file.")

def seek_to_end(fpath):
    global last_pos

    if not ADD_ON_START:
        while True:
            try:
                last_pos = os.path.getsize(fpath)
                return

            except FileNotFoundError:
                print(f"[Mikrocata] File: {fpath} not found. Retrying in 10 seconds..")
                sleep(10)
                continue


def read_json(fpath):
    global last_pos
    while True:
        try:
            with open(fpath, "r") as f:
                f.seek(last_pos)
                alerts = []
                for line in f.readlines():
                    try:
                        alert = json.loads(line)
                        if alert.get('event_type') == 'alert':
                            alerts.append(json.loads(line))
                        else:
                            last_pos = f.tell()
                            continue
                    except:
                        continue
                last_pos = f.tell()
                return alerts
        except FileNotFoundError:
            print(f"[Mikrocata] File: {fpath} not found. Retrying in 10 seconds..")
            sleep(10)
            continue


def add_to_tik(alerts):
    global last_pos
    global api
    global last_save_time
    
    _address = Key("address")
    _id = Key(".id")
    _list = Key("list")

    address_list = api.path("/ip/firewall/address-list")
    address_list_v6 = api.path("/ipv6/firewall/address-list")
    resources = api.path("system/resource")

    # Remove duplicate src_ips.
    for event in {item['src_ip']: item for item in alerts}.values():

        if str(event["alert"]["severity"]) not in SEVERITY:
            print("pass severity: " + str(event["alert"]["severity"]))
            break

        if str(event["in_iface"]) not in LISTEN_INTERFACE:
            break

        if not in_ignore_list(ignore_list, event):
            timestamp = dt.strptime(event["timestamp"],
                                    "%Y-%m-%dT%H:%M:%S.%f%z").strftime(
                                        COMMENT_TIME_FORMAT)
            is_v6 = ':' in event["src_ip"]
            curr_list = address_list
            if ENABLE_IPV6 and is_v6:
                curr_list = address_list_v6
            if event["src_ip"].startswith(WHITELIST_IPS):
                if event["dest_ip"].startswith(WHITELIST_IPS):
                    continue

                wanted_ip, wanted_port = event["dest_ip"], event.get("src_port")
                src_ip, src_port = event["src_ip"], event.get("dest_port")

            else:
                wanted_ip, wanted_port = event["src_ip"], event.get("dest_port")
                src_ip, src_port = event["dest_ip"], event.get("src_port")

            try:
                cmnt=f"""[{event['alert']['gid']}:{
                                 event['alert']['signature_id']}] {
                                 event['alert']['signature']} ::: Port: {
                                 wanted_port}/{
                                 event['proto']} ::: timestamp: {
                                 timestamp}"""

                curr_list.add(list=BLOCK_LIST_NAME,
                                 address=wanted_ip,
                                 comment=cmnt,
                                 timeout=TIMEOUT)

                print(f"[Mikrocata] new ip added: {cmnt}")
                if enable_telegram == True:
                    print(requests.get(sendTelegram("From: " + wanted_ip + "\nTo: " + src_ip + ":" + str(wanted_port) + "\nRule: " + cmnt)).json())


            except librouteros.exceptions.TrapError as e:
                if "failure: already have such entry" in str(e):
                    for row in curr_list.select(_id, _list, _address).where(
                            _address == wanted_ip,
                            _list == BLOCK_LIST_NAME):
                        curr_list.remove(row[".id"])

                    curr_list.add(list=BLOCK_LIST_NAME,
                                     address=wanted_ip,
                                     comment=f"""[{event['alert']['gid']}:{
                                     event['alert']['signature_id']}] {
                                     event['alert']['signature']} ::: Port: {
                                     wanted_port}/{
                                     event['proto']} ::: timestamp: {
                                     timestamp}""",
                                     timeout=TIMEOUT)

                else:
                    raise

            except socket.timeout:
                connect_to_tik()

    # If router has been rebooted add saved list(s), then save lists to a file.
    # Only save lists and check uptime every x minutes
    current_time = int(dt.now().timestamp())
    if current_time - last_save_time >= SAVE_INTERVAL:
        last_save_time = current_time
        
        # Check router uptime and restore lists if needed
        if check_tik_uptime(resources):
            add_saved_lists(address_list)
            if ENABLE_IPV6:
                add_saved_lists(address_list_v6, True)

        # Save current lists to file
        save_lists(address_list)
        if ENABLE_IPV6:
            save_lists(address_list_v6, True)
        
        print("[Mikrocata] Lists saved")

def check_tik_uptime(resources):

    for row in resources:
        uptime = row["uptime"]

    if "w" in uptime:
        weeks = int(re.search(r"(\A|\D)(\d*)w", uptime).group(2))
    else:
        weeks = 0

    if "d" in uptime:
        days = int(re.search(r"(\A|\D)(\d*)d", uptime).group(2))
    else:
        days = 0

    if "h" in uptime:
        hours = int(re.search(r"(\A|\D)(\d*)h", uptime).group(2))
    else:
        hours = 0

    if "m" in uptime:
        minutes = int(re.search(r"(\A|\D)(\d*)m", uptime).group(2))
    else:
        minutes = 0

    if "s" in uptime:
        seconds = int(re.search(r"(\A|\D)(\d*)s", uptime).group(2))
    else:
        seconds = 0

    total_seconds = (weeks*7*24 + days*24 + hours)*3600 + minutes*60 + seconds

    if total_seconds < 900:
        total_seconds = 900

    with open(UPTIME_BOOKMARK, "r") as f:
        try:
            bookmark = int(f.read())
        except ValueError:
            bookmark = 0

    with open(UPTIME_BOOKMARK, "w+") as f:
        f.write(str(total_seconds))

    if total_seconds < bookmark:
        return True

    return False


def connect_to_tik():
    global api
    
    # Determine which port to use
    actual_port = 8729 if USE_SSL else 8728
    
    while True:
        try:
            if USE_SSL:
                # SSL connection setup
                if ALLOW_SELF_SIGNED_CERTS:
                    # Settings for self-signed certificates
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    ctx.set_ciphers('DEFAULT@SECLEVEL=0')
                else:
                    # Settings for valid certificates
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = True
                    ctx.verify_mode = ssl.CERT_REQUIRED
                    ctx.set_ciphers('DEFAULT@SECLEVEL=2')

                # Connect with SSL
                api = connect(username=USERNAME, password=PASSWORD, host=ROUTER_IP,
                            ssl_wrapper=ctx.wrap_socket, port=actual_port)
            else:
                # Plain connection without SSL
                api = connect(username=USERNAME, password=PASSWORD, host=ROUTER_IP,
                            port=actual_port)
            print(f"[Mikrocata] Connected to Mikrotik")
            break


        except librouteros.exceptions.TrapError as e:
            if "invalid user name or password" in str(e):
                print("[Mikrocata] Invalid username or password.")
                sleep(10)
                continue

            raise

        except socket.timeout as e:
            print(f"[Mikrocata] Socket timeout: {str(e)}.")
            sleep(30)
            continue

        except ConnectionRefusedError:
            print("[Mikrocata] Connection refused. (api-ssl disabled in router?)")
            sleep(10)
            continue

        except OSError as e:
            if e.errno == 113:
                print("[Mikrocata] No route to host. Retrying in 10 seconds..")
                sleep(10)
                continue

            if e.errno == 101:
                print("[Mikrocata] Network is unreachable. Retrying in 10 seconds..")
                sleep(10)
                continue

            raise

def save_lists(address_list,is_v6=False):
    _address = Key("address")
    _list = Key("list")
    _timeout = Key("timeout")
    _comment = Key("comment")
    curr_file = SAVE_LISTS_LOCATION
    if is_v6:
        curr_file = SAVE_LISTS_LOCATION_V6
    with open(curr_file, "w") as f:
        for save_list in SAVE_LISTS:
            for row in address_list.select(_list, _address, _timeout,
                                           _comment).where(_list == save_list):
                f.write(ujson.dumps(row) + "\n")

def add_saved_lists(address_list, is_v6=False):
    curr_file = SAVE_LISTS_LOCATION
    if is_v6:
        curr_file = SAVE_LISTS_LOCATION_V6
    with open(curr_file, "r") as f:
        addresses = [ujson.loads(line) for line in f.readlines()]
    for row in addresses:
        cmnt = row.get("comment")
        if cmnt is None:
            cmnt = ""
        try:
            address_list.add(list=row["list"], address=row["address"],
                             comment=cmnt, timeout=row["timeout"])

        except librouteros.exceptions.TrapError as e:
            if "failure: already have such entry" in str(e):
                continue

            raise

def read_ignore_list(fpath):
    global ignore_list

    try:
        with open(fpath, "r") as f:

            for line in f:
                line = line.partition("#")[0].strip()

                if line.strip():
                    ignore_list.append(line)

    except FileNotFoundError:
        print(f"[Mikrocata] File: {IGNORE_LIST_LOCATION} not found. Continuing..")

def in_ignore_list(ignr_list, event):
    for entry in ignr_list:
        if entry.isdigit() and int(entry) == int(event['alert']['signature_id']):
            sleep(1)
            return True

        if entry.startswith("re:"):
            entry = entry.partition("re:")[2].strip()

            if re.search(entry, event['alert']['signature']):
                sleep(1)
                return True

    return False

def sendTelegram(message):
    if enable_telegram:
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHATID}&text={message}&disable_web_page_preview=true&parse_mode=html"
        try:
            response = requests.get(telegram_url)
            print(response.json())
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
    return telegram_url


def main():
    seek_to_end(FILEPATH)
    connect_to_tik()
    read_ignore_list(IGNORE_LIST_LOCATION)
    os.makedirs(os.path.dirname(SAVE_LISTS_LOCATION), exist_ok=True)
    os.makedirs(os.path.dirname(SAVE_LISTS_LOCATION_V6), exist_ok=True)
    os.makedirs(os.path.dirname(UPTIME_BOOKMARK), exist_ok=True)

    directory_to_monitor = os.path.dirname(FILEPATH)

    wm = pyinotify.WatchManager()
    handler = EventHandler()
    notifier = pyinotify.Notifier(wm, handler)
    wm.add_watch(directory_to_monitor, pyinotify.IN_CREATE | pyinotify.IN_MODIFY | pyinotify.IN_DELETE, rec=False)

    while True:
        try:
            notifier.loop()

        except (librouteros.exceptions.ConnectionClosed, socket.timeout) as e:
            print(f"[Mikrocata] (4) {str(e)}")
            connect_to_tik()
            continue

        except librouteros.exceptions.TrapError as e:
            print(f"[Mikrocata] (8) librouteros.TrapError: {str(e)}")
            continue

        except KeyError as e:
            print(f"[Mikrocata] (8) KeyError: {str(e)}")
            continue

if __name__ == "__main__":
    main()
