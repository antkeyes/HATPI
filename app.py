from flask import Flask, render_template, send_from_directory, send_file, request, jsonify, make_response, url_for
import os
import datetime
import json
import logging
import time
import re
import threading
import base64
import hashlib
from collections import OrderedDict

app = Flask(__name__, static_folder='static', template_folder='templates')
BASE_DIR = '/nfs/hatops/ar0/hatpi-website'
EXCLUDE_FOLDERS = set(['fix_json', 'download_sandbox' ,'static', 'templates', 'images', '.git', '__pycache__', 'scripts', 'movies', 'logs', 'markup_images', 'SUB', 'RED', 'data', 'calframe_test', 'daily', 'systemd'])

for folder in os.listdir(BASE_DIR):
    if folder.startswith('ihu'):
        EXCLUDE_FOLDERS.add(folder)

COMMENTS_FILE = '/nfs/hatops/ar0/hatpi-website/comments.json'
SAVE_PATH = '/nfs/hatops/ar0/hatpi-website/markup_images'
KEYBOARD_FLAGS_FILE = '/nfs/hatops/ar0/hatpi-website/keyboard_flags.json'

logging.basicConfig(level=logging.DEBUG)

# Generate cache-busting version at startup
def generate_cache_version():
    """Generate a unique version identifier for cache busting"""
    timestamp = str(int(time.time()))
    # Use a combination of timestamp and a hash of the main script
    try:
        with open(__file__, 'rb') as f:
            script_hash = hashlib.md5(f.read()).hexdigest()[:8]
    except:
        script_hash = hashlib.md5(timestamp.encode()).hexdigest()[:8]
    return f"{timestamp}_{script_hash}"

# Global cache version - generated once at startup
CACHE_VERSION = generate_cache_version()
logging.info(f"Cache-busting version generated: {CACHE_VERSION}")

# Template function to add version to static URLs
@app.template_global()
def versioned_url_for(endpoint, **values):
    """Generate URLs with cache-busting version parameter"""
    if endpoint == 'static':
        filename = values.get('filename', '')
        # Check if it's a CSS or JS file that needs versioning
        if filename.endswith(('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico')):
            return f"/hatpi/static/{filename}?v={CACHE_VERSION}"
        else:
            return f"/hatpi/static/{filename}"
    # For non-static endpoints, try to use url_for but fallback gracefully
    try:
        return url_for(endpoint, **values)
    except:
        # If url_for fails, return a simple string (shouldn't happen for static files)
        return f"/{endpoint}"

# Make cache version available to all templates
@app.context_processor
def inject_cache_version():
    """Make cache version available in all templates"""
    return {'cache_version': CACHE_VERSION}

# Custom static file route - must be defined early to avoid conflicts with catch-all routes
@app.route('/hatpi/static/<path:filename>')
def custom_static(filename):
    """Serve static files with proper cache control"""
    try:
        return send_from_directory(app.static_folder, filename)
    except Exception as e:
        app.logger.error(f"Error serving static file {filename}: {str(e)}")
        return "File not found", 404

class LRUCache:
    def __init__(self, capacity=128):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key not in self.cache:
            return None
        value = self.cache.pop(key)
        self.cache[key] = value
        return value

    def put(self, key, value):
        if key in self.cache:
            self.cache.pop(key)
        elif len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)
        self.cache[key] = value

    def clear(self):
        self.cache.clear()

cache = LRUCache()

def get_cached_dir_list(base_dir):
    """
    Return the list of (folder_name, creation_date_str) for BASE_DIR.
    Uses a short TTL so new date folders appear without restarting the app.
    """
    ROOT_DIR_CACHE_TTL_SECONDS = 15

    cached_entry = cache.get(base_dir)  # cached_entry := (cached_at_epoch, folders)
    if cached_entry:
        try:
            cached_at, folders = cached_entry
            if (time.time() - cached_at) < ROOT_DIR_CACHE_TTL_SECONDS:
                return folders
        except Exception:
            # Fall through and rebuild cache on any unexpected structure
            pass

    folders = []
    for folder in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder)
        if os.path.isdir(folder_path) and folder not in EXCLUDE_FOLDERS:
            creation_date = get_creation_date(folder_path)
            folders.append((folder, creation_date))
    folders.sort(key=lambda x: x[0], reverse=True)
    cache.put(base_dir, (time.time(), folders))
    return folders

def format_folder_name(value):
    parts = value.split('-')
    if len(parts) == 2 and len(parts[1]) == 8:
        return "%s-%s-%s" % (parts[1][:4], parts[1][4:6], parts[1][6:])
    return value

