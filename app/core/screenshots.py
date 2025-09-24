"""Automatic screenshot system for UI changes and testing."""
import os
import asyncio
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from flask import current_app
import subprocess
import json


class ScreenshotManager:
    """Manage UI screenshots for before/after comparisons."""
    
    def __init__(self, screenshots_dir: str = 'static/screenshots'):
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdirectories
        (self.screenshots_dir / 'before').mkdir(exist_ok=True)
        (self.screenshots_dir / 'after').mkdir(exist_ok=True)
        (self.screenshots_dir / 'diffs').mkdir(exist_ok=True)
        
        self.metadata_file = self.screenshots_dir / 'metadata.json'
        self.load_metadata()
    
    def load_metadata(self):
        """Load screenshot metadata."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {'screenshots': [], 'comparisons': []}
    
    def save_metadata(self):
        """Save screenshot metadata."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
    
    def take_screenshot(self, url: str, name: str, viewport: Dict = None, 
                       screenshot_type: str = 'after') -> Optional[str]:
        """Take screenshot using playwright or browser automation."""
        if viewport is None:
            viewport = {'width': 1200, 'height': 800}
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{name}_{timestamp}.png"
        filepath = self.screenshots_dir / screenshot_type / filename
        
        try:
            # Check if playwright is available
            if self._has_playwright():
                return self._take_screenshot_playwright(url, filepath, viewport)
            else:
                # Fallback to headless Chrome via subprocess
                return self._take_screenshot_chrome(url, filepath, viewport)
                
        except Exception as e:
            current_app.logger.error(f"Screenshot failed for {url}: {e}")
            return None
    
    def _has_playwright(self) -> bool:
        """Check if Playwright is available."""
        try:
            import playwright
            return True
        except ImportError:
            return False
    
    def _take_screenshot_playwright(self, url: str, filepath: Path, viewport: Dict) -> str:
        """Take screenshot using Playwright."""
        import asyncio
        from playwright.async_api import async_playwright
        
        async def capture():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(viewport=viewport)
                page = await context.new_page()
                
                await page.goto(url, wait_until='networkidle')
                await page.screenshot(path=str(filepath), full_page=True)
                
                await browser.close()
        
        # Run in new event loop if needed
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create new thread for async operation
                import threading
                import concurrent.futures
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(capture())
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    future.result()
            else:
                loop.run_until_complete(capture())
        except RuntimeError:
            # Create new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(capture())
            finally:
                loop.close()
        
        return str(filepath)
    
    def _take_screenshot_chrome(self, url: str, filepath: Path, viewport: Dict) -> str:
        """Take screenshot using headless Chrome via subprocess."""
        chrome_commands = [
            'google-chrome',
            'chromium-browser',
            'chromium',
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        ]
        
        chrome_path = None
        for cmd in chrome_commands:
            try:
                subprocess.run([cmd, '--version'], capture_output=True, check=True)
                chrome_path = cmd
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        if not chrome_path:
            raise Exception("Chrome/Chromium not found")
        
        cmd = [
            chrome_path,
            '--headless',
            '--disable-gpu',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            f'--window-size={viewport["width"]},{viewport["height"]}',
            f'--screenshot={filepath}',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            raise Exception(f"Chrome screenshot failed: {result.stderr}")
        
        return str(filepath)
    
    def compare_screenshots(self, before_path: str, after_path: str, 
                          threshold: float = 0.1) -> Optional[Dict]:
        """Compare two screenshots and generate diff image."""
        try:
            from PIL import Image, ImageChops, ImageStat
            import numpy as np
        except ImportError:
            current_app.logger.warning("PIL not available for screenshot comparison")
            return None
        
        try:
            # Load images
            before_img = Image.open(before_path)
            after_img = Image.open(after_path)
            
            # Resize to same dimensions
            size = (min(before_img.width, after_img.width), 
                   min(before_img.height, after_img.height))
            before_img = before_img.resize(size)
            after_img = after_img.resize(size)
            
            # Calculate difference
            diff = ImageChops.difference(before_img, after_img)
            
            # Calculate similarity percentage
            stat = ImageStat.Stat(diff)
            diff_percent = sum(stat.mean) / (len(stat.mean) * 255) * 100
            
            # Generate diff image if significant difference
            diff_path = None
            if diff_percent > threshold:
                # Enhance diff visibility
                diff_enhanced = diff.point(lambda p: p * 10)  # Enhance visibility
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                diff_filename = f"diff_{timestamp}.png"
                diff_path = self.screenshots_dir / 'diffs' / diff_filename
                
                diff_enhanced.save(str(diff_path))
            
            comparison = {
                'before': before_path,
                'after': after_path,
                'diff': str(diff_path) if diff_path else None,
                'diff_percentage': round(diff_percent, 2),
                'is_significant': diff_percent > threshold,
                'timestamp': datetime.now().isoformat()
            }
            
            # Save to metadata
            self.metadata['comparisons'].append(comparison)
            self.save_metadata()
            
            return comparison
            
        except Exception as e:
            current_app.logger.error(f"Screenshot comparison failed: {e}")
            return None
    
    def capture_page_variants(self, base_url: str, page_name: str, 
                            test_data: Dict = None) -> List[Dict]:
        """Capture multiple variants of a page (different states, devices, etc.)."""
        results = []
        
        # Standard desktop viewport
        desktop_result = self.capture_ui_state(
            base_url, page_name, 'desktop',
            viewport={'width': 1200, 'height': 800},
            test_data=test_data
        )
        if desktop_result:
            results.append(desktop_result)
        
        # Mobile viewport
        mobile_result = self.capture_ui_state(
            base_url, page_name, 'mobile',
            viewport={'width': 375, 'height': 667},
            test_data=test_data
        )
        if mobile_result:
            results.append(mobile_result)
        
        # Tablet viewport
        tablet_result = self.capture_ui_state(
            base_url, page_name, 'tablet',
            viewport={'width': 768, 'height': 1024},
            test_data=test_data
        )
        if tablet_result:
            results.append(tablet_result)
        
        return results
    
    def capture_ui_state(self, base_url: str, page_name: str, variant: str,
                        viewport: Dict, test_data: Dict = None) -> Optional[Dict]:
        """Capture a specific UI state with test data."""
        url = f"{base_url}/{page_name}"
        
        # Add test parameters if provided
        if test_data:
            query_params = "&".join([f"{k}={v}" for k, v in test_data.items()])
            url = f"{url}?{query_params}"
        
        screenshot_name = f"{page_name}_{variant}"
        filepath = self.take_screenshot(url, screenshot_name, viewport)
        
        if filepath:
            # Generate hash for duplicate detection
            file_hash = self._get_file_hash(filepath)
            
            screenshot_info = {
                'page': page_name,
                'variant': variant,
                'url': url,
                'filepath': filepath,
                'hash': file_hash,
                'viewport': viewport,
                'timestamp': datetime.now().isoformat(),
                'test_data': test_data
            }
            
            self.metadata['screenshots'].append(screenshot_info)
            self.save_metadata()
            
            return screenshot_info
        
        return None
    
    def _get_file_hash(self, filepath: str) -> str:
        """Generate hash of file content."""
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def get_comparison_history(self, page_name: str = None, limit: int = 20) -> List[Dict]:
        """Get recent screenshot comparisons."""
        comparisons = self.metadata.get('comparisons', [])
        
        if page_name:
            comparisons = [
                c for c in comparisons 
                if page_name in c.get('before', '') or page_name in c.get('after', '')
            ]
        
        # Sort by timestamp (newest first)
        comparisons.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return comparisons[:limit]
    
    def cleanup_old_screenshots(self, days: int = 30):
        """Remove screenshots older than specified days."""
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        
        cleaned_count = 0
        for screenshot_type in ['before', 'after', 'diffs']:
            type_dir = self.screenshots_dir / screenshot_type
            for file in type_dir.glob('*.png'):
                if file.stat().st_mtime < cutoff:
                    file.unlink()
                    cleaned_count += 1
        
        # Clean metadata
        self.metadata['screenshots'] = [
            s for s in self.metadata['screenshots']
            if datetime.fromisoformat(s['timestamp']).timestamp() > cutoff
        ]
        
        self.metadata['comparisons'] = [
            c for c in self.metadata['comparisons']
            if datetime.fromisoformat(c['timestamp']).timestamp() > cutoff
        ]
        
        self.save_metadata()
        
        current_app.logger.info(f"Cleaned up {cleaned_count} old screenshots")


def create_ui_regression_test(page_name: str, test_scenarios: List[Dict]) -> bool:
    """Create automated UI regression test."""
    try:
        screenshot_manager = ScreenshotManager()
        base_url = "http://localhost:5000"  # Adjust as needed
        
        all_results = []
        
        for scenario in test_scenarios:
            scenario_name = scenario.get('name', 'default')
            test_data = scenario.get('data', {})
            
            # Capture current state
            results = screenshot_manager.capture_page_variants(
                base_url, page_name, test_data
            )
            
            for result in results:
                result['scenario'] = scenario_name
                all_results.append(result)
        
        current_app.logger.info(f"Created UI regression test for {page_name}: {len(all_results)} screenshots")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to create UI regression test: {e}")
        return False


# Global instance
screenshot_manager = ScreenshotManager()