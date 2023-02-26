#!/bin/bash

### START EDIT SETTINGS

# Path where to install SELKS files
PATH_SELKS=$HOME/SELKS

# SETUP CONFIG SCRIPT
INSTALL_DUMMY_INTERFACE=true
INSTALL_MIKROCATA_SERVICE=true
INSTALL_SELKS=true

### END EDIT SETTINGS

echo "--- Install required package ---"

apt-get install ca-certificates curl wget unzip  gnupg  lsb-release build-essential python3-pip git htop libpcap-dev -y
pip3 install pyinotify ujson requests librouteros

PATH_GIT_MIKROCATA=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
sed -i '/SELKS_CONTAINER_DATA_SURICATA_LOG=/c\SELKS_CONTAINER_DATA_SURICATA_LOG="'$PATH_SELKS'/docker/containers-data/suricata/logs/"' "$PATH_GIT_MIKROCATA/mikrocata.py"

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

    echo "--- Creating interface ---"
    cp $PATH_GIT_MIKROCATA/tzsp.netdev /etc/systemd/network/
    cp $PATH_GIT_MIKROCATA/tzsp.network /etc/systemd/network/
    systemctl enable systemd-networkd
    systemctl restart systemd-networkd

    echo "--- Create service for interface dummy ---"
    cp $PATH_GIT_MIKROCATA/TZSPreplay@.service /etc/systemd/system/
    systemctl enable --now TZSPreplay@tzsp0.service
fi

if $INSTALL_MIKROCATA_SERVICE
then
    echo "--- Installing Mikrocata and his service ---"
    cp $PATH_GIT_MIKROCATA/mikrocata.py /usr/local/bin/
    chmod +x /usr/local/bin/mikrocata.py
    mkdir -p /var/lib/mikrocata
    touch /var/lib/mikrocata/savelists.json
    touch /var/lib/mikrocata/uptime.bookmark
    touch /var/lib/mikrocata/ignore.conf
    cp $PATH_GIT_MIKROCATA/mikrocata.service /etc/systemd/system/
    systemctl enable --now mikrocata.service
fi

if $INSTALL_SELKS
then
    echo "--- Start SELKS Installer ---"

    git clone https://github.com/StamusNetworks/SELKS.git $PATH_SELKS
    cd $PATH_SELKS/docker/
    ./easy-setup.sh --non-interactive -i tzsp0 --iA --restart-mode always --es-memory 6G
    cp $PATH_GIT_MIKROCATA/mikrocata2selks.yaml $PATH_SELKS/docker/containers-data/suricata/etc/
    docker-compose up -d
    echo "include: mikrocata2selks.yaml" >> $PATH_SELKS/docker/containers-data/suricata/etc/suricata.yaml
    docker restart suricata


fi

echo "--- INSTALL COMPLETED ---"
echo "--- "
echo "--- "
echo "--- Edit '/usr/local/bin/mikrocata.py' with your info and then reload service with 'systemctl restart mikrocata.service'"
echo "--- Remember to confiure Mikrotik"
echo "--- "