def format_filename(value):
    # Check if this is a RED/SUB file path
    if '/RED/' in value or '/SUB/' in value:
        # Parse RED/SUB file path: e.g., "/hatpi/RED/1-20250216/ihu50/1-487919_50-red-bin4.jpg"
        path_parts = value.split('/')
        filename = path_parts[-1]  # e.g., "1-487919_50-red-bin4.jpg"
        
        # Extract date from folder path (e.g., "1-20250216" -> "2025-02-16")
        date_folder = None
        for part in path_parts:
            if part.startswith('1-') and len(part) == 10:
                date_folder = part
                break
        
        if date_folder:
            date_part = date_folder[2:6] + '-' + date_folder[6:8] + '-' + date_folder[8:10]
        else:
            date_part = 'unknown-date'
        
        # Determine type (reduction/subtraction)
        if '-red-' in filename.lower():
            type_part = 'reduction'
        elif '-sub-' in filename.lower():
            type_part = 'subtraction'
        else:
            type_part = 'unknown'
        
        # Extract subtype (e.g., "twilight", "object", etc.)
        subtype_match = re.search(r'-(?:red|sub)-([^-]+?)-bin', filename, re.IGNORECASE)
        if subtype_match:
            subtype = subtype_match.group(1).capitalize()
            type_part = type_part + ' | ' + subtype
        
        # Extract IHU from folder path (e.g., "ihu50" -> "IHU-50")
        ihu_folder = None
        for part in path_parts:
            if part.startswith('ihu') and len(part) >= 4:
                ihu_folder = part
                break
        
        if ihu_folder:
            ihu_num = ihu_folder[3:]  # Remove "ihu" prefix
            ihu_part = ihu_num.zfill(2)  # Pad with zero if needed
        else:
            ihu_part = 'unknown'
        
        # Extract frame number
        frame_match = re.search(r'1-(\d+)_', filename)
        if frame_match:
            frame_part = 'frame: ' + frame_match.group(1)
            return "%s | %s | IHU-%s | %s" % (date_part, type_part, ihu_part, frame_part)
        else:
            return "%s | %s | IHU-%s" % (date_part, type_part, ihu_part)
    
    # Original logic for calibration files (extract filename from path if needed)
    if '/' in value:
        filename = value.split('/')[-1]
    else:
        filename = value
    
    if filename.endswith('.jpg'):
        parts = filename.split('-')
        date_part = parts[3][:4] + '-' + parts[3][4:6] + '-' + parts[3][6:8]

        if 'bias' in parts[0]:
            type_part = 'bias'
        elif 'dark' in parts[0]:
            type_part = 'dark'
        elif 'masterglobflat' in parts[0] and 'ss' in parts[-1]:
            type_part = 'globflat ss'
        elif 'masterglobflat' in parts[0] and 'ls' in parts[-1]:
            type_part = 'globflat ls'
        elif 'masterflat' in parts[0] and 'ss' in parts[-1]:
            type_part = 'flat'
        elif 'masterflat' in parts[0] and 'ls' in parts[-1]:
            type_part = 'flat ls'
        else:
            type_part = 'unknown'

        ihu_match = re.search(r'ihu-(\d+)', filename)
        ihu_part = ihu_match.group(1) if ihu_match else 'IHU-'

    elif filename.endswith('.html'):
        parts = filename.split('_')
        date_part = parts[0][2:6] + '-' + parts[0][6:8] + '-' + parts[0][8:10]

        if 'aper_phot_quality' in filename:
            type_part = 'aper phot quality'
        elif 'astrometry_sip_quality' in filename:
            type_part = 'astrometry SIP quality'
        elif 'astrometry_wcs_quality' in filename:
            type_part = 'astrometry WCS quality'
        elif 'calframe_quality' in filename:
            type_part = 'calframe quality'
        elif 'ihu_status' in filename:
            type_part = 'IHU status'
        elif 'psf_sources_model' in filename:
            type_part = 'PSF sources model'
        elif 'subframe_quality' in filename:
            type_part = 'subframe quality'
        elif 'telescope_status' in filename:
            type_part = 'Telescope Status'
        else:
            type_part = 'unknown'

        ihu_match = re.search(r'_(\d+)_', filename)
        ihu_part = ihu_match.group(1) if ihu_match else 'IHU-'

        # Specific check for Telescope Status type
        if type_part == 'Telescope Status':
            return "%s | %s" % (date_part, type_part)

    elif filename.endswith('.mp4'):
        parts = filename.split('_')
        date_part = parts[0][2:6] + '-' + parts[0][6:8] + '-' + parts[0][8:10]

        if 'calframe_movie' in filename:
            type_part = 'calframe'
        elif 'calframe_stamps_movie' in filename:
            type_part = 'calframe stamps'
        elif 'subframe_stamps_movie' in filename:
            type_part = 'subframe stamps'
        elif 'subframe_movie' in filename:
            type_part = 'subframe'
        else:
            type_part = 'unknown'

        ihu_match = re.search(r'_(\d+)_', filename)
        ihu_part = ihu_match.group(1) if ihu_match else 'IHU-'

    else:
        return value

    formatted_string = "%s | %s | IHU-%s" % (date_part, type_part, ihu_part)
    return formatted_string

app.jinja_env.filters['format_folder'] = format_folder_name
app.jinja_env.filters['format_filename'] = format_filename

previous_state = set()

def poll_directory():
    global previous_state
    while True:
        current_state = set()
        for folder in os.listdir(BASE_DIR):
            folder_path = os.path.join(BASE_DIR, folder)
            if os.path.isdir(folder_path) and folder not in EXCLUDE_FOLDERS:
                current_state.add(folder_path)

        if current_state != previous_state:
            cache.clear()
            print("Cache cleared due to directory change")
            previous_state = current_state
        
        time.sleep(1800)
        
