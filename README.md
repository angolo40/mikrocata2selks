<h1 align="center">Welcome to Mikrocata2SELKS 👋</h1>
<p>
  <img alt="Version" src="https://img.shields.io/badge/version-2.2.1-blue.svg?cacheSeconds=2592000" />
  <a href="https://github.com/angolo40/mikrocata2selks" target="_blank">
    <img alt="License: MIT" src="https://img.shields.io/github/license/angolo40/Mikrocata2SELKS" />
  </a>
</p>

## 📋 Introduction

This repository is designed to simplify the installation process for the IDS/IPS Suricata for packet analysis from Mikrotik devices.

**Minimum Requirements:**
- 4 CPU cores
- 10 GB of free RAM
- Minimum 10 GB of free disk space (actual disk occupation will mainly depend of the number of rules and the amount of traffic on the network - 200GB+ SSD grade recommended).


## 🚀 Install

- Setup a fresh Debian 12 install on a dedicated machine (server or vm)
- Login as root
- Install git with 'apt install git'
- Clone this git repo 'git clone https://github.com/angolo40/mikrocata2selks.git'
- Edit easyinstall.sh with path where to install SELKS and how many Mikrotik to handle
- Run ./easyinstall.sh
- Once finished edit /usr/local/bin/mikrocataTZSP0.py with your Mikrotik and Telegram parameters and then reload service with 'systemctl restart mikrocataTZSP0.service'
- Configure Mikrotik


## 📡 Mikrotik Setup

- /tool sniffer set filter-stream=yes streaming-enabled=yes streaming-server=[DEBIANIP]:37008 (37008 is default port for Mikrotik0)
- /tool sniffer start
- /ip/firewall/raw/add action=drop chain=prerouting comment="IPS-drop_in_bad_traffic" src-address-list=Suricata
- /ip/firewall/raw/add action=drop chain=prerouting comment="IPS-drop_out_bad_traffic" dst-address-list=Suricata
Enabling Mikrotik API:
- /ip service set api-ssl address=[DEBIANIP] enabled=yes
Add Mikrocata user in Mikrotik:
-  /user/add name=mikrocata2selks password=xxxxxxxxxxxxx group=full (change password)


## 🛠️ Handle Multiple Mikrotik Devices

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


## 💡 Functions

- Installs Docker and Docker Compose.
- Installs Python.
- Download and install SELKS repo (https://github.com/StamusNetworks/SELKS)
- Download and install Mikrocata
- Installs TZSP interface.
- Enables notifications over Telegram when an IP is blocked.


## 🔄 Changelog

### 2.2.1
- Fixed bug causing microcata.py script crash during Suricata logrotate.

### 2.2
- Migrated compatibility to Debian 12.

### 2.1
- Improved stability of the read_json function.(thanks to bekhzad-khamidullaev)


## 🔧 Troubleshooting

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

## 📝 Notes
- default account of SELKS:
- - Username: selks-user
  - Password: selks-user

## 👤 Author

**Giuseppe Trifilio**

- [Website](https://github.com/angolo40/mikrocata2selks)
- [Github](https://github.com/angolo40)

Inspired by [zzbe/mikrocata](https://github.com/zzbe/mikrocata).

## 🤝 Contributing

Contributions, issues, and feature requests are welcome. Check the [issues page](https://github.com/angolo40/mikrocata2selks).

## 🌟 Show Your Support

Give a ⭐️ if this project helped you!

- **BTC**: `bc1qad42pe2ux24y6vek07stmr7dknrq7dzrcws4k7`
- **BNB**: `0x5fe7087ea857b0b5e509e81cbe120c3bd7524e1f`
- **XMR**: `87LLkcvwm7JUZAVjusKsnwNRPfhegxe73X7X3mWXDPMnTBCb6JDFnspbN8qdKZA6StHXqnJxMp3VgRK7DcS2sgnW3wH7Xhw`
