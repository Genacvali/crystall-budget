"""Diagnostic and monitoring tools for Crystal Budget."""
import os
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from functools import wraps
from typing import Dict, List, Any, Optional
from flask import request, g, current_app, jsonify
from werkzeug.exceptions import HTTPException


class ErrorMetrics:
    """Collect and track error metrics by endpoint."""
    
    def __init__(self):
        self.reset_counters()
        self.detailed_errors = []
        self.max_detailed_errors = 1000  # Keep last 1000 detailed errors
    
    def reset_counters(self):
        """Reset all counters."""
        self.error_counts = defaultdict(lambda: defaultdict(int))  # {endpoint: {status_code: count}}
        self.hourly_counts = defaultdict(lambda: defaultdict(int))  # {hour: {status_code: count}}
        self.last_reset = datetime.now()
    
    def record_error(self, endpoint: str, status_code: int, error_details: Optional[Dict] = None):
        """Record an error occurrence."""
        # Update counters
        self.error_counts[endpoint][status_code] += 1
        
        # Update hourly metrics
        current_hour = datetime.now().strftime('%Y-%m-%d %H:00')
        self.hourly_counts[current_hour][status_code] += 1
        
        # Store detailed error info
        if error_details:
            error_record = {
                'timestamp': datetime.now().isoformat(),
                'endpoint': endpoint,
                'status_code': status_code,
                'details': error_details
            }
            
            self.detailed_errors.append(error_record)
            
            # Keep only recent errors
            if len(self.detailed_errors) > self.max_detailed_errors:
                self.detailed_errors = self.detailed_errors[-self.max_detailed_errors:]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get error metrics summary."""
        total_500 = sum(
            counts.get(500, 0) 
            for counts in self.error_counts.values()
        )
        
        total_404 = sum(
            counts.get(404, 0) 
            for counts in self.error_counts.values()
        )
        
        # Top problematic endpoints
        endpoint_500s = [
            (endpoint, counts.get(500, 0))
            for endpoint, counts in self.error_counts.items()
            if counts.get(500, 0) > 0
        ]
        endpoint_500s.sort(key=lambda x: x[1], reverse=True)
        
        endpoint_404s = [
            (endpoint, counts.get(404, 0))
            for endpoint, counts in self.error_counts.items()
            if counts.get(404, 0) > 0
        ]
        endpoint_404s.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'period': {
                'start': self.last_reset.isoformat(),
                'end': datetime.now().isoformat()
            },
            'totals': {
                'errors_500': total_500,
                'errors_404': total_404,
                'total_errors': total_500 + total_404
            },
            'top_500_endpoints': endpoint_500s[:10],
            'top_404_endpoints': endpoint_404s[:10],
            'hourly_breakdown': dict(self.hourly_counts),
            'recent_errors_count': len(self.detailed_errors)
        }
    
    def get_recent_errors(self, limit: int = 50) -> List[Dict]:
        """Get recent detailed errors."""
        return self.detailed_errors[-limit:]


class StaticAssetLogger:
    """Separate logger for static asset 404s."""
    
    def __init__(self, log_file: str = 'static_404.log'):
        self.log_file = log_file
        self.setup_logger()
        self.asset_404_counts = Counter()
    
    def setup_logger(self):
        """Setup dedicated logger for static assets."""
        self.logger = logging.getLogger('static_assets')
        self.logger.setLevel(logging.WARNING)

        try:
            # Create file handler
            handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)

            if not self.logger.handlers:
                self.logger.addHandler(handler)
        except (PermissionError, OSError):
            # File logging disabled due to read-only filesystem
            # Fall back to console logging only
            pass
    
    def log_static_404(self, path: str, user_agent: str = None, referer: str = None):
        """Log static asset 404."""
        self.asset_404_counts[path] += 1
        
        details = {
            'path': path,
            'count': self.asset_404_counts[path],
            'user_agent': user_agent,
            'referer': referer
        }
        
        self.logger.warning(f"Static asset 404: {json.dumps(details)}")
    
    def get_top_missing_assets(self, limit: int = 20) -> List[tuple]:
        """Get most frequently requested missing assets."""
        return self.asset_404_counts.most_common(limit)


# Global instances
error_metrics = ErrorMetrics()

# Use /var/lib/crystalbudget for logs in production (writable path in systemd)
log_dir = os.environ.get('LOG_DIR', '/var/lib/crystalbudget')
static_logger = StaticAssetLogger(log_file=os.path.join(log_dir, 'static_404.log'))


def track_errors(f):
    """Decorator to track errors in routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        endpoint = request.endpoint or 'unknown'
        
        try:
            response = f(*args, **kwargs)
            
            # Check if response indicates an error
            if hasattr(response, 'status_code') and response.status_code >= 400:
                error_details = {
                    'method': request.method,
                    'url': request.url,
                    'args': dict(request.args),
                    'user_agent': request.headers.get('User-Agent'),
                    'ip': request.remote_addr
                }
                
                # Check if it's a static asset 404
                if (response.status_code == 404 and 
                    request.path.startswith('/static/')):
                    static_logger.log_static_404(
                        request.path,
                        request.headers.get('User-Agent'),
                        request.headers.get('Referer')
                    )
                
                error_metrics.record_error(endpoint, response.status_code, error_details)
            
            return response
            
        except HTTPException as e:
            error_details = {
                'method': request.method,
                'url': request.url,
                'exception': str(e),
                'user_agent': request.headers.get('User-Agent'),
                'ip': request.remote_addr
            }
            
            # Log static 404s separately
            if e.code == 404 and request.path.startswith('/static/'):
                static_logger.log_static_404(
                    request.path,
                    request.headers.get('User-Agent'),
                    request.headers.get('Referer')
                )
            
            error_metrics.record_error(endpoint, e.code, error_details)
            raise
            
        except Exception as e:
            error_details = {
                'method': request.method,
                'url': request.url,
                'exception': str(e),
                'exception_type': type(e).__name__,
                'user_agent': request.headers.get('User-Agent'),
                'ip': request.remote_addr
            }
            
            error_metrics.record_error(endpoint, 500, error_details)
            current_app.logger.error(f"Unhandled exception in {endpoint}: {e}")
            raise
    
    return decorated_function