def group_comments_by_author(comments):
    grouped = {}
    for key, comment in comments.items():
        author = comment.get('author', 'Unknown')
        if author not in grouped:
            grouped[author] = []
        grouped[author].append({
            'unique_key': key,
            'file_path': comment.get('file_path'),
            'comment': comment.get('comment'),
            'timestamp': comment.get('timestamp'),
            'markup_true': comment.get('markup_true'),
            'flags': comment.get('flags', []) #making sure to default to empty list if no flags tagged on image
        })
    return grouped

@app.route('/')
def home():
    start_time = time.time()
    folders = get_cached_dir_list(BASE_DIR)
    comments = load_comments() or {}
    comments_by_author = group_comments_by_author(comments)
    logging.info("Rendering template with folders: %s and comments: %s" % (folders, comments))
    logging.info("Home route processing time: %s seconds" % (time.time() - start_time))
    return render_template('index.html', folders=folders, comments_by_author=comments_by_author)

@app.route('/<folder_name>/')
def folder(folder_name):
    # Avoid expensive full directory scans at render time; the page JS will
    # load items via /api/folder with pagination.
    images, html_files, movies = [], [], []

    keyboard_flags = load_keyboard_flags()
    flagged_for_folder = []

    # Correctly aligned for-loop:
    for fullpath, flag_data in keyboard_flags.items():
        if folder_name in fullpath:
            flagged_for_folder.append({
                "file_path": fullpath,
                "flags": flag_data.get("flags", []),
                "timestamp": flag_data.get("timestamp", ""),
                "author": flag_data.get("author", "")
            })

    return render_template(
        'folder.html',
        images=images,
        html_files=html_files,
        movies=movies,
        folder_name=folder_name,
        flagged_items=flagged_for_folder
    )


@app.route('/api/folder/<path:folder_name>')
def api_folder(folder_name):
    folder_path = os.path.join(BASE_DIR, folder_name)
    images, html_files, movies = get_cached_files(folder_path)

    # Backward-compatible default: if no 'limit' provided, return full arrays
    limit_raw = request.args.get('limit')
    if not limit_raw:
        return jsonify({'images': images, 'html_files': html_files, 'movies': movies})

    # Pagination mode
    try:
        limit = max(1, min(1000, int(limit_raw)))
    except ValueError:
        limit = 200

    # Optional single-category fetch for lazy loading
    category = request.args.get('category')  # 'images' | 'html_files' | 'movies'
    if category:
        offset = int(request.args.get('offset', 0))
        data_map = {'images': images, 'html_files': html_files, 'movies': movies}
        items = data_map.get(category, [])
        sliced = items[offset: offset + limit]
        has_more = (offset + limit) < len(items)
        next_offset = offset + len(sliced)
        return jsonify({
            'category': category,
            'items': sliced,
            'has_more': has_more,
            'next_offset': next_offset,
            'total': len(items),
        })

    # Multi-category initial page
    offset_images = int(request.args.get('offset_images', 0))
    offset_html   = int(request.args.get('offset_html', 0))
    offset_movies = int(request.args.get('offset_movies', 0))

    images_slice = images[offset_images: offset_images + limit]
    html_slice   = html_files[offset_html: offset_html + limit]
    movies_slice = movies[offset_movies: offset_movies + limit]

    return jsonify({
        'images': images_slice,
        'html_files': html_slice,
        'movies': movies_slice,
        'has_more': {
            'images': (offset_images + limit) < len(images),
            'html_files': (offset_html + limit) < len(html_files),
            'movies': (offset_movies + limit) < len(movies),
        },
        'next_offsets': {
            'images': offset_images + len(images_slice),
            'html_files': offset_html + len(html_slice),
            'movies': offset_movies + len(movies_slice),
        },
        'totals': {
            'images': len(images),
            'html_files': len(html_files),
            'movies': len(movies),
        }
    })

def is_date_based_folder(folder_name):
    return re.match(r'\d{4}-\d{2}-\d{2}', folder_name) is not None

def extract_ihu_number(filename):
    """
    Pull the IHU index (1-64) out of any filename pattern we use:
      • "…_51_…", "…_51.html", "…_51-calframe…"   (date folders)
      • "…ihu-51-…", "…ihu-51_…"                   (ihu-## folders)
    Returns the integer, or ∞ so non-matches drop to the end.
    """
    match = re.search(r'(?:_|ihu-)(\d{1,2})(?:[_\.\-])', filename)
    return int(match.group(1)) if match else float("inf")



def parse_file_date(filename):
    """
    Extract a date (YYYYMMDD) from the filename and return a datetime object.
    Return None if no date is found.
    """
    match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return datetime.datetime(year, month, day)
    return None

