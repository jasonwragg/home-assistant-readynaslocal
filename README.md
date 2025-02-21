# ReadyNAS Local Integration for Home Assistant

![HA Integration](https://img.shields.io/badge/Home%20Assistant-Custom%20Component-blue)

A Home Assistant custom integration for NETGEAR ReadyNAS devices. Control and monitor your NAS directly through Home Assistant.

## Features

- Monitor disk status and temperature
- Track volume health and usage
- View system information (CPU temperature, fan speed)
- Shutdown capability via service call
- Real-time status updates
- SSL support with verification options

## Installation

### **HACS Installation**
1. Open **HACS** in Home Assistant.
2. Go to **Integrations** → Click **+**.
3. Add this repository: `https://github.com/jasonwragg/home-assistant-readynaslocal`
4. Install and restart Home Assistant.

### **Manual Installation**
1. Copy the `readynaslocal` folder to your Home Assistant `custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings** → **Devices & Services** → Add `ReadyNAS Local`.

### Configuration

The integration needs the following information:
- Host: IP address or hostname of your ReadyNAS
- Username: Admin username for the ReadyNAS
- Password: Admin password
- SSL Options: Enable/disable SSL verification

## Entities Created

### Sensors
- CPU Temperature
- Fan Speed
- Disk Status (for each disk)
  - Temperature
  - Status
  - Model information
- Volume Information
  - Health status
  - Capacity
  - Usage statistics
  - RAID configuration

### Buttons
- Shutdown: Safely power off your ReadyNAS

## Support

Please [open an issue](https://github.com/jasonwragg/readynaslocal/issues/new) for support.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is not affiliated with or endorsed by NETGEAR.