def init_diagnostics(app):
    """Initialize diagnostic tools for the app."""
    
    @app.before_request
    def before_request():
        g.start_time = datetime.now()
    
    @app.after_request 
    def after_request(response):
        # Track response time
        if hasattr(g, 'start_time'):
            duration = (datetime.now() - g.start_time).total_seconds()
            if duration > 1.0:  # Log slow requests
                current_app.logger.warning(
                    f"Slow request: {request.endpoint} took {duration:.2f}s"
                )
        return response
    
    # Add diagnostic routes
    @app.route('/diagnostics/errors')
    def diagnostic_errors():
        """Get error metrics summary."""
        if not current_app.debug and not current_app.config.get('DIAGNOSTICS_ENABLED'):
            return jsonify({'error': 'Diagnostics not enabled'}), 403
        
        return jsonify(error_metrics.get_summary())
    
    @app.route('/diagnostics/errors/recent')
    def diagnostic_recent_errors():
        """Get recent detailed errors."""
        if not current_app.debug and not current_app.config.get('DIAGNOSTICS_ENABLED'):
            return jsonify({'error': 'Diagnostics not enabled'}), 403
        
        limit = request.args.get('limit', 50, type=int)
        return jsonify({
            'recent_errors': error_metrics.get_recent_errors(limit)
        })
    
    @app.route('/diagnostics/static-404')
    def diagnostic_static_404():
        """Get static asset 404 metrics."""
        if not current_app.debug and not current_app.config.get('DIAGNOSTICS_ENABLED'):
            return jsonify({'error': 'Diagnostics not enabled'}), 403
        
        return jsonify({
            'top_missing_assets': static_logger.get_top_missing_assets()
        })
    
    @app.route('/diagnostics/reset')
    def diagnostic_reset():
        """Reset error counters."""
        if not current_app.debug and not current_app.config.get('DIAGNOSTICS_ENABLED'):
            return jsonify({'error': 'Diagnostics not enabled'}), 403
        
        error_metrics.reset_counters()
        static_logger.asset_404_counts.clear()
        
        return jsonify({'status': 'counters reset'})


def generate_diagnostic_report() -> Dict[str, Any]:
    """Generate comprehensive diagnostic report."""
    return {
        'timestamp': datetime.now().isoformat(),
        'error_summary': error_metrics.get_summary(),
        'static_404_summary': {
            'top_missing': static_logger.get_top_missing_assets(10),
            'total_unique_missing': len(static_logger.asset_404_counts)
        },
        'system_info': {
            'uptime_hours': (datetime.now() - error_metrics.last_reset).total_seconds() / 3600
        }
    }