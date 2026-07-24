import asyncio
from playwright.async_api import async_playwright
import os

os.makedirs("screenshots", exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(viewport={"width": 1080, "height": 1920})
        page = await ctx.new_page()

        # Login
        await page.goto("http://localhost:8000/login", timeout=10000)
        await page.fill('input[name="username"]', 'admin')
        await page.fill('input[name="password"]', 'admin123')
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard", timeout=10000)
        print("Logged in")

        pages = [
            ("01-dashboard", "/dashboard"),
            ("02-customers", "/customers"),
            ("03-vehicles", "/vehicles"),
            ("04-work-orders", "/work-orders"),
            ("05-inventory", "/inventory"),
            ("06-scrap-metal", "/scrap-metal"),
            ("07-invoices", "/invoices"),
            ("08-analytics", "/analytics"),
        ]

        for name, path in pages:
            await page.goto(f"http://localhost:8000{path}", timeout=10000)
            await asyncio.sleep(1.5)
            await page.screenshot(path=f"screenshots/{name}.png")
            print(f"OK: {name}")

        await browser.close()
        print("Done!")

asyncio.run(main())
