# Changelog - v2.3.0 (April 2025)

## Key Features

* **Advanced Whitelist Support:** Added full support for CIDR notations (e.g., `"10.0.0.0/8"`) in whitelist.
* **Emoji and Special Characters Handling:** Fixed issues with rules containing emojis or Unicode characters that caused crashes.
* **Debug Mode:** Added debug mode to facilitate troubleshooting.
* **Optimized Logging:** More concise and informative log messages in normal mode.
* **Critical Fixes:** Fixed bugs that caused some alerts to be skipped during processing.

## Technical Improvements

* Implemented `is_ip_in_whitelist()` function to correctly handle all forms of whitelist entries (exact IPs, prefixes, CIDR).
* Added `sanitize_text()` function to remove emojis and special characters from messages.
* Fixed double JSON parsing in `read_json()`.
* Replaced `break` with `continue` to ensure all alerts are processed.
* Improved logging system with categorization (`BLOCKED`, `UPDATED`, `ERROR`).
* Added full IPv6 support in whitelist management.

## Bug Fixes

* Fixed the issue that prevented recognition of CIDR format subnets in the whitelist.
* Fixed a bug that caused failure to process multiple events in a single cycle.
* Fixed crashes during processing of PAW rules containing emojis.

## Upgrade Instructions

1.  **Backup Existing Configurations**
    Backup all configuration files:

    ```bash
    sudo cp /usr/local/bin/mikrocataTZSP\*.py /usr/local/bin/mikrocataTZSP\*.py.bak
    sudo mkdir -p /var/lib/mikrocata/backup-$(date +%Y%m%d)
    sudo cp /var/lib/mikrocata/\* /var/lib/mikrocata/backup-$(date +%Y%m%d)/
    ```

2.  **Update Repository Files**

    ```bash
    cd /path/to/mikrocata2selks
    git pull
    ```

3.  **Install New Files**

    ```bash
    sudo cp mikrocata.py /usr/local/bin/mikrocataTZSP0.py
    ```

    Repeat for each instance if you have more than one Mikrotik router.

    ```bash
    sudo chmod +x /usr/local/bin/mikrocataTZSP0.py
    ```

4.  **Transfer Previous Configurations**
    Open the backup file and the new one to manually copy your custom settings:

    ```bash
    sudo nano /usr/local/bin/mikrocataTZSP0.py.bak
    sudo nano /usr/local/bin/mikrocataTZSP0.py
    ```

    Make sure to transfer all of the following settings:

    * Mikrotik credentials (`USERNAME`, `PASSWORD`, `ROUTER_IP`)
    * Telegram configuration
    * Whitelist IPs
    * SSL settings
    * LISTEN_INTERFACE
    * SELKS_CONTAINER_DATA_SURICATA_LOG

5.  **Restart Services**

    ```bash
    sudo systemctl restart mikrocataTZSP0.service
    ```

    Repeat for each instance if you have more than one Mikrotik router.

6.  **Verify Operation**
    ```bash
    sudo journalctl -u mikrocataTZSP0.service -f
    ```

## Important Notes for Upgrading

* **Debug Mode:** To activate debug mode for troubleshooting, set `DEBUG_MODE = True` in the file settings.
* **CIDR Whitelist:** The new version supports CIDR notations (e.g., `"10.0.0.0/8"`) in the whitelist.
* **IPv6 Compatibility:** The whitelist management now works correctly for both IPv4 and IPv6.

## What to Do in Case of Problems

If you encounter issues after upgrading:

* Check logs for any errors:
    ```bash
    sudo journalctl -u mikrocataTZSP0.service -n 100
    ```
* Enable debug mode for more detailed logs:
    ```bash
    sudo nano /usr/local/bin/mikrocataTZSP0.py
    ```
    Set `DEBUG_MODE = True`
    ```bash
    sudo systemctl restart mikrocataTZSP0.service
    ```
* If necessary, restore the previous version:
    ```bash
    sudo cp /usr/local/bin/mikrocataTZSP0.py.bak /usr/local/bin/mikrocataTZSP0.py
    sudo systemctl restart mikrocataTZSP0.service
    ```
* Report the issue on GitHub with relevant logs.

### v2.2.6 (March 4, 2025)
- **Performance:** Optimized Mikrotik address list saving to run every 5 minutes instead of on every alert
- **Stability:** Reduced router CPU load, particularly beneficial for high-traffic networks or routers with limited resources
- **System:** Added interval-based save mechanism with configurable timing (default: 300 seconds)

### v2.2.5 (January, 2025)
- **Security:** Fixed SSL certificate management issues
- **Reliability:** Improved handling of certificate validation

### v2.2.4 (December 2024)
- **Security:** Added support for self-signed certificates
- **Configuration:** Added new option `ALLOW_SELF_SIGNED_CERTS` for trusted environments

### v2.2.3 (July 2024)
- **Feature:** Added IPv6 support (thanks to contributor: floridan95)
- **Configuration:** Added `ENABLE_IPV6` option to enable/disable IPv6 blocking

### v2.2.2
- **Fix:** Resolved issue with Telegram notifications not being delivered properly

### v2.2.1
- **Bugfix:** Fixed script crash during Suricata logrotate operations
- **Stability:** Improved file handling for log rotation events

### v2.2
- **Compatibility:** Added support for Debian 12
- **System:** Updated installation scripts for newer package versions

### v2.1
- **Reliability:** Improved stability of the `read_json` function (thanks to contributor: bekhzad-khamidullaev)
- **Performance:** Better handling of malformed JSON data