def get_cached_files(folder_path: str):
    """
    Return three lists – images, html_files, movies – for *folder_path*.
    Each list contains tuples of the form (filename, creation_date_str).

    Key points for speed:

    1.  Use os.scandir once (45–60× fewer syscalls than os.listdir + os.stat).
    2.  Avoid os.stat entirely for typical IHU folders; parse the date that
        already sits in every filename.
    3.  Store a (folder_mtime, data) tuple in the cache so we only re-scan
        when that specific directory has changed.
    """

    start_time = time.time()

    # ---- 0. Quick cache hit -------------------------------------------------
    try:
        folder_mtime = os.path.getmtime(folder_path)
    except FileNotFoundError as e:
        logging.error("get_cached_files – folder does not exist: %s", folder_path)
        return [], [], []

    # Cache entry layout: (cached_mtime, (images, html_files, movies), cached_at_epoch)
    cached_entry = cache.get(folder_path)
    if cached_entry:
        try:
            cached_mtime, cached_data, cached_at = cached_entry
            # Serve if mtime unchanged
            if cached_mtime == folder_mtime:
                logging.info(
                    "get_cached_files – served from cache in %.3f s",
                    time.time() - start_time,
                )
                return cached_data
            # Short TTL fallback to reduce rescans on frequently updated dirs (e.g., IHU)
            PER_FOLDER_CACHE_TTL_SECONDS = 15
            if (time.time() - cached_at) < PER_FOLDER_CACHE_TTL_SECONDS:
                logging.info(
                    "get_cached_files – served slightly stale (TTL) in %.3f s",
                    time.time() - start_time,
                )
                return cached_data
        except Exception:
            # Ignore malformed cache entry and rebuild
            pass

    # ---- 1. Decide which filename-parsing rules apply -----------------------
    is_ihu_folder   = "/nfs/hatops/ar0/hatpi-website/ihu-" in folder_path
    is_date_folder  = bool(re.match(r'/nfs/hatops/ar0/hatpi-website/1-\d{8}', folder_path))

    # ---- 2. One fast scan with os.scandir -----------------------------------
    images_tmp:  list[tuple[str, datetime.datetime, str]] = []  # (fname, dt, dt_str)
    html_tmp:    list[tuple[str, datetime.datetime, str]] = []
    movies_tmp:  list[tuple[str, datetime.datetime, str]] = []

    try:
        with os.scandir(folder_path) as it:
            for de in it:                           # DirEntry gives stat() for free
                if not de.is_file():
                    continue
                fname = de.name
                ext   = os.path.splitext(fname)[1].lower()

                # 2.a. derive the timestamp -------------------------------
                if is_ihu_folder:
                    dt = parse_file_date(fname) or datetime.datetime.min
                else:
                    # stat() is cached inside the DirEntry after first access
                    dt = datetime.datetime.fromtimestamp(de.stat().st_mtime)

                dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')

                # 2.b. bucket by file type --------------------------------
                if ext == '.jpg':
                    images_tmp.append((fname, dt, dt_str))
                elif ext == '.html':
                    html_tmp.append((fname, dt, dt_str))
                elif ext == '.mp4':
                    movies_tmp.append((fname, dt, dt_str))
    except Exception as e:
        logging.error("get_cached_files – error reading %s: %s", folder_path, e)
        return [], [], []

    # ---- 3. Sorting ---------------------------------------------------------
    if is_ihu_folder:
        images_tmp.sort(key=lambda x: x[1], reverse=True)
        html_tmp.sort(
            key=lambda x: (0 if 'telescope_status' in x[0] else 1, x[1]),
            reverse=True,
        )
        movies_tmp.sort(key=lambda x: x[1], reverse=True)

    elif is_date_folder:
        images_tmp.sort(key=lambda x: extract_ihu_number(x[0]))
        html_tmp.sort(
            key=lambda x: (0 if 'telescope_status' in x[0] else 1,
                           extract_ihu_number(x[0])),
        )
        movies_tmp.sort(key=lambda x: extract_ihu_number(x[0]))

    else:   # generic fallback – newest first
        images_tmp.sort(key=lambda x: x[1], reverse=True)
        html_tmp.sort(  key=lambda x: x[1], reverse=True)
        movies_tmp.sort(key=lambda x: x[1], reverse=True)

    # ---- 4. Strip the extra dt object for template compatibility -----------
    images      = [(f, s) for (f, _, s) in images_tmp]
    html_files  = [(f, s) for (f, _, s) in html_tmp]
    movies      = [(f, s) for (f, _, s) in movies_tmp]

    # ---- 5. Cache & return --------------------------------------------------
    cache.put(folder_path, (folder_mtime, (images, html_files, movies), time.time()))

    logging.info(
        "get_cached_files – scanned %s in %.3f s – items: %d jpg, %d html, %d mp4",
        folder_path, time.time() - start_time, len(images), len(html_files), len(movies)
    )
    return images, html_files, movies


@app.route("/lcplots")
@app.route("/lcplots/")
def lcplots():
    """List the contents of the LCPLOT directory"""
    lcplot_dir = "/nfs/php2/ar0/P/HP1/REDUCTION/LCPLOT"
    
    files = []
    directories = []

    try:
        # First, get all items in the main directory
        for item_name in sorted(os.listdir(lcplot_dir)):
            item_path = os.path.join(lcplot_dir, item_name)
            
            # If it's a file, add it directly
            if os.path.isfile(item_path):
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(item_path))
                formatted_time = mod_time.strftime('%Y-%m-%d %H:%M:%S')
                
                size_bytes = os.path.getsize(item_path)
                size_mb = size_bytes / (1024 * 1024)
                
                files.append({
                    'name': item_name,
                    'path': f"/hatpi/lcplots/{item_name}",
                    'modified': formatted_time,
                    'size': f"{size_mb:.2f} MB",
                    'is_dir': False
                })
            
            # If it's a directory, add it and its files
            elif os.path.isdir(item_path):
                # Add the directory itself first
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(item_path))
                formatted_time = mod_time.strftime('%Y-%m-%d %H:%M:%S')
                
                dir_entry = {
                    'name': item_name,
                    'path': f"/hatpi/lcplots/{item_name}",  # Changed from lcplot to lcplots to match route
                    'modified': formatted_time,
                    'size': "-",
                    'is_dir': True
                }
                directories.append(dir_entry)
    except Exception as e:
        app.logger.error(f"Error reading LCPLOT directory: {str(e)}")
    
    # Combine directories and files, with directories first
    all_items = directories + files
    return render_template("lcplots.html", files=all_items)

