from flask import Flask, render_template, send_from_directory, send_file, request, jsonify, make_response
import os
import datetime
import json
import logging
import time
import re
import threading
import base64
from collections import OrderedDict

app = Flask(__name__, static_folder='static', template_folder='templates')
BASE_DIR = '/nfs/hatops/ar0/hatpi-website'
EXCLUDE_FOLDERS = set(['fix_json', 'download_sandbox' ,'static', 'templates', 'images', '.git', '__pycache__', 'scripts', 'movies', 'logs', 'markup_images', 'SUB', 'RED', 'data', 'calframe_test'])

for folder in os.listdir(BASE_DIR):
    if folder.startswith('ihu'):
        EXCLUDE_FOLDERS.add(folder)

COMMENTS_FILE = '/nfs/hatops/ar0/hatpi-website/comments.json'
SAVE_PATH = '/nfs/hatops/ar0/hatpi-website/markup_images'
KEYBOARD_FLAGS_FILE = '/nfs/hatops/ar0/hatpi-website/keyboard_flags.json'

logging.basicConfig(level=logging.DEBUG)

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
    cached_result = cache.get(base_dir)
    if cached_result:
        return cached_result

    folders = []
    for folder in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder)
        if os.path.isdir(folder_path) and folder not in EXCLUDE_FOLDERS:
            creation_date = get_creation_date(folder_path)
            folders.append((folder, creation_date))
    folders.sort(key=lambda x: x[0], reverse=True)
    cache.put(base_dir, folders)
    return folders

def format_folder_name(value):
    parts = value.split('-')
    if len(parts) == 2 and len(parts[1]) == 8:
        return "%s-%s-%s" % (parts[1][:4], parts[1][4:6], parts[1][6:])
    return value

def format_filename(value):
    if value.endswith('.jpg'):
        parts = value.split('-')
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

        ihu_match = re.search(r'ihu-(\d+)', value)
        ihu_part = ihu_match.group(1) if ihu_match else 'IHU-'

    elif value.endswith('.html'):
        parts = value.split('_')
        date_part = parts[0][2:6] + '-' + parts[0][6:8] + '-' + parts[0][8:10]

        if 'aper_phot_quality' in value:
            type_part = 'aper phot quality'
        elif 'astrometry_sip_quality' in value:
            type_part = 'astrometry SIP quality'
        elif 'astrometry_wcs_quality' in value:
            type_part = 'astrometry WCS quality'
        elif 'calframe_quality' in value:
            type_part = 'calframe quality'
        elif 'ihu_status' in value:
            type_part = 'IHU status'
        elif 'psf_sources_model' in value:
            type_part = 'PSF sources model'
        elif 'subframe_quality' in value:
            type_part = 'subframe quality'
        elif 'telescope_status' in value:
            type_part = 'Telescope Status'
        else:
            type_part = 'unknown'

        ihu_match = re.search(r'_(\d+)_', value)
        ihu_part = ihu_match.group(1) if ihu_match else 'IHU-'

        # Specific check for Telescope Status type
        if type_part == 'Telescope Status':
            return "%s | %s" % (date_part, type_part)

    elif value.endswith('.mp4'):
        parts = value.split('_')
        date_part = parts[0][2:6] + '-' + parts[0][6:8] + '-' + parts[0][8:10]

        if 'calframe_movie' in value:
            type_part = 'calframe'
        elif 'calframe_stamps_movie' in value:
            type_part = 'calframe stamps'
        elif 'subframe_stamps_movie' in value:
            type_part = 'subframe stamps'
        elif 'subframe_movie' in value:
            type_part = 'subframe'
        else:
            type_part = 'unknown'

        ihu_match = re.search(r'_(\d+)_', value)
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
    folder_path = os.path.join(BASE_DIR, folder_name)
    images, html_files, movies = get_cached_files(folder_path)

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
    return jsonify({'images': images, 'html_files': html_files, 'movies': movies})

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

    cached_entry = cache.get(folder_path)  # cached_entry := (mtime, (img, html, mov))
    if cached_entry and cached_entry[0] == folder_mtime:
        logging.info(
            "get_cached_files – served from cache in %.3f s",
            time.time() - start_time,
        )
        return cached_entry[1]

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
    cache.put(folder_path, (folder_mtime, (images, html_files, movies)))

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
    folder_path = os.path.join(BASE_DIR, folder_name)
    images, html_files, movies = get_cached_files(folder_path)

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
