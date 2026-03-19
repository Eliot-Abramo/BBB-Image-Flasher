from __future__ import annotations

import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup


DISTROS_URL = "https://www.beagleboard.org/distros"


@dataclass(slots=True)
class CatalogEntry:
    label: str
    image_url: str
    checksum: str
    source_page: str


class CatalogError(RuntimeError):
    pass


class BeagleCatalog:
    def fetch_bbb_images(self) -> list[CatalogEntry]:
        response = requests.get(DISTROS_URL, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        links = soup.find_all("a", href=True)
        detail_links = []
        for link in links:
            href = link["href"]
            text = " ".join(link.get_text(" ", strip=True).split())
            if "/distros/beaglebone-black-" in href:
                detail_links.append((text or href, href))

        entries: list[CatalogEntry] = []
        seen: set[str] = set()
        for _, href in detail_links:
            detail_url = href if href.startswith("http") else f"https://www.beagleboard.org{href}"
            if detail_url in seen:
                continue
            seen.add(detail_url)
            entry = self._parse_detail_page(detail_url)
            if entry is not None:
                entries.append(entry)

        if not entries:
            raise CatalogError("No BeagleBone Black images found on the Beagle distros page.")
        return entries

    def _parse_detail_page(self, url: str) -> CatalogEntry | None:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text("\n", strip=True)

        image_url = None
        checksum = None
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.endswith(".img.xz"):
                image_url = href
            if re.fullmatch(r"[a-fA-F0-9]{64}", link.get_text(strip=True)):
                checksum = link.get_text(strip=True)

        title = soup.title.get_text(strip=True) if soup.title else url
        if image_url and checksum:
            return CatalogEntry(
                label=title.replace(" - BeagleBoard", ""),
                image_url=image_url,
                checksum=checksum,
                source_page=url,
            )
        return None
