"""Asset versioning and optimization utilities."""
import os
import hashlib
from functools import lru_cache
from flask import current_app, url_for
from datetime import datetime


class AssetManager:
    """Manage static asset versioning and caching."""
    
    _file_hashes = {}
    _last_check = {}
    
    @classmethod
    def get_file_hash(cls, filepath: str) -> str:
        """Get MD5 hash of file for cache busting."""
        try:
            # Full path to the static file
            full_path = os.path.join(current_app.static_folder, filepath)
            
            if not os.path.exists(full_path):
                current_app.logger.warning(f"Static file not found: {filepath}")
                return "missing"
            
            # Get file modification time
            mtime = os.path.getmtime(full_path)
            
            # Check if we need to recalculate hash
            if filepath in cls._last_check and cls._last_check[filepath] == mtime:
                return cls._file_hashes[filepath]
            
            # Calculate MD5 hash of file contents
            with open(full_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()[:8]  # First 8 chars
            
            # Cache the result
            cls._file_hashes[filepath] = file_hash
            cls._last_check[filepath] = mtime
            
            return file_hash
            
        except Exception as e:
            current_app.logger.error(f"Error generating hash for {filepath}: {e}")
            # Fallback to timestamp
            return str(int(datetime.now().timestamp()))[-8:]
    
    @classmethod
    def versioned_url(cls, filename: str, **kwargs) -> str:
        """Generate versioned URL for static asset."""
        # Get file hash
        file_hash = cls.get_file_hash(filename)
        
        try:
            # Generate base URL using Flask's url_for
            base_url = url_for('static', filename=filename, **kwargs)
        except RuntimeError:
            # Fallback when outside request context
            base_url = f"/static/{filename}"
        
        # Add hash as version parameter
        separator = '&' if '?' in base_url else '?'
        return f"{base_url}{separator}v={file_hash}"
    
    @classmethod
    def clear_cache(cls):
        """Clear internal caches."""
        cls._file_hashes.clear()
        cls._last_check.clear()


def versioned_static(filename: str, **kwargs) -> str:
    """Template helper for versioned static URLs."""
    return AssetManager.versioned_url(filename, **kwargs)


def get_asset_manifest():
    """Generate asset manifest for Service Worker precaching."""
    static_folder = current_app.static_folder
    if not static_folder or not os.path.exists(static_folder):
        return []
    
    assets = []
    
    # Common asset patterns to include
    include_patterns = [
        'css/*.css',
        'js/*.js', 
        'js/entries/*.js',
        'js/modules/*.js',
        'icons/*',
        'vendor/bootstrap/*.css',
        'vendor/bootstrap/*.js',
        'vendor/bootstrap-icons/*.css',
        'manifest.json',
        'manifest.webmanifest'
    ]
    
    for pattern in include_patterns:
        pattern_path = pattern.replace('*', '')
        if '/' in pattern_path:
            # Directory pattern
            base_dir, ext_pattern = pattern_path.rsplit('/', 1)
            full_dir = os.path.join(static_folder, base_dir)
            
            if os.path.exists(full_dir):
                for file in os.listdir(full_dir):
                    if ext_pattern == '' or file.endswith(ext_pattern.replace('*', '')):
                        rel_path = f"{base_dir}/{file}"
                        url = f"/static/{rel_path}"
                        file_hash = AssetManager.get_file_hash(rel_path)
                        assets.append({
                            'url': f"{url}?v={file_hash}",
                            'path': rel_path,
                            'hash': file_hash
                        })
        else:
            # Single file
            if os.path.exists(os.path.join(static_folder, pattern)):
                url = f"/static/{pattern}"
                file_hash = AssetManager.get_file_hash(pattern)
                assets.append({
                    'url': f"{url}?v={file_hash}",
                    'path': pattern,
                    'hash': file_hash
                })
    
    return assets


# Template globals
def init_asset_helpers(app):
    """Initialize asset helpers for templates."""
    app.jinja_env.globals['versioned_static'] = versioned_static
    app.jinja_env.globals['asset_manifest'] = get_asset_manifest