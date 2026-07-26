import asyncio
from playwright.async_api import async_playwright
import os

os.makedirs("screenshots", exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        ctx = await browser.new_context(viewport={"width": 1080, "height": 1920})
        page = await ctx.new_page()

        # Step 1: GET login page to capture CSRF token
        await page.goto("http://localhost:8000/login", wait_until="networkidle", timeout=15000)
        await asyncio.sleep(1)

        # Extract CSRF token from hidden input
        csrf = await page.evaluate('() => document.querySelector(\'input[name="csrf_token"]\')?.value || ""')
        print(f"CSRF token: {csrf[:20]}...")

        # Step 2: POST login directly
        resp = await page.evaluate(f'''async () => {{
            const formData = new FormData();
            formData.append("csrf_token", "{csrf}");
            formData.append("username", "admin");
            formData.append("password", "admin123");
            const r = await fetch("/login", {{
                method: "POST",
                body: formData,
                redirect: "manual"
            }});
            return {{status: r.status, type: r.type, url: r.url, redirected: r.redirected}};
        }}''')
        print(f"Login response: {resp}")

        # Step 3: Navigate to dashboard to pick up session cookie
        await page.goto("http://localhost:8000/dashboard", wait_until="networkidle", timeout=15000)
        await asyncio.sleep(1)
        print(f"After dashboard nav: {page.url}")

        # Check if we're on the dashboard
        title = await page.title()
        print(f"Page title: {title}")

        # Take screenshots
        pages = [
            ("00-login", "/login"),
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
            await page.goto(f"http://localhost:8000{path}", wait_until="networkidle", timeout=15000)
            await asyncio.sleep(1.5)
            await page.screenshot(path=f"screenshots/{name}.png")
            sz = os.path.getsize(f"screenshots/{name}.png")
            print(f"Captured: {name} ({sz//1024}KB)")

        await browser.close()
        print("\nDone!")

asyncio.run(main())