@app.route('/lcplots/<path:filepath>')
def lcplots_filepath(filepath):
    """Alternate route for the lcplots page when accessed directly through Flask without the /hatpi prefix"""
    # Just redirect to the main handler
    return serve_lcplot(filepath)

@app.route('/hatpi/lcplots/<path:filepath>')  # Changed from lcplot to lcplots to match other routes
def serve_lcplot(filepath):
    """Serve files from the LCPLOT directory"""
    lcplot_dir = "/nfs/php2/ar0/P/HP1/REDUCTION/LCPLOT"
    
    # Log the request for debugging
    app.logger.info(f"Serving LCPLOT: {filepath}")
    
    # Handle virtual category paths
    path_parts = filepath.split('/')
    
    # Categories to filter by
    first_level_categories = ['aperphot', 'subphot']
    second_level_categories = ['aper0', 'aper1', 'aper2', 'bad_epochs', 'template_selection']
    third_level_categories = ['base', 'binned', 'binned_curves']
    
    # Initialize filter and real path
    filters = []
    real_path = filepath
    
    # Extract filters from path
    if len(path_parts) > 1:
        # Check for first level filter (aperphot/subphot)
        if path_parts[-1] in first_level_categories:
            # We're at the first level of filtering
            filters.append(path_parts[-1])
            real_path = '/'.join(path_parts[:-1])
        elif len(path_parts) > 2 and path_parts[-2] in first_level_categories and path_parts[-1] in second_level_categories:
            # We're at the second level of filtering
            filters.append(path_parts[-2])  # First level category (aperphot/subphot)
            filters.append(path_parts[-1])  # Second level category (aper0/aper1/etc)
            real_path = '/'.join(path_parts[:-2])
        elif len(path_parts) > 3 and path_parts[-3] in first_level_categories and path_parts[-2] in second_level_categories and path_parts[-1] in third_level_categories:
            # We're at the third level of filtering
            filters.append(path_parts[-3])  # First level category (aperphot/subphot)
            filters.append(path_parts[-2])  # Second level category (aper0/aper1/etc)
            filters.append(path_parts[-1])  # Third level category (base/binned/binned_curves)
            real_path = '/'.join(path_parts[:-3])
    
    app.logger.info(f"Using filters: {filters}, real path: {real_path}")
    
    # Securely join the path to prevent directory traversal attacks
    file_path = os.path.normpath(os.path.join(lcplot_dir, real_path))
    
    # Check if path is still under the LCPLOT directory to prevent directory traversal
    if not file_path.startswith(lcplot_dir):
        return "Access denied", 403
    
    if not os.path.exists(file_path):
        app.logger.error(f"File not found: {file_path}")
        return "File not found", 404
    
    if os.path.isdir(file_path):
        subfiles = []
        subdirs = []
        
        # Check if this is a direct IHU directory (not a subcategory yet)
        is_ihu_dir = re.match(r'^ihu\d+$', os.path.basename(file_path)) is not None
        
        # Determine the current level of filtering
        if is_ihu_dir and not filters:
            # Top level of an IHU directory - show first level categories
            for category in first_level_categories:
                subdirs.append({
                    'name': category,
                    'path': f"/hatpi/lcplots/{filepath}/{category}",
                    'modified': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'size': "-",
                    'is_dir': True
                })
        elif len(filters) == 1 and filters[0] in first_level_categories:
            # First level of filtering - show second level categories
            for category in second_level_categories:
                subdirs.append({
                    'name': category,
                    'path': f"/hatpi/lcplots/{filepath}/{category}",
                    'modified': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'size': "-",
                    'is_dir': True
                })
        elif len(filters) == 2 and filters[0] in first_level_categories and filters[1] in ['aper0', 'aper1', 'aper2']:
            # Second level is aper0/1/2 - add the third level of categorization
            subdirs.append({
                'name': 'base',
                'path': f"/hatpi/lcplots/{filepath}/base",
                'modified': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'size': "-",
                'is_dir': True
            })
            subdirs.append({
                'name': 'binned',
                'path': f"/hatpi/lcplots/{filepath}/binned",
                'modified': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'size': "-",
                'is_dir': True
            })
            subdirs.append({
                'name': 'binned_curves',
                'path': f"/hatpi/lcplots/{filepath}/binned_curves",
                'modified': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'size': "-",
                'is_dir': True
            })
        else:
            try:
                # List the actual directory contents
                for item in sorted(os.listdir(file_path)):
                    item_path = os.path.join(file_path, item)
                    
                    # Only add real directories if we're not filtering
                    if os.path.isdir(item_path) and not filters:
                        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(item_path))
                        formatted_time = mod_time.strftime('%Y-%m-%d %H:%M:%S')
                        
                        subdirs.append({
                            'name': item,
                            'path': f"/hatpi/lcplots/{filepath}/{item}",
                            'modified': formatted_time,
                            'size': "-",
                            'is_dir': True
                        })
                    elif os.path.isfile(item_path):
                        # Apply filtering criteria
                        should_include = True
                        
                        # Apply basic filters first
                        if len(filters) >= 2:
                            # Check first two filters (aperphot/subphot and aper0/1/2)
                            for filter_term in filters[:2]:
                                if filter_term not in item:
                                    should_include = False
                                    break
                        
                        # Apply third level filtering if needed
                        if should_include and len(filters) == 3 and filters[1] in ['aper0', 'aper1', 'aper2']:
                            aper_filter = filters[1]  # aper0, aper1, or aper2
                            third_filter = filters[2]  # base, binned, or binned_curves
                            
                            # Handle each third-level filter type
                            if third_filter == 'base':
                                # Include only files like "*_aper0.jpg" without "binned"
                                if not item.endswith(f"_{aper_filter}.jpg") or "_binned" in item:
                                    should_include = False
                            elif third_filter == 'binned':
                                # Include only files like "*_aper0_binned.jpg" without "curves"
                                if not item.endswith(f"_{aper_filter}_binned.jpg") or "_curves" in item:
                                    should_include = False
                            elif third_filter == 'binned_curves':
                                # Include only files like "*_aper0_binned_curves.jpg"
                                if not item.endswith(f"_{aper_filter}_binned_curves.jpg"):
                                    should_include = False
                        
                        # Skip files that don't match our filters
                        if not should_include:
                            continue
                        
                        # Add matching files to our list
                        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(item_path))
                        formatted_time = mod_time.strftime('%Y-%m-%d %H:%M:%S')
                        
                        size_bytes = os.path.getsize(item_path)
                        size_mb = size_bytes / (1024 * 1024)
                        
                        subfiles.append({
                            'name': item,
                            'path': f"/hatpi/lcplots/{real_path}/{item}",
                            'modified': formatted_time,
                            'size': f"{size_mb:.2f} MB",
                            'is_dir': False
                        })
            except Exception as e:
                app.logger.error(f"Error reading directory {file_path}: {str(e)}")
        
        # Combine directories and files for display, with directories first
        all_items = subdirs + subfiles
        
        # Use the original filepath for display in the breadcrumb
        return render_template("lcplots.html", files=all_items, current_dir=filepath)
    
    # If it's a file, serve it
    return send_file(file_path)


