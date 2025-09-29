#!/usr/bin/env python3
"""Real-time canary rollout monitoring script."""
import requests
import time
import json
from datetime import datetime
from collections import defaultdict, deque


class CanaryMonitor:
    def __init__(self, base_url="http://localhost:5030"):
        self.base_url = base_url
        self.metrics = defaultdict(deque)
        self.error_count = 0
        self.total_requests = 0
        self.start_time = time.time()
        
        # Performance thresholds (from requirements)
        self.thresholds = {
            'modal_get_p95_ms': 300,      # GET /modals/* p95 < 300ms
            'modal_post_p95_ms': 500,     # POST /modals/* p95 < 500ms
            'modal_error_pct': 1.0,       # error% < 1%
            'fe_error_rate': 0.5,         # FE error rate < 0.5%
            'lcp_degradation_ms': 300,    # LCP без деградации > +300ms
            'inp_ms': 200,                # INP < 200ms
            'cls': 0.1                    # CLS < 0.1
        }
        
        print(f"🚀 Starting Canary Monitoring for {base_url}")
        print(f"📊 Performance Thresholds: {json.dumps(self.thresholds, indent=2)}")
        print("=" * 60)

    def check_health(self):
        """Check application health."""
        try:
            response = requests.get(f"{self.base_url}/healthz", timeout=5)
            if response.status_code == 200:
                return True, "healthy"
            else:
                return False, f"status_code_{response.status_code}"
        except Exception as e:
            return False, str(e)

    def test_modal_endpoints(self):
        """Test modal endpoint performance."""
        modal_endpoints = [
            ('GET', '/modals/expense/add'),
            ('GET', '/modals/income/add'),
            ('GET', '/modals/goal/add'),
            ('GET', '/modals/settings/profile'),
        ]
        
        results = []
        
        for method, endpoint in modal_endpoints:
            start_time = time.time()
            try:
                if method == 'GET':
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                else:
                    response = requests.post(f"{self.base_url}{endpoint}", timeout=10)
                
                duration_ms = (time.time() - start_time) * 1000
                success = 200 <= response.status_code < 400
                
                results.append({
                    'endpoint': endpoint,
                    'method': method,
                    'duration_ms': duration_ms,
                    'status_code': response.status_code,
                    'success': success
                })
                
                self.total_requests += 1
                if not success:
                    self.error_count += 1
                    
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                results.append({
                    'endpoint': endpoint,
                    'method': method,
                    'duration_ms': duration_ms,
                    'status_code': 0,
                    'success': False,
                    'error': str(e)
                })
                
                self.total_requests += 1
                self.error_count += 1
        
        return results

    def test_core_pages(self):
        """Test core page performance (dashboard, expenses, income, goals, settings)."""
        core_pages = [
            '/',                    # Dashboard
            '/expenses',           # Expenses
            '/income',             # Income  
            '/goals',              # Goals
            '/settings'            # Settings
        ]
        
        results = []
        
        for page in core_pages:
            start_time = time.time()
            try:
                response = requests.get(f"{self.base_url}{page}", 
                                      timeout=10, 
                                      allow_redirects=True)
                duration_ms = (time.time() - start_time) * 1000
                
                # Check for bundle information in response
                content = response.text
                using_unified = 'modals.js' in content or 'Using unified bundle' in content
                using_legacy = not using_unified
                
                results.append({
                    'page': page,
                    'duration_ms': duration_ms,
                    'status_code': response.status_code,
                    'success': response.status_code == 200,
                    'bundle_type': 'unified' if using_unified else 'legacy',
                    'content_length': len(content)
                })
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                results.append({
                    'page': page,
                    'duration_ms': duration_ms,
                    'status_code': 0,
                    'success': False,
                    'error': str(e)
                })
        
        return results

    def calculate_percentiles(self, values):
        """Calculate percentiles for performance metrics."""
        if not values:
            return {'p50': 0, 'p95': 0, 'p99': 0}
            
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            'p50': sorted_values[int(n * 0.5)],
            'p95': sorted_values[int(n * 0.95)],
            'p99': sorted_values[int(n * 0.99)]
        }

    def analyze_results(self, modal_results, page_results):
        """Analyze results and check against thresholds."""
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Separate GET and POST modal results
        get_modals = [r for r in modal_results if r['method'] == 'GET']
        post_modals = [r for r in modal_results if r['method'] == 'POST']
        
        # Calculate performance metrics
        get_durations = [r['duration_ms'] for r in get_modals if r['success']]
        post_durations = [r['duration_ms'] for r in post_modals if r['success']]
        page_durations = [r['duration_ms'] for r in page_results if r['success']]
        
        get_percentiles = self.calculate_percentiles(get_durations)
        post_percentiles = self.calculate_percentiles(post_durations)
        page_percentiles = self.calculate_percentiles(page_durations)
        
        # Calculate error rates
        modal_errors = sum(1 for r in modal_results if not r['success'])
        modal_total = len(modal_results)
        modal_error_pct = (modal_errors / modal_total * 100) if modal_total > 0 else 0
        
        overall_error_pct = (self.error_count / self.total_requests * 100) if self.total_requests > 0 else 0
        
        # Bundle distribution
        bundle_distribution = defaultdict(int)
        for r in page_results:
            bundle_distribution[r.get('bundle_type', 'unknown')] += 1
        
        # Status report
        status_report = {
            'timestamp': current_time,
            'uptime_seconds': int(time.time() - self.start_time),
            'performance': {
                'modal_get_p95_ms': get_percentiles['p95'],
                'modal_post_p95_ms': post_percentiles['p95'],
                'page_load_p95_ms': page_percentiles['p95'],
                'modal_error_pct': modal_error_pct,
                'overall_error_pct': overall_error_pct
            },
            'bundle_distribution': dict(bundle_distribution),
            'requests': {
                'total': self.total_requests,
                'errors': self.error_count,
                'modal_requests': len(modal_results),
                'page_requests': len(page_results)
            }
        }
        
        # Check thresholds
        alerts = []
        perf = status_report['performance']
        
        if perf['modal_get_p95_ms'] > self.thresholds['modal_get_p95_ms']:
            alerts.append(f"🚨 Modal GET p95 ({perf['modal_get_p95_ms']:.1f}ms) > {self.thresholds['modal_get_p95_ms']}ms")
        
        if perf['modal_post_p95_ms'] > self.thresholds['modal_post_p95_ms']:
            alerts.append(f"🚨 Modal POST p95 ({perf['modal_post_p95_ms']:.1f}ms) > {self.thresholds['modal_post_p95_ms']}ms")
        
        if perf['modal_error_pct'] > self.thresholds['modal_error_pct']:
            alerts.append(f"🚨 Modal error rate ({perf['modal_error_pct']:.1f}%) > {self.thresholds['modal_error_pct']}%")
        
        if perf['overall_error_pct'] > self.thresholds['fe_error_rate']:
            alerts.append(f"🚨 Overall error rate ({perf['overall_error_pct']:.1f}%) > {self.thresholds['fe_error_rate']}%")
        
        status_report['alerts'] = alerts
        return status_report

    def print_report(self, report):
        """Print formatted monitoring report."""
        print(f"[{report['timestamp']}] Canary Monitor Report (Uptime: {report['uptime_seconds']}s)")
        print("-" * 60)
        
        # Performance metrics
        perf = report['performance']
        print(f"📈 Performance:")
        print(f"  Modal GET p95:     {perf['modal_get_p95_ms']:6.1f}ms (threshold: {self.thresholds['modal_get_p95_ms']}ms)")
        print(f"  Modal POST p95:    {perf['modal_post_p95_ms']:6.1f}ms (threshold: {self.thresholds['modal_post_p95_ms']}ms)")
        print(f"  Page load p95:     {perf['page_load_p95_ms']:6.1f}ms")
        print(f"  Modal error rate:  {perf['modal_error_pct']:6.1f}% (threshold: {self.thresholds['modal_error_pct']}%)")
        print(f"  Overall error rate:{perf['overall_error_pct']:6.1f}% (threshold: {self.thresholds['fe_error_rate']}%)")
        
        # Bundle distribution
        print(f"\\n📦 Bundle Distribution:")
        total_bundles = sum(report['bundle_distribution'].values())
        for bundle_type, count in report['bundle_distribution'].items():
            pct = (count / total_bundles * 100) if total_bundles > 0 else 0
            print(f"  {bundle_type.capitalize():8}: {count:3d} requests ({pct:5.1f}%)")
        
        # Requests
        req = report['requests']
        print(f"\\n📊 Requests:")
        print(f"  Total: {req['total']}, Errors: {req['errors']}, Modal: {req['modal_requests']}, Pages: {req['page_requests']}")
        
        # Alerts
        if report['alerts']:
            print(f"\\n🚨 ALERTS:")
            for alert in report['alerts']:
                print(f"  {alert}")
        else:
            print(f"\\n✅ All metrics within thresholds")
        
        print("=" * 60)

    def monitor_loop(self, interval_seconds=30, duration_minutes=None):
        """Main monitoring loop."""
        print(f"🔄 Starting monitoring loop (interval: {interval_seconds}s)")
        if duration_minutes:
            print(f"⏰ Will run for {duration_minutes} minutes")
        
        end_time = time.time() + (duration_minutes * 60) if duration_minutes else None
        iteration = 0
        
        try:
            while True:
                iteration += 1
                print(f"\\n🔍 Monitoring iteration #{iteration}")
                
                # Check health first
                health_ok, health_msg = self.check_health()
                if not health_ok:
                    print(f"❌ Health check failed: {health_msg}")
                    time.sleep(interval_seconds)
                    continue
                
                # Test modal endpoints
                modal_results = self.test_modal_endpoints()
                
                # Test core pages
                page_results = self.test_core_pages()
                
                # Analyze and report
                report = self.analyze_results(modal_results, page_results)
                self.print_report(report)
                
                # Check if we should continue
                if end_time and time.time() >= end_time:
                    print(f"\\n⏰ Monitoring duration completed")
                    break
                
                # Wait for next iteration
                print(f"\\n⏳ Waiting {interval_seconds}s until next check...")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print(f"\\n🛑 Monitoring interrupted by user")
        except Exception as e:
            print(f"\\n❌ Monitoring error: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Canary rollout monitoring')
    parser.add_argument('--url', default='http://localhost:5030', help='Base URL to monitor')
    parser.add_argument('--interval', type=int, default=30, help='Monitoring interval in seconds')
    parser.add_argument('--duration', type=int, default=None, help='Duration in minutes (default: run forever)')
    
    args = parser.parse_args()
    
    monitor = CanaryMonitor(args.url)
    monitor.monitor_loop(args.interval, args.duration)