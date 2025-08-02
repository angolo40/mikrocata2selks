#!/usr/bin/env python3

import ssl
import os
import socket
import re
import ipaddress
from time import sleep
from datetime import datetime as dt
import pyinotify
import ujson
import json
import librouteros
from librouteros import connect
from librouteros.query import Key
import requests

VERSION = "3.0.2"

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
LOCAL_IP_PREFIX = "192.168.0.0/16"
WHITELIST_IPS = (WAN_IP, LOCAL_IP_PREFIX, "127.0.0.1", "1.1.1.1", "8.8.8.8", "fe80:", "10.0.0.0/8", "172.16.0.0/12")
COMMENT_TIME_FORMAT = "%-d %b %Y %H:%M:%S.%f"  # See datetime strftime formats.
ENABLE_IPV6 = False

#Set comma separated value of suricata alerts severity which will be blocked in Mikrotik. All severity values are ("1","2","3")
SEVERITY=("1","2")

# Allow self-signed certificates
# WARNING: These settings bypass certificate verification and should only be used
# with self-signed certificates in trusted environments
ALLOW_SELF_SIGNED_CERTS = False

# Enable debug mode for verbose logging
DEBUG_MODE = False

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

def debug_log(message):
    """Print message only if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(f"[Mikrocata-DEBUG] {message}")

def sanitize_text(text):
    """Remove emojis and other non-ASCII characters from text"""
    if not text:
        return ""
    # Keep only ASCII characters (removes all emojis and special characters)
    return ''.join(char for char in text if ord(char) < 128)

def is_ip_in_whitelist(ip_to_check, whitelist):
    """
    Check if an IP is in the whitelist, supporting both direct matches,
    prefix matches, and CIDR notation.
    """
    try:
        # Convert the IP to check to an ipaddress object for CIDR matching
        if ':' in ip_to_check:  # IPv6
            ip_obj = ipaddress.IPv6Address(ip_to_check)
        else:  # IPv4
            ip_obj = ipaddress.IPv4Address(ip_to_check)
            
        for item in whitelist:
            # Direct IP match
            if ip_to_check == item:
                debug_log(f"IP {ip_to_check} matches exact whitelist entry {item}")
                return True
                
            # String prefix match (like "192.168.")
            if isinstance(item, str) and not '/' in item and ip_to_check.startswith(item):
                debug_log(f"IP {ip_to_check} matches prefix whitelist entry {item}")
                return True
                
            # CIDR notation check (like "10.0.0.0/8")
            if '/' in item:
                try:
                    network = ipaddress.ip_network(item)
                    if ip_obj in network:
                        debug_log(f"IP {ip_to_check} is within CIDR whitelist range {item}")
                        return True
                except ValueError:
                    print(f"[Mikrocata] Warning: Invalid CIDR notation in whitelist: {item}")
                    
        debug_log(f"IP {ip_to_check} is not in any whitelist entry")
        return False
        
    except ValueError as e:
        debug_log(f"Error checking whitelist for IP {ip_to_check}: {e}")
        # If we can't parse the IP, we should not whitelist it
        return False

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
                            alerts.append(alert)  # Fixed: don't json.loads again
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

    if DEBUG_MODE:
        print(f"[Mikrocata] Processing {len(alerts)} alert events")
    
    if not alerts:
        debug_log("No alerts to process")
        return
        
    try:
        address_list = api.path("/ip/firewall/address-list")
        address_list_v6 = api.path("/ipv6/firewall/address-list")
        resources = api.path("system/resource")
        debug_log("Successfully connected to Mikrotik API paths")
    except Exception as e:
        print(f"[Mikrocata] Error connecting to Mikrotik API: {str(e)}")
        raise

    # Remove duplicate src_ips
    unique_alerts = {item['src_ip']: item for item in alerts}.values()
    debug_log(f"Processing {len(unique_alerts)} unique source IPs from alerts")
    
    for event in unique_alerts:
        debug_log(f"Processing alert: SID={event['alert']['signature_id']}, Severity={event['alert']['severity']}")
        
        # Check alert severity
        if str(event["alert"]["severity"]) not in SEVERITY:
            print(f"[Mikrocata] Skipping alert SID={event['alert']['signature_id']} (severity {event['alert']['severity']})")
            continue

        # Check interface
        if str(event["in_iface"]) not in LISTEN_INTERFACE:
            debug_log(f"Skipping alert from interface {event['in_iface']}")
            continue

        # Check if in ignore list
        if in_ignore_list(ignore_list, event):
            print(f"[Mikrocata] Skipping alert {event['alert']['signature_id']} - in ignore list")
            continue
            
        debug_log(f"Alert passed all filters, preparing to add to MikroTik")
            
        try:
            timestamp = dt.strptime(event["timestamp"],
                                   "%Y-%m-%dT%H:%M:%S.%f%z").strftime(
                                       COMMENT_TIME_FORMAT)
        except Exception as e:
            debug_log(f"Error parsing timestamp {event['timestamp']}: {str(e)}")
            timestamp = dt.now().strftime(COMMENT_TIME_FORMAT)
            
        # Determine if IPv6
        is_v6 = ':' in event["src_ip"]
        curr_list = address_list
        if ENABLE_IPV6 and is_v6:
            debug_log(f"IPv6 address detected: {event['src_ip']}")
            curr_list = address_list_v6
            
        # Check whitelist with improved function
        if is_ip_in_whitelist(event["src_ip"], WHITELIST_IPS):
            debug_log(f"Source IP {event['src_ip']} in whitelist")
            if is_ip_in_whitelist(event["dest_ip"], WHITELIST_IPS):
                debug_log(f"Destination IP {event['dest_ip']} also in whitelist - skipping alert")
                continue

            wanted_ip, wanted_port = event["dest_ip"], event.get("src_port")
            src_ip, src_port = event["src_ip"], event.get("dest_port")
            debug_log(f"Source IP in whitelist, targeting destination: {wanted_ip}")
        else:
            wanted_ip, wanted_port = event["src_ip"], event.get("dest_port")
            src_ip, src_port = event["dest_ip"], event.get("src_port")
            debug_log(f"Targeting source IP: {wanted_ip}")

        # Check if target IP is in whitelist
        if is_ip_in_whitelist(wanted_ip, WHITELIST_IPS):
            print(f"[Mikrocata] Skipping: target IP {wanted_ip} is in whitelist")
            continue

        try:
            # Log original signature before sanitizing
            original_signature = event['alert']['signature']
            debug_log(f"Original signature: {original_signature}")
            
            # Sanitize the signature to remove emojis and special characters
            signature = sanitize_text(original_signature)
            debug_log(f"Sanitized signature: {signature}")
            
            # If significant information was lost in sanitization, log a warning
            if len(signature) < len(original_signature) * 0.7:  # If more than 30% of chars were removed
                debug_log(f"WARNING: Significant information lost during sanitization!")
                
            cmnt = f"""[{event['alert']['gid']}:{
                         event['alert']['signature_id']}] {
                         signature} ::: Port: {
                         wanted_port}/{
                         event['proto']} ::: timestamp: {
                         timestamp}"""

            debug_log(f"Adding to list '{BLOCK_LIST_NAME}': IP={wanted_ip}, Timeout={TIMEOUT}")
            debug_log(f"Comment: {cmnt}")
            
            curr_list.add(list=BLOCK_LIST_NAME,
                         address=wanted_ip,
                         comment=cmnt,
                         timeout=TIMEOUT)

            print(f"[Mikrocata] BLOCKED: {wanted_ip} - SID:{event['alert']['signature_id']} - Severity:{event['alert']['severity']}")
            
            # Telegram notifications
            if enable_telegram:
                debug_log("Telegram notifications enabled, sending message")
                clean_message = sanitize_text(f"From: {wanted_ip}\nTo: {src_ip}:{str(wanted_port)}\nRule: {cmnt}")
                response = sendTelegram(clean_message)
                if response:
                    debug_log(f"Telegram message sent successfully")

        except librouteros.exceptions.TrapError as e:
            debug_log(f"MikroTik TrapError: {str(e)}")
            
            if "failure: already have such entry" in str(e):
                debug_log(f"IP {wanted_ip} already exists in list {BLOCK_LIST_NAME}, updating entry")
                
                # Find and remove existing entry
                existing_entries = list(curr_list.select(_id, _list, _address).where(
                        _address == wanted_ip,
                        _list == BLOCK_LIST_NAME))
                
                debug_log(f"Found {len(existing_entries)} existing entries for {wanted_ip}")
                
                for row in existing_entries:
                    debug_log(f"Removing existing entry with ID {row['.id']}")
                    curr_list.remove(row[".id"])

                # Sanitize the signature here too
                signature = sanitize_text(event['alert']['signature'])
                
                # Add updated entry
                updated_comment = f"""[{event['alert']['gid']}:{
                                 event['alert']['signature_id']}] {
                                 signature} ::: Port: {
                                 wanted_port}/{
                                 event['proto']} ::: timestamp: {
                                 timestamp}"""
                                 
                debug_log(f"Re-adding IP {wanted_ip} with updated comment")
                curr_list.add(list=BLOCK_LIST_NAME,
                             address=wanted_ip,
                             comment=updated_comment,
                             timeout=TIMEOUT)
                print(f"[Mikrocata] UPDATED: {wanted_ip} - SID:{event['alert']['signature_id']}")

            else:
                print(f"[Mikrocata] ERROR: TrapError: {str(e)}")
                raise

        except socket.timeout as e:
            print(f"[Mikrocata] Socket timeout: {str(e)}, reconnecting...")
            connect_to_tik()
        
        except Exception as e:
            print(f"[Mikrocata] ERROR: {type(e).__name__} while processing {wanted_ip}: {str(e)}")
            if DEBUG_MODE:
                import traceback
                print(f"[Mikrocata] Traceback: {traceback.format_exc()}")
            continue

    # Save lists and check uptime every x minutes
    current_time = int(dt.now().timestamp())
    time_since_last_save = current_time - last_save_time
    debug_log(f"Time since last save: {time_since_last_save} seconds (interval: {SAVE_INTERVAL} seconds)")
    
    if time_since_last_save >= SAVE_INTERVAL:
        debug_log(f"Save interval reached, saving lists and checking router uptime")
        last_save_time = current_time
        
        # Check router uptime and restore lists if needed
        debug_log("Checking MikroTik uptime")
        uptime_check = check_tik_uptime(resources)
        
        if uptime_check:
            print("[Mikrocata] Router rebooted - restoring saved lists")
            try:
                add_saved_lists(address_list)
                debug_log("Successfully restored IPv4 address lists")
                if ENABLE_IPV6:
                    add_saved_lists(address_list_v6, True)
                    debug_log("Successfully restored IPv6 address lists")
            except Exception as e:
                print(f"[Mikrocata] ERROR: Failed to restore lists: {str(e)}")
        else:
            debug_log("Router has not been rebooted, no need to restore lists")

        # Save current lists to file
        try:
            save_lists(address_list)
            debug_log("Successfully saved IPv4 address lists")
            if ENABLE_IPV6:
                save_lists(address_list_v6, True)
                debug_log("Successfully saved IPv6 address lists")
        except Exception as e:
            print(f"[Mikrocata] ERROR: Failed to save lists: {str(e)}")
        
        debug_log("Lists saved successfully")
    
    debug_log("Alert processing completed")

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
            debug_log(f"Telegram response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"[Mikrocata] Failed to send Telegram message: {e}")
            debug_log(f"Telegram error details: {str(e)}")
    return False


def main():

    print(f"[Mikrocata] Starting Mikrocata2SELKS v{VERSION}")

    if DEBUG_MODE:
        print("[Mikrocata] Starting in DEBUG mode - verbose logging enabled")
    else:
        print("[Mikrocata] Starting in normal mode")
        
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

    print(f"[Mikrocata] Monitoring {FILEPATH} for alerts")
    print(f"[Mikrocata] Whitelist configured for: {WHITELIST_IPS}")
    print(f"[Mikrocata] Configured to process alerts with severity: {SEVERITY}")

    while True:
        try:
            notifier.loop()

        except (librouteros.exceptions.ConnectionClosed, socket.timeout) as e:
            print(f"[Mikrocata] Connection error: {str(e)}")
            connect_to_tik()
            continue

        except librouteros.exceptions.TrapError as e:
            print(f"[Mikrocata] TrapError: {str(e)}")
            continue

        except KeyError as e:
            print(f"[Mikrocata] KeyError: {str(e)}")
            continue
        
        except Exception as e:
            print(f"[Mikrocata] Unexpected error: {str(e)}")
            if DEBUG_MODE:
                import traceback
                print(f"[Mikrocata] Traceback: {traceback.format_exc()}")
            sleep(5)
            continue

if __name__ == "__main__":
    main()