@app.route("/skyflats_runtimes")
@app.route("/hatpi/skyflats_runtimes")
def skyflats_runtimes():
    """Serve the Daily Skyflats & Task Runtimes page"""
    daily_dir = "/nfs/hatops/ar0/hatpi-website/daily"
    
    skyflat_files = []
    runtime_files = []
    
    try:
        # Get all files in the daily directory
        for filename in sorted(os.listdir(daily_dir)):
            if filename.endswith('.html'):
                file_path = os.path.join(daily_dir, filename)
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                formatted_time = mod_time.strftime('%Y-%m-%d %H:%M:%S')
                
                if filename.startswith('skyflat_metrics_ihuid_'):
                    # Extract IHU ID from filename
                    ihu_match = re.search(r'skyflat_metrics_ihuid_(\d+)\.html', filename)
                    if ihu_match:
                        ihu_id = ihu_match.group(1)
                        display_name = f"IHU-{ihu_id.zfill(2)} Skyflat Metrics"
                    else:
                        display_name = filename.replace('.html', '').replace('_', ' ').title()
                    
                    skyflat_files.append({
                        'name': filename,
                        'display_name': display_name,
                        'modified': formatted_time
                    })
                
                elif filename.startswith('task_timings_'):
                    # Extract date from filename
                    date_match = re.search(r'task_timings_(\d{8})\.html', filename)
                    if date_match:
                        date_str = date_match.group(1)
                        # Format as YYYY-MM-DD
                        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                        display_name = f"Task Runtimes - {formatted_date}"
                    else:
                        display_name = filename.replace('.html', '').replace('_', ' ').title()
                    
                    runtime_files.append({
                        'name': filename,
                        'display_name': display_name,
                        'modified': formatted_time
                    })
        
        # Sort files - skyflats by IHU ID (ascending), runtimes by date (descending)
        skyflat_files.sort(key=lambda x: int(re.search(r'(\d+)', x['name']).group(1)) if re.search(r'(\d+)', x['name']) else 0)
        runtime_files.sort(key=lambda x: x['name'], reverse=True)
        
    except Exception as e:
        app.logger.error(f"Error reading daily directory: {str(e)}")
    
    return render_template("skyflats_runtimes.html", 
                         skyflat_files=skyflat_files, 
                         runtime_files=runtime_files)


@app.route('/hatpi/daily/<filename>')
def serve_daily_file(filename):
    """Serve files from the daily directory"""
    daily_dir = "/nfs/hatops/ar0/hatpi-website/daily"
    file_path = os.path.join(daily_dir, filename)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_file(file_path)
    else:
        return "File not found", 404


