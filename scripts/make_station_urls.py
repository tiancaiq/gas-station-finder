import asyncio
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

START_URL = "https://www.gasbuddy.com/gasprices/california/irvine"

async def main():
    browser_config = BrowserConfig(headless=True, viewport_width=1280, viewport_height=800)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        remove_overlay_elements=True,
        wait_for="css:body",
        page_timeout=60000,
        screenshot=False,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=START_URL, config=run_config)

    if not result.success:
        print("❌ Failed:", result.error_message)
        return

    links = (result.links.get("internal", []) or []) + (result.links.get("external", []) or [])

    urls = []
    for link in links:
        href = link.get("href") if isinstance(link, dict) else str(link)
        if not href:
            continue
        urls.append(urljoin(result.url, href))

    # GasBuddy station pages commonly contain "/station/"
    station_urls = sorted({u for u in urls if "/station/" in u.lower()})

    with open("urls.txt", "w", encoding="utf-8") as f:
        for u in station_urls:
            f.write(u + "\n")

    print(f"✅ Saved {len(station_urls)} station URLs to urls.txt")

if __name__ == "__main__":
    asyncio.run(main())
