<h1 align="center">Welcome to Mikrocata2SELKS 👋</h1>
<p>
  <img alt="Version" src="https://img.shields.io/badge/version-1.0.0-blue.svg?cacheSeconds=2592000" />
  <a href="https://github.com/angolo40/mikrocata2selks" target="_blank">
    <img alt="License: MIT" src="https://img.shields.io/github/license/angolo40/Mikrocata2SELKS" />
  </a>
</p>

> Script for auto-install Selks and mikrocata on Debian 11
## Introduction
This repo intend to semplify installation of IDS/IPS Suricata for packet analyzing analyzing coming from Mikrotik.
It uses latest docker repo from SELKS (Suricata, ELK Stack) and mikrocata.

Minimum working setup:

- 2 cores
- 10 GB of free RAM
- minimum 10 GB of free disk space (actual disk occupation will mainly depend of the number of rules and the amount of traffic on the network). 200GB+ SSD grade is recommended.

## Functions
- Install Docker and Docker Compose
- Install Python
- Download and install SELKS repo (https://github.com/StamusNetworks/SELKS)
- Download and install Mikrocata
- Install TZSP interface
- Notification over Telegram when ip is blocked

## Install

```sh
./easyinstall.sh
```

## Usage

- Setup a fresh Debian 11 install on a dedicated machine (server or vm)
- Login as root
- Download this git repo
- Edit easyinstall.sh with path where to install SELKS
- Run ./easyinstall.sh
- Once finished edit /usr/local/bin/mikrocata.py with your Mikrotik and Telegram parameters and then reload service with 'systemctl restart mikrocata.service'
- Configure Mikrotik

## Mikrotik setup

- /tool sniffer set filter-stream=yes streaming-enabled=yes streaming-server=xxx.xxx.xxx.xxx (xxx.xxx.xxx.xxx is your Debian ip addr)
- /tool sniffer start

- /ip/firewall/raw/add action=drop chain=prerouting comment="IPS-drop_in_bad_traffic" src-address-list=Suricata
- /ip/firewall/raw/add action=drop chain=prerouting comment="IPS-drop_out_bad_traffic" dst-address-list=Suricata

Enabling Mikrotik API

- /ip service set api-ssl address=xxx.xxx.xxx.xxx enabled=yes (xxx.xxx.xxx.xxx is your Debian ip addr)

Add Mikrotik User

-  /user/add name=mikrocata2selks password=xxxxxxxxxxxxx group=full (change password)

## Author

👤 **Giuseppe Trifilio**

* Website: https://github.com/angolo40/mikrocata2selks
* Github: [@angolo40](https://github.com/angolo40)
* Inspired by https://github.com/zzbe/mikrocata

## 🤝 Contributing

- Contributions, issues and feature requests are welcome!<br />Feel free to check [issues page](https://github.com/angolo40/mikrocata2selks).
## Show your support

- Give a ⭐️ if this project helped you!

***

_This README was generated with ❤️ by [readme-md-generator](https://github.com/kefranabg/readme-md-generator)_
