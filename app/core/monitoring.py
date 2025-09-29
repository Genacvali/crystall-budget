"""Monitoring utilities for modal system rollout."""
import time
import logging
from functools import wraps
from flask import request, session, current_app
from app.core.features import is_modal_system_enabled

# Set up monitoring logger
monitoring_logger = logging.getLogger('crystalbudget.monitoring')
monitoring_logger.setLevel(logging.INFO)


class ModalMetrics:
    """Collect and track modal system metrics."""
    
    def __init__(self):
        self.metrics = {
            'modal_loads': 0,
            'modal_errors': 0,
            'bundle_loads': {'unified': 0, 'legacy': 0},
            'feature_flag_checks': 0,
            'average_load_time': 0.0,
            'load_times': []
        }
    
    def record_modal_load(self, duration_ms, success=True):
        """Record a modal load event."""
        self.metrics['modal_loads'] += 1
        if not success:
            self.metrics['modal_errors'] += 1
            
        self.metrics['load_times'].append(duration_ms)
        if self.metrics['load_times']:
            self.metrics['average_load_time'] = sum(self.metrics['load_times']) / len(self.metrics['load_times'])
            
        # Keep only last 100 measurements
        if len(self.metrics['load_times']) > 100:
            self.metrics['load_times'] = self.metrics['load_times'][-100:]
    
    def record_bundle_load(self, bundle_type):
        """Record bundle load by type."""
        if bundle_type in self.metrics['bundle_loads']:
            self.metrics['bundle_loads'][bundle_type] += 1
    
    def record_feature_flag_check(self):
        """Record feature flag check."""
        self.metrics['feature_flag_checks'] += 1
    
    def get_stats(self):
        """Get current metrics."""
        return self.metrics.copy()


# Global metrics instance
modal_metrics = ModalMetrics()


def monitor_modal_performance(route_name=None):
    """Decorator to monitor modal route performance."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            user_id = session.get('user_id', 'anonymous')
            modal_enabled = is_modal_system_enabled()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Record metrics
                modal_metrics.record_modal_load(duration_ms, success=True)
                
                # Record telemetry
                try:
                    from app.core.telemetry import record_modal_load
                    record_modal_load(route_name or func.__name__, duration_ms, True, user_id)
                except Exception:
                    pass  # Don't break monitoring for telemetry failures
                
                # Log performance
                monitoring_logger.info(
                    f"modal_route={route_name or func.__name__} "
                    f"duration_ms={duration_ms:.2f} "
                    f"status=success "
                    f"user_id={user_id} "
                    f"modal_enabled={modal_enabled} "
                    f"path={request.path}"
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                modal_metrics.record_modal_load(duration_ms, success=False)
                
                # Record telemetry for error
                try:
                    from app.core.telemetry import record_modal_error
                    record_modal_error(route_name or func.__name__, 'load_error', str(e), user_id)
                except Exception:
                    pass
                
                monitoring_logger.error(
                    f"modal_route={route_name or func.__name__} "
                    f"duration_ms={duration_ms:.2f} "
                    f"status=error "
                    f"error={str(e)} "
                    f"user_id={user_id} "
                    f"modal_enabled={modal_enabled} "
                    f"path={request.path}"
                )
                raise
                
        return wrapper
    return decorator


def log_bundle_usage():
    """Log which bundle was used for this request."""
    try:
        modal_enabled = is_modal_system_enabled()
        bundle_type = 'unified' if modal_enabled else 'legacy'
        user_id = session.get('user_id', 'anonymous')
        
        modal_metrics.record_bundle_load(bundle_type)
        modal_metrics.record_feature_flag_check()
        
        monitoring_logger.debug(
            f"bundle_load=true "
            f"bundle_type={bundle_type} "
            f"user_id={user_id} "
            f"modal_enabled={modal_enabled} "
            f"path={request.path}"
        )
        
    except Exception as e:
        monitoring_logger.error(f"Failed to log bundle usage: {e}")


def get_monitoring_stats():
    """Get comprehensive monitoring statistics."""
    stats = modal_metrics.get_stats()
    
    # Add feature flag distribution
    total_checks = stats['feature_flag_checks']
    unified_pct = (stats['bundle_loads']['unified'] / total_checks * 100) if total_checks > 0 else 0
    legacy_pct = (stats['bundle_loads']['legacy'] / total_checks * 100) if total_checks > 0 else 0
    
    stats['rollout_stats'] = {
        'unified_percentage': unified_pct,
        'legacy_percentage': legacy_pct,
        'total_requests': total_checks
    }
    
    # Add performance thresholds
    avg_load_time = stats['average_load_time']
    stats['performance_alerts'] = {
        'slow_loads': avg_load_time > 500,  # > 500ms
        'high_error_rate': (stats['modal_errors'] / max(stats['modal_loads'], 1)) > 0.05  # > 5%
    }
    
    return stats


def create_monitoring_dashboard_data():
    """Create data structure for monitoring dashboard."""
    stats = get_monitoring_stats()
    
    return {
        'feature_flags': {
            'modal_system_enabled': current_app.config.get('MODAL_SYSTEM_ENABLED', True),
            'modal_system_debug': current_app.config.get('MODAL_SYSTEM_DEBUG', False),
            'canary_percentage': current_app.config.get('MODAL_SYSTEM_CANARY_PCT', 100)
        },
        'performance': {
            'average_load_time_ms': stats['average_load_time'],
            'total_modal_loads': stats['modal_loads'],
            'error_count': stats['modal_errors'],
            'error_rate_pct': (stats['modal_errors'] / max(stats['modal_loads'], 1)) * 100
        },
        'rollout': stats['rollout_stats'],
        'alerts': stats['performance_alerts'],
        'bundle_distribution': stats['bundle_loads']
    }