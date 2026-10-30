#!/bin/bash
# easyinstall.sh - A script to install Mikrocata for Clear NDR

install_dependencies() {
    echo "--- Install required package ---"
    apt-get install ca-certificates curl wget unzip tcpdump gnupg lsb-release build-essential python3-pip python3-pyinotify python3-ujson python3-librouteros python3-requests git htop libpcap-dev -y
}

install_base_components() {
    echo "--- Installing base components ---"
    PATH_GIT_MIKROCATA=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

    HOW_MANY_MIKROTIK=$(( $HOW_MANY_MIKROTIK - 1 ))

    if ! docker -v &>/dev/null; then
        echo "--- Installing docker ---"
        curl -fsSL https://get.docker.com/ | sh
    else
        echo "--- Docker already installed ---"
    fi

    echo "--- Install packet sniffer interface ---"
    wget -P /opt https://github.com/thefloweringash/tzsp2pcap/archive/master.zip
    cd /opt
    unzip -o /opt/master.zip
    cd /opt/tzsp2pcap-master/
    make
    make install

    wget -P /opt https://github.com/appneta/tcpreplay/releases/download/v4.4.2/tcpreplay-4.4.2.tar.gz
    cd /opt
    tar -xf /opt/tcpreplay-4.4.2.tar.gz -C /opt
    cd /opt/tcpreplay-4.4.2/
    ./configure
    make
    make install

    num=0
    while [ $num -le $HOW_MANY_MIKROTIK ]
    do
        echo "--- Creating interface ---"
        cp $PATH_GIT_MIKROCATA/tzsp.netdev /etc/systemd/network/tzsp$num.netdev
        cp $PATH_GIT_MIKROCATA/tzsp.network /etc/systemd/network/tzsp$num.network
        cmd="tzsp$num"
        sed -i "s/tzsp0/$cmd/g" /etc/systemd/network/tzsp$num.netdev
        sed -i "s/tzsp*/$cmd/g" /etc/systemd/network/tzsp$num.network
        cmd="25$num"
        sed -i "s/254/$cmd/g" /etc/systemd/network/tzsp$num.network
        num=$(( $num + 1 ))
    done
    systemctl enable systemd-networkd
    systemctl restart systemd-networkd

    port=37008
    num=0
    while [ $num -le $HOW_MANY_MIKROTIK ]
    do
        echo "--- Create service for interface dummy ---"
        cp $PATH_GIT_MIKROCATA/TZSPreplay@.service /etc/systemd/system/TZSPreplay$port@.service
        cmd="tzsp2pcap -p $port"
        sed -i "s/tzsp2pcap/$cmd/g" /etc/systemd/system/TZSPreplay$port@.service
        systemctl enable --now TZSPreplay$port@tzsp$num.service
        num=$(( $num + 1 ))
        port=$(( $port + 1 ))
    done

    num=0
    while [ $num -le $HOW_MANY_MIKROTIK ]
    do
        echo "--- Installing Mikrocata and his service ---"
        cp $PATH_GIT_MIKROCATA/mikrocata.py /usr/local/bin/mikrocataTZSP$num.py
        chmod +x /usr/local/bin/mikrocataTZSP$num.py
        sed -i "s/tzsp0/tzsp$num/g" /usr/local/bin/mikrocataTZSP$num.py
        mkdir -p /var/lib/mikrocata
        touch /var/lib/mikrocata/savelists-tzsp$num.json
        touch /var/lib/mikrocata/uptime-tzsp$num.bookmark
        touch /var/lib/mikrocata/ignore-tzsp$num.conf
        cp $PATH_GIT_MIKROCATA/mikrocata.service /etc/systemd/system/mikrocataTZSP$num.service
        cmd="mikrocataTZSP$num.py"
        sed -i "s/mikrocata.py/$cmd/g" /etc/systemd/system/mikrocataTZSP$num.service
        systemctl enable --now mikrocataTZSP$num.service
        num=$(( $num + 1 ))
    done
    cd $PATH_GIT_MIKROCATA
}

install_clear_ndr() {
    echo "--- Clear NDR Installer ---"
    
    # Validate Clear NDR installation path
    while true; do
        read -e -p "Enter the installation path for Clear NDR: " -i "/root/NDR" PATH_NDR
        if [[ -n "$PATH_NDR" && "$PATH_NDR" =~ ^[a-zA-Z0-9/_.-]+$ ]]; then
            break
        else
            echo "Error: Please enter a valid path (no spaces or special characters except /, -, ., _)"
        fi
    done
    mkdir -p $PATH_NDR
    
    echo "--- DISCLAIMER: Only one Mikrotik device is officially supported. ---"
    echo "--- Multiple Mikrotik devices can be configured manually (will be documented in future updates). ---"
    sleep 3
    HOW_MANY_MIKROTIK=1
    
    PATH_GIT_MIKROCATA=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
    sed -i '/NDR_SURICATA_LOG_PATH=/c\NDR_SURICATA_LOG_PATH="'$PATH_NDR'/config/containers-data/suricata/logs/"' "$PATH_GIT_MIKROCATA/mikrocata.py"
    
    install_dependencies
    install_base_components

    echo "--- Installing Stamus Clear NDR ---"
    wget https://dl.clearndr.io/stamusctl-linux-amd64 -O /usr/local/bin/stamusctl
    chmod +x /usr/local/bin/stamusctl

    cd $PATH_NDR
    stamusctl compose init suricata.interfaces=tzsp0
    stamusctl config set suricata.interfaces=tzsp0
    stamusctl compose up -d
    
    echo "--- Clear NDR INSTALL COMPLETED ---"
    print_summary
}

