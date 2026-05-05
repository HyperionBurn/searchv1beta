"""
Google Places API Plugin — Company and location data.

Free tier: $200/mo free credit
Rate limit: 20 req/min
API docs: https://developers.google.com/maps/documentation/places/web-service
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from rcf.core.base_plugin import ALL_PLUGINS, RateLimitInfo, SourcePlugin
from models.models import ContactQuery, RecruiterContact, SourceResult


class GooglePlacesPlugin(SourcePlugin):
    """Google Places API — company search, phone numbers, addresses, websites."""

    SPEC = ALL_PLUGINS["google_places"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def discover(self, query: ContactQuery) -> list[SourceResult]:
        api_key = self._resolve_api_key()
        if not api_key:
            return []

        results: list[SourceResult] = []
        search_terms = query.company_names + query.keywords

        for term in search_terms:
            region_text = query.region.value if query.region else "uae"
            params = {
                "query": f"{term} recruitment agency {region_text}",
                "key": api_key,
                "fields": "name,formatted_phone_number,website,formatted_address,url",
            }

            resp = await self.http_client.get(
                f"{self.SPEC.url_pattern}/place/textsearch/json",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            for place in data.get("results", []):
                results.append(self._make_source_result(
                    raw_data=place,
                    extracted_company=place.get("name"),
                    extracted_phone=place.get("formatted_phone_number"),
                    source_url=place.get("website") or place.get("url"),
                    confidence_contribution=0.35,
                ))
        return results

    async def enrich(self, contact: RecruiterContact) -> RecruiterContact:
        """Look up company details via Places API."""
        api_key = self._resolve_api_key()
        if not api_key or not contact.company:
            return contact

        try:
            resp = await self.http_client.get(
                f"{self.SPEC.url_pattern}/place/textsearch/json",
                params={"query": contact.company, "key": api_key},
            )
            resp.raise_for_status()
            places = resp.json().get("results", [])
            if places:
                place = places[0]
                phone = place.get("formatted_phone_number")
                if phone and not any(p.phone == phone for p in contact.phones):
                    from models.models import PhoneRecord
                    from models.enums import SourceType
                    contact.phones.append(PhoneRecord(phone=phone, source=SourceType.API))
        except httpx.HTTPError:
            pass

        return contact

    async def validate_config(self) -> bool:
        return bool(self._resolve_api_key())

    async def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(requests_per_minute=self.SPEC.rate_limit_rpm)
