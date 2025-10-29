"""Service for handling IP location detection and geo-location data."""

import logging
from typing import NamedTuple, Optional

import requests

logger = logging.getLogger(__name__)


class LocationInfo(NamedTuple):
    """Container for location information."""
    ip: str
    latitude_longitude: str
    city_state: str
    timezone: str
    latitude: str
    longitude: str


class LocationService:
    """Service for detecting user location from IP addresses."""

    IP_API_URL = "http://ip-api.com/json/{}"
    IPIFY_API_URL = "https://api.ipify.org?format=json"

    @classmethod
    def get_location_info(
        cls,
        x_forwarded_for: Optional[str] = None,
        cf_connecting_ip: Optional[str] = None
    ) -> LocationInfo:
        """
        Get location information from request headers.

        Args:
            x_forwarded_for: X-Forwarded-For header value
            cf_connecting_ip: CF-Connecting-IP header value (Cloudflare)

        Returns:
            LocationInfo containing IP, coordinates, city/state, and timezone
        """
        try:
            # Determine the IP address to use
            ip = cls._determine_ip_address(x_forwarded_for, cf_connecting_ip)

            # Get location data from IP
            return cls._get_location_from_ip(ip)

        except Exception as e:
            logger.error(f"Error getting location info: {e}")
            return cls._get_fallback_location_info(x_forwarded_for or cf_connecting_ip)

    @classmethod
    def _determine_ip_address(
        cls,
        x_forwarded_for: Optional[str],
        cf_connecting_ip: Optional[str]
    ) -> str:
        """Determine the actual IP address from headers or external service."""
        if x_forwarded_for:
            # Handle comma-separated IPs, take the first one
            ip = x_forwarded_for.split(",")[0].strip()
        elif cf_connecting_ip:
            # Handle comma-separated IPs, take the first one
            ip = cf_connecting_ip.split(",")[0].strip()
        else:
            # Fallback to external IP detection
            response = requests.get(cls.IPIFY_API_URL, timeout=5)
            ip = response.json()["ip"]

        return ip

    @classmethod
    def _get_location_from_ip(cls, ip: str) -> LocationInfo:
        """Get location information from an IP address using ip-api.com."""
        response = requests.get(cls.IP_API_URL.format(ip), timeout=5)
        data = response.json()

        if data.get("status") == "success":
            latitude_longitude = f"{data['lat']},{data['lon']}"
            city_state = f"{data['city']}, {data['regionName']}"
            timezone = data["timezone"]
            actual_ip = data["query"]

            return LocationInfo(
                ip=actual_ip,
                latitude_longitude=latitude_longitude,
                city_state=city_state,
                timezone=timezone,
                latitude=data["lat"],
                longitude=data["lon"]
            )
        else:
            logger.warning(f"IP API failed for {ip}: {data}")
            return LocationInfo(
                ip=ip,
                latitude_longitude="unknown",
                city_state="unknown",
                timezone="unknown",
                latitude="unknown",
                longitude="unknown"
            )

    @classmethod
    def _get_fallback_location_info(cls, fallback_ip: Optional[str]) -> LocationInfo:
        """Create fallback location info when all else fails."""
        return LocationInfo(
            ip=fallback_ip or "",
            latitude_longitude="unknown",
            city_state="unknown",
            timezone="unknown",
            latitude="unknown",
            longitude="unknown"
        )
