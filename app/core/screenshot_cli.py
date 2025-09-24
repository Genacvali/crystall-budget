"""CLI commands for screenshot management."""
import click
from flask.cli import with_appcontext
from app.core.screenshots import screenshot_manager, create_ui_regression_test


@click.group()
def screenshot():
    """Screenshot management commands."""
    pass


@screenshot.command()
@click.argument('page_name')
@click.option('--url', default='http://localhost:5000', help='Base URL')
@click.option('--variants', default='desktop,mobile,tablet', help='Viewport variants')
@with_appcontext
def capture(page_name, url, variants):
    """Capture screenshots of a page in different variants."""
    click.echo(f"Capturing screenshots for page: {page_name}")
    
    results = []
    for variant in variants.split(','):
        if variant == 'desktop':
            viewport = {'width': 1200, 'height': 800}
        elif variant == 'mobile':
            viewport = {'width': 375, 'height': 667}
        elif variant == 'tablet':
            viewport = {'width': 768, 'height': 1024}
        else:
            viewport = {'width': 1200, 'height': 800}
        
        result = screenshot_manager.capture_ui_state(
            url, page_name, variant, viewport
        )
        
        if result:
            results.append(result)
            click.echo(f"✅ Captured {variant}: {result['filepath']}")
        else:
            click.echo(f"❌ Failed to capture {variant}")
    
    click.echo(f"Completed: {len(results)}/{len(variants.split(','))} screenshots captured")


@screenshot.command()
@click.argument('page_name')
@click.option('--scenarios', default='default', help='Test scenarios JSON file or comma-separated names')
@with_appcontext
def regression_test(page_name, scenarios):
    """Create UI regression test for a page."""
    click.echo(f"Creating UI regression test for: {page_name}")
    
    # Parse scenarios
    if scenarios == 'default':
        test_scenarios = [{'name': 'default', 'data': {}}]
    elif scenarios.endswith('.json'):
        import json
        with open(scenarios, 'r') as f:
            test_scenarios = json.load(f)
    else:
        test_scenarios = [
            {'name': name.strip(), 'data': {}} 
            for name in scenarios.split(',')
        ]
    
    success = create_ui_regression_test(page_name, test_scenarios)
    
    if success:
        click.echo("✅ UI regression test created successfully")
    else:
        click.echo("❌ Failed to create UI regression test")


@screenshot.command()
@click.argument('before_path')
@click.argument('after_path')
@click.option('--threshold', default=0.1, help='Difference threshold (0.0-100.0)')
@with_appcontext
def compare(before_path, after_path, threshold):
    """Compare two screenshots."""
    click.echo(f"Comparing screenshots...")
    click.echo(f"Before: {before_path}")
    click.echo(f"After: {after_path}")
    
    result = screenshot_manager.compare_screenshots(
        before_path, after_path, threshold
    )
    
    if result:
        click.echo(f"\n📊 Comparison Results:")
        click.echo(f"Difference: {result['diff_percentage']}%")
        click.echo(f"Significant: {'Yes' if result['is_significant'] else 'No'}")
        
        if result['diff']:
            click.echo(f"Diff image: {result['diff']}")
    else:
        click.echo("❌ Comparison failed")


@screenshot.command()
@click.option('--page', help='Filter by page name')
@click.option('--limit', default=10, help='Number of comparisons to show')
@with_appcontext
def history(page, limit):
    """Show screenshot comparison history."""
    comparisons = screenshot_manager.get_comparison_history(page, limit)
    
    if not comparisons:
        click.echo("No comparison history found")
        return
    
    click.echo(f"\n📝 Recent Comparisons ({len(comparisons)}):")
    click.echo("-" * 80)
    
    for comp in comparisons:
        timestamp = comp.get('timestamp', 'Unknown')[:19]  # Remove microseconds
        diff_percent = comp.get('diff_percentage', 0)
        significant = "🔴" if comp.get('is_significant') else "🟢"
        
        click.echo(f"{significant} {timestamp} - {diff_percent}% difference")
        
        before_name = comp.get('before', '').split('/')[-1]
        after_name = comp.get('after', '').split('/')[-1]
        
        click.echo(f"   Before: {before_name}")
        click.echo(f"   After:  {after_name}")
        
        if comp.get('diff'):
            diff_name = comp.get('diff', '').split('/')[-1]
            click.echo(f"   Diff:   {diff_name}")
        
        click.echo()


@screenshot.command()
@click.option('--days', default=30, help='Days to keep screenshots')
@with_appcontext
def cleanup(days):
    """Clean up old screenshots."""
    click.echo(f"Cleaning up screenshots older than {days} days...")
    
    screenshot_manager.cleanup_old_screenshots(days)
    
    click.echo("✅ Cleanup completed")


@screenshot.command()
@with_appcontext
def auto_dashboard():
    """Automatically capture dashboard screenshots in different states."""
    click.echo("📸 Capturing dashboard screenshots...")
    
    # Define different dashboard states to test
    scenarios = [
        {
            'name': 'empty_state',
            'data': {'test_mode': 'empty'}
        },
        {
            'name': 'with_data',
            'data': {'test_mode': 'sample_data'}
        },
        {
            'name': 'mobile_view',
            'data': {'mobile': '1'}
        }
    ]
    
    success = create_ui_regression_test('dashboard', scenarios)
    
    if success:
        click.echo("✅ Dashboard screenshots captured")
        
        # Also capture key pages
        pages = ['categories', 'expenses', 'income', 'profile']
        for page in pages:
            click.echo(f"📸 Capturing {page}...")
            result = screenshot_manager.capture_ui_state(
                'http://localhost:5000', page, 'desktop',
                {'width': 1200, 'height': 800}
            )
            
            if result:
                click.echo(f"✅ {page} captured")
            else:
                click.echo(f"❌ {page} failed")
    else:
        click.echo("❌ Dashboard capture failed")


def register_screenshot_commands(app):
    """Register screenshot commands with Flask app."""
    app.cli.add_command(screenshot)