"""Verified udata API adapter; discovery never scrapes retailer websites."""

import re
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field


class Resource(BaseModel):
    id: str
    url: str
    format: str = ""
    title: str = ""


class Organization(BaseModel):
    name: str
    slug: str


class Dataset(BaseModel):
    id: str
    slug: str
    title: str
    license: str | None = None
    organization: Organization | None = None
    resources: list[Resource] = Field(default_factory=list)


class Page(BaseModel):
    data: list[Dataset]
    next_page: str | None = None


@dataclass(frozen=True)
class RetailerSource:
    slug: str
    name: str
    dataset_id: str
    url: str
    license: str | None


@dataclass(frozen=True)
class Download:
    status: int
    content: bytes
    etag: str | None = None
    last_modified: str | None = None


class Portal(Protocol):
    def discover(self) -> list[RetailerSource]: ...

    def download(
        self,
        source: RetailerSource,
        etag: str | None = None,
        modified: str | None = None,
    ) -> Download: ...


class PortalClient:
    def __init__(self, client: httpx.Client, base_url: str = "https://data.gov.rs") -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.issues: dict[str, str] = {}
        self.download_retries = 0

    def discover(self) -> list[RetailerSource]:
        datasets: dict[str, Dataset] = {}
        self.issues.clear()
        for query in ("ценовници", "cenovnici", "cenovnik"):
            url: str | None = str(
                httpx.URL(self.base_url + "/api/1/datasets/", params={"q": query, "page_size": 100})
            )
            visited: set[str] = set()
            while url:
                if url in visited or urlparse(url).netloc != urlparse(self.base_url).netloc:
                    raise ValueError("Invalid portal pagination")
                visited.add(url)
                response = self.client.get(url)
                response.raise_for_status()
                page = Page.model_validate(response.json())
                datasets.update((dataset.id, dataset) for dataset in page.data)
                url = page.next_page
        sources: dict[str, RetailerSource] = {}
        ambiguous: set[str] = set()
        for dataset in datasets.values():
            resources = [
                r
                for r in dataset.resources
                if r.format.lower() == "csv"
                and re.search(r"cene[-_]proizvoda", r.url, re.IGNORECASE)
            ]
            if not resources:
                continue
            slug = dataset.organization.slug if dataset.organization else dataset.slug
            urls = {resource.url for resource in resources}
            if len(urls) != 1:
                self.issues[slug] = "ambiguous_resources"
                ambiguous.add(slug)
                continue
            source = RetailerSource(
                slug=slug,
                name=dataset.organization.name if dataset.organization else dataset.title,
                dataset_id=dataset.id,
                url=resources[0].url,
                license=dataset.license,
            )
            if slug in sources and sources[slug].url != source.url:
                self.issues[slug] = "ambiguous_datasets"
                ambiguous.add(slug)
            else:
                sources[slug] = source
        return [source for slug, source in sorted(sources.items()) if slug not in ambiguous]

    def download(
        self,
        source: RetailerSource,
        etag: str | None = None,
        modified: str | None = None,
    ) -> Download:
        self.download_retries = 0
        if urlparse(source.url).scheme != "https":
            raise ValueError("Resource must use HTTPS")
        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        elif modified:
            headers["If-Modified-Since"] = modified
        while True:
            try:
                return self._download(source.url, headers, etag, modified)
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.HTTPStatusError) as exc:
                if (
                    isinstance(exc, httpx.HTTPStatusError)
                    and not 500 <= exc.response.status_code <= 599
                ) or self.download_retries == 2:
                    raise
                delay = (5, 15)[self.download_retries]
                self.download_retries += 1
                time.sleep(delay)

    def _download(
        self, url: str, headers: dict[str, str], etag: str | None, modified: str | None
    ) -> Download:
        with self.client.stream("GET", url, headers=headers) as response:
            if response.status_code == 304:
                return Download(304, b"", etag, modified)
            response.raise_for_status()
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > 100_000_000:
                    raise ValueError("CSV exceeds 100 MB download limit")
                chunks.append(chunk)
            return Download(
                response.status_code,
                b"".join(chunks),
                response.headers.get("etag"),
                response.headers.get("last-modified"),
            )