uninstall() {
    echo "--- Uninstalling all components ---"
    read -p "Are you sure you want to uninstall all components? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi

    # Clear NDR uninstall (SELKS is no longer supported)
    echo "This will uninstall Clear NDR."
    uninstall_choice=2

    # Detect interfaces (common step)
    echo "--- Detecting number of configured interfaces ---"
    HOW_MANY_MIKROTIK=$(ls /etc/systemd/network/tzsp*.netdev 2>/dev/null | wc -l)
    if [ "$HOW_MANY_MIKROTIK" -eq 0 ]; then
        echo "No configured interfaces found. Nothing to do for interfaces and services."
    else
        echo "Found $HOW_MANY_MIKROTIK interfaces."
        HOW_MANY_MIKROTIK_LOOPS=$(( $HOW_MANY_MIKROTIK - 1 ))

        # Stop and disable services
        port=37008
        num=0
        while [ $num -le $HOW_MANY_MIKROTIK_LOOPS ]; do
            echo "--- Stopping and disabling services for interface tzsp$num ---"
            systemctl disable --now mikrocataTZSP$num.service
            systemctl disable --now TZSPreplay$port@tzsp$num.service
            num=$(( $num + 1 ))
            port=$(( $port + 1 ))
        done

        # Remove files
        echo "--- Removing system files ---"
        num=0
        port=37008
        while [ $num -le $HOW_MANY_MIKROTIK_LOOPS ]; do
            rm -f /usr/local/bin/mikrocataTZSP$num.py
            rm -f /etc/systemd/system/mikrocataTZSP$num.service
            rm -f /etc/systemd/system/TZSPreplay$port@.service
            rm -f /etc/systemd/network/tzsp$num.netdev
            rm -f /etc/systemd/network/tzsp$num.network
            num=$(( $num + 1 ))
            port=$(( $port + 1 ))
        done
    fi

    rm -rf /var/lib/mikrocata

    # Uninstall Clear NDR with path validation
    while true; do
        read -e -p "Enter the installation path for Clear NDR that was used: " -i "/root/NDR" PATH_NDR
        if [[ -n "$PATH_NDR" && "$PATH_NDR" =~ ^[a-zA-Z0-9/_.-]+$ ]]; then
            break
        else
            echo "Error: Please enter a valid path (no spaces or special characters except /, -, ., _)"
        fi
    done
    if [ -d "$PATH_NDR" ]; then
        echo "--- Removing Clear NDR from $PATH_NDR ---"
        cd $PATH_NDR
        stamusctl compose down
        cd ..
        rm -rf $PATH_NDR
    else
        echo "--- Clear NDR directory not found at $PATH_NDR, skipping ---"
    fi

    if [ -f "/usr/local/bin/stamusctl" ]; then
        rm -f /usr/local/bin/stamusctl
    fi

    # Remove common downloaded tools
    echo "--- Removing downloaded tools ---"
    rm -rf /opt/tzsp2pcap-master
    rm -f /opt/master.zip
    rm -rf /opt/tcpreplay-4.4.2
    rm -f /opt/tcpreplay-4.4.2.tar.gz

    # Reload systemd
    echo "--- Reloading systemd ---"
    systemctl daemon-reload
    systemctl restart systemd-networkd

    echo "--- UNINSTALL COMPLETED ---"
}

print_summary() {
    echo "--- "
    echo "--- "
    echo "#################################################################"
    echo "---            POST-INSTALLATION CONFIGURATION                ---"
    echo "#################################################################"
    echo ""
    
    port=37008
    num=0
    # This variable is expected to be decremented by install_base_components
    while [ $num -le $HOW_MANY_MIKROTIK ]
    do
        echo "--- MIKROTIK $num CONFIGURATION ---"
        echo "1. EDIT THE PYTHON SCRIPT:"
        echo "   - File: /usr/local/bin/mikrocataTZSP$num.py"
        echo "   - Set your Mikrotik IP, Username, and Password."
        echo "   - Set your Telegram Bot Token and Chat ID."
        echo ""
        echo "2. RESTART THE MIKROCATA SERVICE:"
        echo "   systemctl restart mikrocataTZSP$num.service"
        echo ""
        echo "3. CHECK SERVICE STATUS:"
        echo "   - Mikrocata: systemctl status mikrocataTZSP$num.service"
        echo "   - Interface: systemctl status TZSPreplay$port@tzsp$num.service"
        echo ""
        echo "-----------------------------------------------------------------"
        num=$(( $num + 1 ))
        port=$(( $port + 1 ))
    done
    
    echo "--- MIKROTIK ROUTER CONFIGURATION ---"
    echo "Remember to configure the following on your Mikrotik router:"
    echo "1. Enable the Sniffer to stream traffic to this server's IP on the correct port."
    echo "2. Add the Firewall rules to block IPs found by Suricata."
    echo "3. Enable the API service and create a user for Mikrocata."
    echo "(See README.md for the exact commands)"
    echo ""
    echo "#################################################################"
    echo ""
}

# --- Main Menu ---
while true; do
    clear
    echo "========================================"
    echo "   Mikrocata Clear NDR Installer"
    echo "========================================"
    echo "1. Install Clear NDR"
    echo "   (A free, open-source NDR solution.)"
    echo "   NOTE: SELKS repository has been removed by Stamus Networks."
    echo "   Only Clear NDR is now supported."
    echo ""
    echo "2. Uninstall"
    echo "3. Exit"
    echo "========================================"
    read -p "Enter your choice [1-3]: " choice

    case $choice in
        1)
            install_clear_ndr
            break
            ;;
        2)
            uninstall
            break
            ;;
        3)
            exit 0
            ;;
        *)
            echo "Error: Please enter a number between 1 and 3"
            sleep 2
            ;;
    esac
done
