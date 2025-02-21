import aiohttp
import xml.etree.ElementTree as ET
import re
import base64
import asyncio
import ssl


class ReadyNASAPI:
    def __init__(self, host, username, password, use_ssl=False, ignore_ssl_errors=True):
        """Initialize API connection with optional SSL settings."""
        self.host = host
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.ignore_ssl_errors = ignore_ssl_errors

        # Store protocol for consistent use
        self.protocol = "https" if self.use_ssl else "http"
        self.url = f"{self.protocol}://{self.host}/dbbroker"
        self.admin_url = f"{self.protocol}://{self.host}/admin/"
        self.csrf_token = None
        self.session = None

    async def _encode_credentials(self):
        """Encode username and password for Basic Authentication."""
        credentials = f"{self.username}:{self.password}"
        return base64.b64encode(credentials.encode()).decode()

    async def _get_csrf_token(self):
        """Fetch CSRF token asynchronously."""
        print("🔍 Fetching CSRF token...")

        headers = {
            "Authorization": f"Basic {await self._encode_credentials()}",
            "User-Agent": "HomeAssistant-ReadyNAS",
        }

        ssl_context = ssl.SSLContext()
        if self.ignore_ssl_errors:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    self.admin_url, headers=headers, ssl=ssl_context
                ) as response:
                    if response.status == 401:
                        print("❌ 401 Unauthorized - Check username/password.")
                        return None

                    response_text = await response.text()

                    match = re.search(
                        r'csrfInsert\("csrfpId", "([^"]+)"\);', response_text
                    )
                    if match:
                        self.csrf_token = match.group(1)
                        print(f"✅ CSRF Token Retrieved: {self.csrf_token}")
                        return self.csrf_token
                    else:
                        print("❌ CSRF token not found in response!")
                        return None
            except aiohttp.ClientError as e:
                print(f"❌ Error fetching CSRF token: {e}")
                return None

    async def get_health_info(self):
        """Retrieve system health info asynchronously."""
        print("🚀 DEBUG: Entering `get_health_info()` function")

        # Get basic health info first
        health_data = {}

        # Get disk and system info
        basic_health = await self._get_basic_health()
        if basic_health:
            health_data.update(basic_health)

        # Get volume info
        volume_data = await self.get_volume_info()
        if volume_data:
            print(f"📊 Volume data retrieved: {volume_data}")
            health_data["volumes"] = volume_data
        else:
            print("❌ No volume data retrieved!")

        return health_data

    async def parse_health_info(self, xml_data):
        """Parse ReadyNAS XML health data and extract key metrics asynchronously."""
        root = ET.fromstring(xml_data)

        parsed_data = {"fan_speed": None, "cpu_temp": None, "disks": []}

        for enclosure in root.findall(".//Enclosure_Health"):
            temp_element = enclosure.find(".//Temperature")
            if temp_element is not None:
                parsed_data["cpu_temp"] = int(temp_element.find("temp_value").text)

            fan_element = enclosure.find(".//Fan")
            if fan_element is not None:
                parsed_data["fan_speed"] = int(fan_element.find("fan_speed").text)

            for disk in enclosure.findall(".//Disk"):
                disk_data = {
                    "model": disk.find("disk_model").text
                    if disk.find("disk_model") is not None
                    else "Unknown",
                    "temperature": int(disk.find("disk_temperature").text)
                    if disk.find("disk_temperature") is not None
                    else None,
                    "status": disk.find("disk_status").text
                    if disk.find("disk_status") is not None
                    else "Unknown",
                    "capacity": int(disk.find("disk_capacity").text)
                    if disk.find("disk_capacity") is not None
                    else None,
                }
                parsed_data["disks"].append(disk_data)

        return parsed_data

    async def _get_basic_health(self):
        """Get basic health information from the NAS."""
        print("🚀 DEBUG: Entering `_get_basic_health()` function")
        print(f"🌐 Using {self.protocol.upper()} protocol")

        # Add retry logic
        retries = 3
        while retries > 0:
            if not self.csrf_token:
                print("🔍 No CSRF token found, fetching a new one...")
                if not await self._get_csrf_token():
                    print("❌ Failed to get CSRF token")
                    retries -= 1
                    continue

            headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Authorization": f"Basic {await self._encode_credentials()}",
                "csrfpId": self.csrf_token,
            }

            xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
            <xs:nml xmlns:xs="http://www.netgear.com/protocol/transaction/NMLSchema-0.9" xmlns="urn:netgear:nas:readynasd" src="dpv_1739644512000" dst="nas">
                <xs:transaction id="njl_id_2912">
                    <xs:get id="njl_id_2911" resource-id="HealthInfo" resource-type="Health_Collection" />
                </xs:transaction>
            </xs:nml>"""

            ssl_context = ssl.SSLContext()
            if self.ignore_ssl_errors:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            async with aiohttp.ClientSession() as session:
                try:
                    print(f"🌐 Making request to URL: {self.url}")
                    async with session.post(
                        self.url,
                        headers=headers,
                        data=xml_payload,
                        ssl=ssl_context,
                        timeout=30,
                    ) as response:
                        print(f"📡 Response status: {response.status}")
                        print(f"📡 Response headers: {response.headers}")

                        if response.status == 401:
                            print("❌ 401 Unauthorized - Session expired, retrying...")
                            self.csrf_token = None
                            retries -= 1
                            continue

                        response_text = await response.text()
                        if not response_text or response_text.isspace():
                            print("❌ Empty response received!")
                            retries -= 1
                            await asyncio.sleep(1)  # Wait before retry
                            continue

                        print(f"📜 Full XML Response: {response_text}")

                        try:
                            data = await self.parse_health_info(response_text)
                            if data:
                                return data
                        except ET.ParseError as e:
                            print(f"❌ XML parsing error: {e}")
                            print(
                                f"❌ Problematic XML content: {response_text[:200]}..."
                            )

                    retries -= 1
                    await asyncio.sleep(1)  # Wait before retry

                except aiohttp.ClientError as e:
                    print(f"❌ Error fetching ReadyNAS health info: {e}")
                    retries -= 1
                    await asyncio.sleep(1)  # Wait before retry
                    continue

            print(f"⚠️ Retry attempt {3 - retries} failed")

        print("❌ All retry attempts failed")
        return None

    # Add this method to the ReadyNASAPI class
    async def get_volume_info(self):
        """Retrieve volume info asynchronously."""
        print("🚀 DEBUG: Entering `get_volume_info()` function")
        print(f"🌐 Using {self.protocol.upper()} protocol")

        retries = 3
        while retries > 0:
            if not self.csrf_token:
                print("🔍 No CSRF token found, fetching a new one...")
                if not await self._get_csrf_token():
                    print("❌ Failed to get CSRF token")
                    retries -= 1
                    continue

            headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Authorization": f"Basic {await self._encode_credentials()}",
                "csrfpId": self.csrf_token,
            }

            xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
            <xs:nml xmlns:xs="http://www.netgear.com/protocol/transaction/NMLSchema-0.9" xmlns="urn:netgear:nas:readynasd" src="dpv_1740071202000" dst="nas">
                <xs:transaction id="njl_id_281">
                    <xs:get id="njl_id_280" resource-id="Volumes" resource-type="Volume_Collection"/>
                </xs:transaction>
            </xs:nml>"""

            ssl_context = ssl.SSLContext()
            if self.ignore_ssl_errors:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            async with aiohttp.ClientSession() as session:
                try:
                    print(f"🌐 Making request to URL: {self.url}")
                    async with session.post(
                        self.url,
                        headers=headers,
                        data=xml_payload,
                        ssl=ssl_context,
                        timeout=30,
                    ) as response:
                        if response.status == 401:
                            print("❌ 401 Unauthorized - Session expired, retrying...")
                            self.csrf_token = None
                            retries -= 1
                            continue

                        response_text = await response.text()
                        if not response_text or response_text.isspace():
                            print("❌ Empty response received!")
                            retries -= 1
                            await asyncio.sleep(1)
                            continue

                        print(f"📜 Full XML Response: {response_text}")

                        try:
                            data = await self.parse_volume_info(response_text)
                            if data:
                                return data
                        except ET.ParseError as e:
                            print(f"❌ XML parsing error: {e}")
                            print(
                                f"❌ Problematic XML content: {response_text[:200]}..."
                            )

                    retries -= 1
                    await asyncio.sleep(1)

                except aiohttp.ClientError as e:
                    print(f"❌ Error fetching ReadyNAS volume info: {e}")
                    retries -= 1
                    await asyncio.sleep(1)
                    continue

        print("❌ All retry attempts failed")
        return None

    async def parse_volume_info(self, xml_data):
        """Parse ReadyNAS XML volume data and extract metrics asynchronously."""
        root = ET.fromstring(xml_data)
        volumes = []

        for volume in root.findall(".//Volume"):
            props = volume.find("Property_List")
            if props is not None:
                volume_data = {
                    "name": props.findtext("Volume_Name", "Unknown"),
                    "raid_level": props.findtext("RAID_Level", "Unknown"),
                    "health": props.findtext("Health", "Unknown"),
                    "capacity_gb": round(
                        float(props.findtext("Capacity", "0")) / (1024 * 1024), 2
                    ),
                    "free_gb": round(
                        float(props.findtext("Free", "0")) / (1024 * 1024), 2
                    ),
                    "used_gb": round(
                        float(props.findtext("DataUsedKB", "0")) / 1024, 2
                    ),
                    "encryption_enabled": props.find("Encryption").get("enabled", "0")
                    == "1",
                    "auto_expand": props.findtext("AutoExpand", "off") == "on",
                    "quota_enabled": props.findtext("Quota", "off") == "on",
                }

                # Calculate used percentage
                if volume_data["capacity_gb"] > 0:
                    volume_data["used_percentage"] = round(
                        (volume_data["used_gb"] / volume_data["capacity_gb"]) * 100, 1
                    )
                else:
                    volume_data["used_percentage"] = 0

                # Get RAID configuration
                raid_configs = []
                for raid in volume.findall(".//RAID"):
                    raid_config = {
                        "level": raid.get("LEVEL", "Unknown"),
                        "id": raid.get("ID", "Unknown"),
                        "disks": [
                            disk.get("resource-id") for disk in raid.findall("Disk")
                        ],
                    }
                    raid_configs.append(raid_config)

                volume_data["raid_configs"] = raid_configs
                volumes.append(volume_data)

        return volumes

    async def shutdown_nas(self):
        """Shutdown the NAS system."""
        print("🚀 DEBUG: Entering `shutdown_nas()` function")

        if not self.csrf_token:
            print("🔍 No CSRF token found, fetching a new one...")
            await self._get_csrf_token()

        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Authorization": f"Basic {await self._encode_credentials()}",
            "csrfpId": self.csrf_token,
        }

        xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
        <xs:nml xmlns:xs="http://www.netgear.com/protocol/transaction/NMLSchema-0.9" xmlns="urn:netgear:nas:readynasd" src="dpv_1584484996000" dst="nas">
            <xs:transaction id="njl_id_1628">
                <xs:custom id="njl_id_1628" name="Halt" resource-id="Shutdown" resource-type="System">
                    <Shutdown halt="true" fsck="false"/>
                </xs:custom>
            </xs:transaction>
        </xs:nml>"""

        ssl_context = ssl.SSLContext()
        if self.ignore_ssl_errors:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.url, headers=headers, data=xml_payload, ssl=ssl_context
                ) as response:
                    if response.status == 401:
                        print("❌ 401 Unauthorized - Session expired, retrying...")
                        await self._get_csrf_token()
                        return False

                    if response.status == 200:
                        print("✅ Shutdown command sent successfully")
                        return True
                    else:
                        print(
                            f"❌ Failed to send shutdown command. Status: {response.status}"
                        )
                        return False

            except aiohttp.ClientError as e:
                print(f"❌ Error sending shutdown command: {e}")
                return False
