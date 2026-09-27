from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedLocation:
    country_code: str
    region: str
    is_remote: bool


_COUNTRY_ALIASES: dict[str, str] = {
    "id": "ID",
    "indonesia": "ID",
    "us": "US",
    "usa": "US",
    "united states": "US",
    "sg": "SG",
    "singapore": "SG",
    "my": "MY",
    "malaysia": "MY",
    "ph": "PH",
    "philippines": "PH",
    "th": "TH",
    "thailand": "TH",
    "vn": "VN",
    "vietnam": "VN",
    "gb": "GB",
    "uk": "GB",
    "united kingdom": "GB",
    "de": "DE",
    "germany": "DE",
    "fr": "FR",
    "france": "FR",
    "nl": "NL",
    "netherlands": "NL",
    "ca": "CA",
    "canada": "CA",
    "au": "AU",
    "australia": "AU",
    "in": "IN",
    "india": "IN",
    "jp": "JP",
    "japan": "JP",
    "kr": "KR",
    "korea": "KR",
    "br": "BR",
    "brazil": "BR",
}

_REGION_BY_CODE: dict[str, str] = {
    "ID": "apac",
    "SG": "apac",
    "MY": "apac",
    "PH": "apac",
    "TH": "apac",
    "VN": "apac",
    "IN": "apac",
    "JP": "apac",
    "KR": "apac",
    "AU": "apac",
    "US": "americas",
    "CA": "americas",
    "BR": "americas",
    "GB": "emea",
    "DE": "emea",
    "FR": "emea",
    "NL": "emea",
}

_REMOTE_KEYWORDS = (
    "remote",
    "anywhere",
    "work from home",
    "wfh",
    "telecommute",
)


def normalize_location(text: str, identifiers: dict) -> NormalizedLocation:
    cleaned = (text or "").strip().lower()
    code = _COUNTRY_ALIASES.get(cleaned, "")
    region = _REGION_BY_CODE.get(code, "")
    is_remote = _detect_remote(cleaned, identifiers)
    return NormalizedLocation(
        country_code=code,
        region=region,
        is_remote=is_remote,
    )


def _detect_remote(cleaned_text: str, identifiers: dict) -> bool:
    flag = str(identifiers.get("remote", "") or "").strip().lower()
    if flag == "1":
        return True
    if flag == "0":
        return False
    return any(keyword in cleaned_text for keyword in _REMOTE_KEYWORDS)