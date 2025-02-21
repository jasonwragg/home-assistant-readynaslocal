# ReadyNAS Local Integration for Home Assistant

A Home Assistant custom integration for NETGEAR ReadyNAS devices. Control and monitor your NAS directly through Home Assistant.

## Features

- Monitor disk status and temperature
- Track volume health and usage
- View system information (CPU temperature, fan speed)
- Shutdown capability via service call
- Real-time status updates
- SSL support with verification options

## Installation

### Manual Installation

1. Copy the `readynaslocal` folder to your `custom_components` directory in your Home Assistant configuration directory.
   ```bash
   cp -r readynaslocal /path/to/your/config/custom_components/
   ```

2. Restart Home Assistant
3. Add the integration through the Home Assistant UI:
   - Navigate to **Settings** > **Devices & Services**
   - Click **+ ADD INTEGRATION**
   - Search for "ReadyNAS"

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
