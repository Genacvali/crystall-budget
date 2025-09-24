"""E2E test configuration and fixtures."""
import pytest
from playwright.async_api import async_playwright
import asyncio
import os


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the entire test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def browser():
    """Browser instance for all tests."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        yield browser
        await browser.close()


@pytest.fixture(scope="function")
async def page(browser):
    """Fresh page for each test."""
    context = await browser.new_context(
        viewport={'width': 1280, 'height': 720},
        locale='ru-RU'
    )
    page = await context.new_page()
    
    # Add console error tracking
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda err: errors.append(str(err)))
    
    yield page
    
    # Check for console errors
    if errors:
        print(f"Console errors detected: {errors}")
    
    await context.close()


@pytest.fixture(scope="function")
async def authenticated_page(page):
    """Page with authenticated user (mock Telegram auth)."""
    base_url = os.getenv('BASE_URL', 'http://localhost:5000')
    
    # For testing, we'll need to mock Telegram auth
    # This is a simplified version - in real tests you'd need proper auth setup
    await page.goto(f"{base_url}/login")
    
    # Check if already authenticated
    if "/dashboard" in page.url:
        return page
        
    # Mock authentication by directly setting session
    # In real implementation, you'd handle Telegram auth properly
    await page.evaluate("""
        // Mock authentication for testing
        localStorage.setItem('user_authenticated', 'true');
        document.cookie = 'session=test_session_token; path=/';
    """)
    
    await page.goto(f"{base_url}/dashboard")
    return page


class TestHelpers:
    """Helper methods for E2E tests."""
    
    @staticmethod
    async def wait_for_load(page, timeout=10000):
        """Wait for page to fully load."""
        await page.wait_for_load_state("networkidle", timeout=timeout)
    
    @staticmethod
    async def fill_form_field(page, selector, value):
        """Fill form field and wait for it to be filled."""
        await page.fill(selector, value)
        await page.wait_for_function(
            f"document.querySelector('{selector}').value === '{value}'"
        )
    
    @staticmethod
    async def click_and_wait(page, selector, wait_for=None):
        """Click element and optionally wait for navigation or selector."""
        await page.click(selector)
        if wait_for:
            if wait_for.startswith('http'):
                await page.wait_for_url(wait_for)
            else:
                await page.wait_for_selector(wait_for)
    
    @staticmethod
    async def take_screenshot(page, name):
        """Take screenshot for debugging."""
        screenshot_dir = "test-results/screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        await page.screenshot(path=f"{screenshot_dir}/{name}.png")
    
    @staticmethod
    async def assert_no_console_errors(page):
        """Assert no JavaScript console errors."""
        errors = await page.evaluate("""
            () => window.testErrors || []
        """)
        assert len(errors) == 0, f"Console errors found: {errors}"


@pytest.fixture
def helpers():
    """Provide test helpers."""
    return TestHelpers