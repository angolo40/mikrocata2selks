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

## Function
- Install Docker and Docker compose
- Install Python
- Download SELKS repo
- Download mikrocata repo
- Install TZSP interface
- Notification over Telegram when IP is blocked

## Install

```sh
./easyinstall.sh
```

## Usage

- Download this git repo 
- Edit easyinstall.sh with your parameters
- Edit microcata.py with your parameters
- Remember to enable packet sniffer on Mikrotik
- Enable blocking rule on Mikrotik

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
