#!/bin/bash

### START EDIT SETTINGS

# Path where to install SELKS files
PATH_SELKS=$HOME/SELKS

# SETUP CONFIG SCRIPT
INSTALL_DUMMY_INTERFACE=true
INSTALL_MIKROCATA_SERVICE=true
INSTALL_SELKS=true

HOW_MANY_MIKROTIK=1  #Min 1 Mikrotik

### END EDIT SETTINGS

echo "--- Install required package ---"

apt-get install ca-certificates curl wget unzip  gnupg  lsb-release build-essential python3-pip git htop libpcap-dev -y
pip3 install pyinotify ujson requests librouteros

PATH_GIT_MIKROCATA=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
sed -i '/SELKS_CONTAINER_DATA_SURICATA_LOG=/c\SELKS_CONTAINER_DATA_SURICATA_LOG="'$PATH_SELKS'/docker/containers-data/suricata/logs/"' "$PATH_GIT_MIKROCATA/mikrocata.py"

HOW_MANY_MIKROTIK=$(( $HOW_MANY_MIKROTIK - 1 ))

docker -v
if [ $? -eq 128 ]; then
    echo "--- Installing docker ---"
    curl -fsSL https://get.docker.com/ | sh
else
    echo "--- Docker already installed ---"
fi

if $INSTALL_DUMMY_INTERFACE
then
    echo "--- Install packet sniffer interface ---"
    wget -P /opt https://github.com/thefloweringash/tzsp2pcap/archive/master.zip
    cd /opt
    unzip /opt/master.zip
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
fi

if $INSTALL_MIKROCATA_SERVICE
then

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

fi

if $INSTALL_SELKS
then
    echo "--- Start SELKS Installer ---"

    git clone https://github.com/StamusNetworks/SELKS.git $PATH_SELKS
    cd $PATH_SELKS/docker/

    num=0
    cmd=""
    cmd2=""
    while [ $num -le $HOW_MANY_MIKROTIK ]
    do
        cp $PATH_GIT_MIKROCATA/mikrocata2selks.yaml $PATH_SELKS/docker/containers-data/suricata/etc/
        cp $PATH_GIT_MIKROCATA/suricata.yaml $PATH_SELKS/docker/containers-data/suricata/etc/
        echo "include: mikrocata2selks.yaml" >> $PATH_SELKS/docker/containers-data/suricata/etc/suricata.yaml
        cmd2="$cmd2 -i tzsp$num"
        num=$(( $num + 1 ))
    done

    ./easy-setup.sh --non-interactive $cmd2 --iA --restart-mode always --es-memory 6G
    docker compose up -d

fi

echo "--- INSTALL COMPLETED ---"
echo "--- "
echo "--- "
    port=37008
    num=0
    while [ $num -le $HOW_MANY_MIKROTIK ]
    do
        echo "--- MIKROTIK $num"
        echo "--- Port: $port "
        echo "--- Local Interface: tzsp$num"
        echo "--- SERVICEs:"
        echo "--- --- ----: Mikrocata: Edit '/usr/local/bin/mikrocataTZSP$num.py' with your info and then reload service --> 'systemctl restart mikrocataTZSP$num.service'"
        echo "--- --- --- : Interface: TZSPreplay$port@tzsp$num.service  --> 'systemctl status TZSPreplay$port@tzsp$num.service'"
        echo "--- "
        num=$(( $num + 1 ))
        port=$(( $port + 1 ))
    done
echo "--- "
echo "--- "
echo "--- Remember to configure Mikrotik"
echo "--- "
