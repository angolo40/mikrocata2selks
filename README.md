<h1 align="center">Welcome to Mikrocata2SELKS 👋</h1>
<p>
  <img alt="Version" src="https://img.shields.io/badge/version-2.1.0-blue.svg?cacheSeconds=2592000" />
  <a href="https://github.com/angolo40/mikrocata2selks" target="_blank">
    <img alt="License: MIT" src="https://img.shields.io/github/license/angolo40/Mikrocata2SELKS" />
  </a>
</p>

> Script for auto-install Selks and mikrocata on Debian 12
## Introduction
This repo intend to semplify installation of IDS/IPS Suricata for packet analyzing coming from Mikrotik.
It uses latest docker repo from SELKS (Suricata, ELK Stack) and mikrocata.

Minimum working setup:

- 4 cores
- 10 GB of free RAM
- minimum 10 GB of free disk space (actual disk occupation will mainly depend of the number of rules and the amount of traffic on the network). 200GB+ SSD grade is recommended.

## Install

- Setup a fresh Debian 12 install on a dedicated machine (server or vm)
- Login as root
- Install git with 'apt install git'
- Download this git repo
- Edit easyinstall.sh with path where to install SELKS and how many Mikrotik to handle
- Run ./easyinstall.sh
- Once finished edit /usr/local/bin/mikrocataTZSP0.py with your Mikrotik and Telegram parameters and then reload service with 'systemctl restart mikrocataTZSP0.service'
- Configure Mikrotik

## Handle multiple Mikrotik

- Setting more than 1 Mikrotik it will create for each device a dedicated dummy interface and dedicated mikrocata service.
- Example:
- - for Mikrotik0 will create tzsp0 interface listening at 37008 port and /usr/local/bin/mikrocataTZSP0.py
- - for Mikrotik1 will create tzsp1 interface listening at 37009 port and /usr/local/bin/mikrocataTZSP1.py
- - for Mikrotik2 will create tzsp2 interface listening at 37010 port and /usr/local/bin/mikrocataTZSP2.py
- - and so on...
- - So you have to edit:
- - /usr/local/bin/mikrocataTZSP0.py with specific Mikrotik0 value and enable sniffer on Mikrotik0 sending data to 37008 port.
- - /usr/local/bin/mikrocataTZSP1.py with specific Mikrotik1 value and enable sniffer on Mikrotik1 sending data to 37009 port
- - /usr/local/bin/mikrocataTZSP2.py with specific Mikrotik2 value and enable sniffer on Mikrotik2 sending data to 37010 port.
- - and so on...

## Mikrotik setup

- /tool sniffer set filter-stream=yes streaming-enabled=yes streaming-server=xxx.xxx.xxx.xxx:37008 (xxx.xxx.xxx.xxx is your Debian ip addr, 37008 is default port for Mikrotik0)
- /tool sniffer start

- /ip/firewall/raw/add action=drop chain=prerouting comment="IPS-drop_in_bad_traffic" src-address-list=Suricata
- /ip/firewall/raw/add action=drop chain=prerouting comment="IPS-drop_out_bad_traffic" dst-address-list=Suricata

Enabling Mikrotik API

- /ip service set api-ssl address=xxx.xxx.xxx.xxx enabled=yes (xxx.xxx.xxx.xxx is your Debian ip addr)

Add Mikrotik User

-  /user/add name=mikrocata2selks password=xxxxxxxxxxxxx group=full (change password)

## Functions
- Install Docker and Docker Compose
- Install Python
- Download and install SELKS repo (https://github.com/StamusNetworks/SELKS)
- Download and install Mikrocata
- Install TZSP interface
- Notification over Telegram when ip is blocked

## Changelog 2.2
- migrated compatibility to debian 12

## Changelog 2.1
- now mikrotcata read alerts from default suricata eve.json instead of create a new one 
- rewrited read_json function for better stability (thanks to bekhzad-khamidullaev)

## Troubleshooting
- Check if packets are coming to VM from mikrotik through dummy interface
```sh
tcpdump -i tzsp0
```
- Check if mikrocata service and tzsp0 interface are up and running
```sh
systemctl status mikrocataTZSP0.service
systemctl status TZSPreplay37008@tzsp0.service
```
- Check if suricata docker is up and running
```sh
docker logs -f suricata
```
## Notes
- default account of SELKS:
- - Username: selks-user
  - Password: selks-user

## Author

👤 **Giuseppe Trifilio**

* Website: https://github.com/angolo40/mikrocata2selks
* Github: [@angolo40](https://github.com/angolo40)
* Inspired by https://github.com/zzbe/mikrocata

## 🤝 Contributing

- Contributions, issues and feature requests are welcome!<br />Feel free to check [issues page](https://github.com/angolo40/mikrocata2selks).
## Show your support

- Give a ⭐️ if this project helped you!
- BTC: bc1qga68pwf49sfhdd9nj96m8e2s65ypjegtx8lafj
- BNB: 0x720b2b3e4436ec7064d54598BAd113e5293fF691
***

_This README was generated with ❤️ by [readme-md-generator](https://github.com/kefranabg/readme-md-generator)_