@app.route('/hatpi/comments.json')
def get_comments():
    try:
        with open(COMMENTS_FILE, 'r') as file:
            comments = json.load(file)
        return jsonify(comments)
    except Exception as e:
        app.logger.error("Error loading comments: {}".format(str(e)))
        return jsonify({})

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    
    # Add cache control headers for static files
    if request.endpoint == 'custom_static' or request.endpoint == 'static':
        # Check if it's a versioned file (has 'v=' parameter) 
        query_string = request.query_string.decode()
        if 'v=' in query_string and CACHE_VERSION in query_string:
            # Versioned files - cache for 1 year since they'll change URL when updated
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            # Remove no-cache headers if they exist
            response.headers.pop('Pragma', None)
            response.headers.pop('Expires', None)
        else:
            # Non-versioned files - no cache to ensure fresh content
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
    
    return response

@app.route('/api/save_markups', methods=['POST'])
def save_markups():
    try:
        data = request.get_json()
        file_name = data['fileName']
        image_data = data['imageData']
        comment = data.get('comment', '')
        author = data.get('author', '')
        markup_true = data.get('markup_true')
        flags = data.get('flags', [])

        if not comment:
            return jsonify(success=False, message="Comment is required")

        image_data = image_data.replace('data:image/jpeg;base64,', '')
        image_data = base64.b64decode(image_data)

        if not os.path.exists(SAVE_PATH):
            os.makedirs(SAVE_PATH)

        save_file_path = os.path.join(SAVE_PATH, file_name)
        with open(save_file_path, 'wb') as f:
            f.write(image_data)

        comments = load_comments()
        unique_key = '%s_%s' % (file_name, datetime.datetime.now().strftime('%Y%m%d%H%M%S%f'))
        comments[unique_key] = {
            'comment': comment,
            'author': author,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'file_path': '/hatpi/markup_images/%s' % file_name,
            'markup_true': markup_true,
            'flags': flags
        }
        save_comments(comments)

        return jsonify(success=True)
    except Exception as e:
        app.logger.error("Error saving markups: {}".format(str(e)))
        return jsonify(success=False, message=str(e))

@app.route('/<folder_name>/<filename>')
def file(folder_name, filename):
    app.logger.info(f"Catch-all route called with folder_name='{folder_name}', filename='{filename}'")
    
    # Handle static file requests that got caught by this catch-all route
    if folder_name == 'hatpi' and filename.startswith('static/'):
        app.logger.info(f"Detected static file request, redirecting to custom_static")
        # Extract the actual filename from "static/filename"
        static_filename = filename[7:]  # Remove "static/" prefix
        app.logger.info(f"Static filename: '{static_filename}'")
        return custom_static(static_filename)
    
    folder_path = os.path.join(BASE_DIR, folder_name)
    file_path = os.path.join(folder_path, filename)

    app.logger.info("Requested file: %s" % file_path)

    if os.path.islink(file_path):
        real_path = os.path.realpath(file_path)
        app.logger.info("Resolved symlink %s to %s" % (file_path, real_path))
        return send_file(real_path)

    return send_from_directory(folder_path, filename)

@app.route('/ihu/ihu-<cell_number>')
def ihu_cell(cell_number):
    folder_name = f'ihu-{cell_number}'
    # Avoid expensive full directory scans at render time; page JS will load via /api/folder
    images, html_files, movies = [], [], []

    # Load keyboard flags
    keyboard_flags = load_keyboard_flags()

    # Because your real folder or your JSON might use "ihu03"
    alt_folder_name = folder_name.replace('ihu-', 'ihu')

    flagged_for_folder = []
    for fullpath, flag_data in keyboard_flags.items():
        # Substring-check for both "ihu-03" and "ihu03"
        if folder_name in fullpath or alt_folder_name in fullpath:
            flagged_for_folder.append({
                "file_path": fullpath,
                "flags": flag_data.get("flags", []),
                "timestamp": flag_data.get("timestamp", ""),
                "author": flag_data.get("author", "")
            })

    return render_template(
        'folder.html',
        folder_name=folder_name,
        images=images,
        html_files=html_files,
        movies=movies,
        flagged_items=flagged_for_folder
    )


@app.route('/submit_comment', methods=['POST'])
def submit_comment():
    data = request.json
    file_name = data.get('fileName')
    file_path = data.get('filePath')
    comment = data.get('comment')
    author = data.get('author')
    markup_true = data.get('markup_true', '')
    flags = data.get('flags', [])
    
    if file_name and comment:
        comments = load_comments()
        unique_key = '%s_%s' % (file_name, datetime.datetime.now().strftime('%Y%m%d%H%M%S%f'))
        comments[unique_key] = {
            'file_path': file_path,
            'comment': comment,
            'author': author,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'markup_true': markup_true,
            'flags': flags
        }
        save_comments(comments)
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/delete_comment', methods=['POST'])
def delete_comment():
    data = request.get_json()
    comment_id = data.get('commentId')
    
    if comment_id:
        comments = load_comments()
        if comment_id in comments:
            del comments[comment_id]
            save_comments(comments)
            return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/RED/<path:subpath>')
def serve_red_path(subpath):
    """
    Example: subpath might be "1-20250216/ihu50/1-487919_50-red-bin4.jpg"
    We'll build the real path under /nfs/hatops/ar0/hatpi-website/RED/...
    """
    import os

    # The base for RED is: /nfs/hatops/ar0/hatpi-website/RED
    red_base = os.path.join(BASE_DIR, 'RED')
    # Then we join subpath => /nfs/hatops/ar0/hatpi-website/RED/1-20250216/ihu50/1-4879...
    target_dir = os.path.join(red_base, os.path.dirname(subpath))
    filename = os.path.basename(subpath)

    # Resolve symlinks
    real_dir = os.path.realpath(target_dir)
    full_file_path = os.path.join(real_dir, filename)

    app.logger.info(f"Serving RED file: {full_file_path}")
    if not os.path.isfile(full_file_path):
        return "Not Found", 404

    # Option 1: use send_file
    from flask import send_file
    return send_file(full_file_path)

    # or Option 2: use send_from_directory if you prefer
    # from flask import send_from_directory
    # return send_from_directory(real_dir, filename, follow_symlinks=True)


