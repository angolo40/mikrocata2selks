<h1 align="center">Welcome to Mikrocata2SELKS 👋</h1>
<p>
  <img alt="Version" src="https://img.shields.io/badge/version-2.2.4-blue.svg?cacheSeconds=2592000" />
  <a href="https://github.com/angolo40/mikrocata2selks" target="_blank">
    <img alt="License: MIT" src="https://img.shields.io/github/license/angolo40/Mikrocata2SELKS" />
  </a>
</p>

## 📋 Introduction

Mikrocata2SELKS is a streamlined solution for integrating Mikrotik devices with Suricata IDS/IPS for packet analysis.
It automates the setup process and enables efficient network traffic monitoring and threat detection.
The script is compatible with latest SELKS 10.

```mermaid
graph LR
    A[Mikrotik Router] -->|TZSP Traffic| B[Mikrocata2SELKS]
    B -->|Analysis| C[Suricata IDS/IPS]
    C -->|Alerts| D[Telegram Notifications]
    C -->|Blocks| E[Firewall Rules]
```

**Minimum Requirements:**
- 4 CPU cores
- 10 GB of free RAM
- Minimum 10 GB of free disk space (actual disk usage will mainly depend on the number of rules and the amount of traffic on the network - 200GB+ SSD grade recommended).

## 🚀 Installation

1. Set up a fresh Debian 12 installation on a dedicated machine (server or VM).
2. Log in as root.
3. Install Git: `apt install git`.
4. Clone this repository: `git clone https://github.com/angolo40/mikrocata2selks.git`.
5. Edit `easyinstall.sh` with the path where to install SELKS and the number of Mikrotik devices to handle.
6. Run `./easyinstall.sh`.
7. Wait....
8. Once finished, edit `/usr/local/bin/mikrocataTZSP0.py` with your Mikrotik and Telegram parameters, then reload the service with `systemctl restart mikrocataTZSP0.service`.
9. Configure your Mikrotik devices.

## 📡 Mikrotik Setup

1. Enable sniffer:
    ```sh
    /tool/sniffer/set filter-stream=yes streaming-enabled=yes streaming-server=[YOURDEBIANIP]:37008
    /tool/sniffer/start
    ```
2. Add firewall rules:
    ```sh
    /ip/firewall/raw/add action=drop chain=prerouting comment="IPS-drop_in_bad_traffic" src-address-list=Suricata
    /ip/firewall/raw/add action=drop chain=prerouting comment="IPS-drop_out_bad_traffic" dst-address-list=Suricata
    /ipv6/firewall/raw/add action=drop chain=prerouting comment="IPS-drop_in_bad_traffic" src-address-list=Suricata
    /ipv6/firewall/raw/add action=drop chain=prerouting comment="IPS-drop_out_bad_traffic" dst-address-list=Suricata
    ```
3. Enable Mikrotik API:
    ```sh
    /ip/service/set api-ssl address=[DEBIANIP] enabled=yes
    ```
4. Add Mikrocata user in Mikrotik:
    ```sh
    /user/add name=mikrocata2selks password=xxxxxxxxxxxxx group=full (change password)
    ```

## 🛠️ Handling Multiple Mikrotik Devices

By configuring the `easyinstall.sh` file to manage more than one Mikrotik device, the setup script will automatically create dedicated dummy interfaces and corresponding Mikrocata services for each device on the Debian machine.

- Example configuration:
    - For Mikrotik0: Creates the `tzsp0` interface on port `37008` and the script `/usr/local/bin/mikrocataTZSP0.py`.
    - For Mikrotik1: Creates the `tzsp1` interface on port `37009` and the script `/usr/local/bin/mikrocataTZSP1.py`.
    - For Mikrotik2: Creates the `tzsp2` interface on port `37010` and the script `/usr/local/bin/mikrocataTZSP2.py`.

You will need to edit each script with the specific Mikrotik values and enable the sniffer on each Mikrotik device to send data to the corresponding port.
The system architecture for handling multiple Mikrotik devices is designed to be modular and scalable. Here's a visual representation of how the system works:

```mermaid
flowchart TD
    subgraph Mikrotik_Devices
        M0[Mikrotik0 Port:37008]
        M1[Mikrotik1 Port:37009]
        M2[Mikrotik2 Port:37010]
    end

    subgraph Debian_Server ["Debian Server (SELKS)"]
        subgraph Interfaces
            I0[Interface:tzsp0 Port:37008]
            I1[Interface:tzsp1 Port:37009]
            I2[Interface:tzsp2 Port:37010]
        end

        subgraph Mikrocata_Services
            S0[mikrocataTZSP0.py]
            S1[mikrocataTZSP1.py]
            S2[mikrocataTZSP2.py]
        end

        subgraph Analysis
            suricata[Suricata IDS/IPS\nDocker Container]
            telegram[Telegram\nNotifications]
        end
    end

    M0 -->|TZSP Traffic| I0
    M1 -->|TZSP Traffic| I1
    M2 -->|TZSP Traffic| I2

    I0 -->|Packet Analysis| S0
    I1 -->|Packet Analysis| S1
    I2 -->|Packet Analysis| S2

    S0 -->|Alerts| suricata
    S1 -->|Alerts| suricata
    S2 -->|Alerts| suricata

    suricata -->|Block Notifications| telegram
    
    style Debian_Server fill:#f5f5f5,stroke:#333,stroke-width:2px
    style Mikrotik_Devices fill:#e1f5fe,stroke:#333,stroke-width:2px
    style Analysis fill:#e8f5e9,stroke:#333,stroke-width:2px
```

## 💡 Features

- Installs Docker and Docker Compose.
- Installs Python.
- Downloads and installs SELKS repository (https://github.com/StamusNetworks/SELKS).
- Downloads and installs Mikrocata.
- Installs TZSP interface.
- Enables notifications over Telegram when an IP is blocked.

## 🔄 Changelog
### 2.2.4
- Manage Self-Signed Certificate

### 2.2.3
- Added IPV6Support (thanks floridan95)
  
### 2.2.2
- Fixed telegram notification issue.

### 2.2.1
- Fixed bug causing `mikrocata.py` script crash during Suricata logrotate.

### 2.2
- Added compatibility with Debian 12.

### 2.1
- Improved stability of the `read_json` function (thanks to bekhzad-khamidullaev).

## 🔧 Troubleshooting

- Check if packets are arriving at the VM from Mikrotik through the dummy interface:
    ```sh
    tcpdump -i tzsp0
    ```
- Check if mikrocata service and tzsp0 interface are up and running:
    ```sh
    systemctl status mikrocataTZSP0.service
    systemctl status TZSPreplay37008@tzsp0.service
    ```
- Check if Suricata Docker container is up and running:
    ```sh
    docker logs -f suricata
    ```

## 📝 Notes
- Default account for SELKS:
    - URL: `https://[YOURDEBIANIP]`
    - Username: `selks-user`
    - Password: `selks-user`

## 👤 Author

**Giuseppe Trifilio**

- [Website](https://github.com/angolo40/mikrocata2selks)
- [GitHub](https://github.com/angolo40)

Inspired by [zzbe/mikrocata](https://github.com/zzbe/mikrocata).

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Check the [issues page](https://github.com/angolo40/mikrocata2selks).

## 🌟 Show Your Support

Give a ⭐️ if this project helped you!

- **XMR**: `87LLkcvwm7JUZAVjusKsnwNRPfhegxe73X7X3mWXDPMnTBCb6JDFnspbN8qdKZA6StHXqnJxMp3VgRK7DcS2sgnW3wH7Xhw`