@app.route('/SUB/<path:subpath>')
def serve_sub_path(subpath):
    """
    Example: subpath might be "1-20250216/ihu50/1-222222_50-sub-bin4.jpg"
    We'll build the real path under /nfs/hatops/ar0/hatpi-website/SUB/...
    """
    import os

    sub_base = os.path.join(BASE_DIR, 'SUB')
    target_dir = os.path.join(sub_base, os.path.dirname(subpath))
    filename = os.path.basename(subpath)

    real_dir = os.path.realpath(target_dir)
    full_file_path = os.path.join(real_dir, filename)

    app.logger.info(f"Serving SUB file: {full_file_path}")
    if not os.path.isfile(full_file_path):
        return "Not Found", 404

    from flask import send_file
    return send_file(full_file_path)


@app.route('/api/subfolders/<path:folder_name>')
def api_subfolders(folder_name):
    """
    Returns a JSON list of subfolder names (not files) directly inside 'folder_name'.
    This is used by the front-end to show "date" subfolders in the IHU folder's RED or SUB directory.
    E.g. /api/subfolders/ihu-01/RED => ["1-20250213", "1-20250216", ...]
    """
    full_path = os.path.join(BASE_DIR, folder_name)
    if not os.path.isdir(full_path):
        return jsonify({"subfolders": []})

    try:
        entries = os.listdir(full_path)
    except Exception as e:
        app.logger.error(f"Error listing subfolders in {full_path}: {e}")
        return jsonify({"subfolders": []})

    # We only want directories (including symlinks that point to directories).
    subfolders = []
    for entry in entries:
        entry_path = os.path.join(full_path, entry)
        if os.path.isdir(entry_path):
            subfolders.append(entry)

    # Sort them (reverse=False so you get chronological, if you prefer)
    subfolders.sort()
    return jsonify({"subfolders": subfolders})

@app.route('/api/keyboard_flags', methods=['POST'])
def update_keyboard_flags():
    """
    Saves the 'keyboard-selected' flags to a separate file (keyboard_flags.json).
    If the new flags array is empty, removes the entry from the JSON.
    This does NOT require a comment and does NOT appear in comments.json.
    """
    data = request.get_json() or {}
    file_path = data.get('filePath')       # e.g. "/SUB/1-20250216/ihu50/1-4879..."
    new_flags = data.get('flags', [])       # List of flags
    author = "Adriana"                      # hardcoded for now

    # Load the current dictionary of keyboard flags
    kflags = load_keyboard_flags()
    
    # Remove duplicates and sort new flags
    final_flags = sorted(list(set(new_flags)))
    
    if final_flags:
        # If there are flags, update (or add) the entry for this file path
        kflags[file_path] = {
            "flags": final_flags,
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "author": author
        }
    else:
        # If the flags array is empty, remove the entry if it exists
        if file_path in kflags:
            del kflags[file_path]

    # Save the updated dictionary back to the JSON file
    save_keyboard_flags(kflags)

    return jsonify(success=True, flags=final_flags)


@app.route('/hatpi/keyboard_flags.json')
def serve_kb_flags():
    data = load_keyboard_flags()
    return jsonify(data)



def get_creation_date(file_path):
    return datetime.datetime.fromtimestamp(os.path.getctime(file_path)).strftime('%Y-%m-%d %H:%M:%S')

def load_comments():
    if os.path.exists(COMMENTS_FILE):
        try:
            with open(COMMENTS_FILE, 'r') as file:
                comments = json.load(file)
            sorted_comments = OrderedDict(
                sorted(comments.items(), key=lambda item: datetime.datetime.strptime(item[1]['timestamp'], '%Y-%m-%d %H:%M:%S'), reverse=True)
            )
            logging.info("Comments loaded and sorted: %s" % sorted_comments)
            return sorted_comments
        except ValueError as e:
            logging.error("Error loading JSON: %s" % e)
            return {}
    logging.info("No comments file found, returning empty dictionary")
    return {}

def save_comments(comments):
    with open(COMMENTS_FILE, 'w') as file:
        json.dump(comments, file, indent=4)
        
def load_keyboard_flags():
    if os.path.exists(KEYBOARD_FLAGS_FILE):
        try:
            with open(KEYBOARD_FLAGS_FILE, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            app.logger.error(f"Error loading {KEYBOARD_FLAGS_FILE}: {e}")
            return {}
    return {}

def save_keyboard_flags(data):
    try:
        with open(KEYBOARD_FLAGS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        app.logger.error(f"Error saving {KEYBOARD_FLAGS_FILE}: {e}")


if __name__ == '__main__':
    polling_thread = threading.Thread(target=poll_directory)
    polling_thread.daemon = True
    polling_thread.start()
    
    app.run(debug=True, port=8080)
