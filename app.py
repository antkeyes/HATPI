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
EXCLUDE_FOLDERS = set(['download_sandbox' ,'static', 'templates', 'images', '.git', '__pycache__', 'scripts', 'movies', 'logs', 'markup_images', 'SUB', 'RED'])

for folder in os.listdir(BASE_DIR):
    if folder.startswith('ihu'):
        EXCLUDE_FOLDERS.add(folder)

COMMENTS_FILE = '/nfs/hatops/ar0/hatpi-website/comments.json'
SAVE_PATH = '/nfs/hatops/ar0/hatpi-website/markup_images'

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
    return render_template('folder.html', images=images, html_files=html_files, movies=movies, folder_name=folder_name)

@app.route('/api/folder/<path:folder_name>')
def api_folder(folder_name):
    folder_path = os.path.join(BASE_DIR, folder_name)
    images, html_files, movies = get_cached_files(folder_path)
    return jsonify({'images': images, 'html_files': html_files, 'movies': movies})

def is_date_based_folder(folder_name):
    return re.match(r'\d{4}-\d{2}-\d{2}', folder_name) is not None

def extract_ihu_number(filename):
    match = re.search(r'ihu-(\d+)', filename)
    if match:
        return int(match.group(1))
    return float('inf')


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

def get_cached_files(folder_path):
    start_time = time.time()
    cached_result = cache.get(folder_path)
    if cached_result:
        logging.info("get_cached_files - Cached result time: %s seconds" % (time.time() - start_time))
        return cached_result

    try:
        files = os.listdir(folder_path)
        logging.debug("Files in %s: %s" % (folder_path, files))
    except Exception as e:
        logging.error("Error reading directory %s: %s" % (folder_path, e))
        return [], [], []
    
    # Sort raw filenames alphabetically first
    files.sort()

    # Create lists of (filename, creation_date_string)
    images = [(file, get_creation_date(os.path.join(folder_path, file))) for file in files if file.endswith('.jpg')]
    html_files = [(file, get_creation_date(os.path.join(folder_path, file))) for file in files if file.endswith('.html')]
    movies = [(file, get_creation_date(os.path.join(folder_path, file))) for file in files if file.endswith('.mp4')]
    
    # -----------------------------------------------------------
    #   If path looks like "/nfs/hatops/ar0/hatpi-website/ihu-XX"
    #   => Sort by embedded filename date for ALL file types
    # -----------------------------------------------------------
    if "/nfs/hatops/ar0/hatpi-website/ihu-" in folder_path:
        images.sort(
            key=lambda x: (parse_file_date(x[0]) or datetime.datetime.min),
            reverse=True
        )
        html_files.sort(
            key=lambda x: (
                0 if 'telescope_status' in x[0] else 1,
                parse_file_date(x[0]) or datetime.datetime.min
            ),
            reverse=True
        )
        movies.sort(
            key=lambda x: (parse_file_date(x[0]) or datetime.datetime.min),
            reverse=True
        )

    # -----------------------------------------------------------
    #   If it's a "Dates" folder (e.g. "/nfs/hatops/ar0/hatpi-website/1-20250105")
    #   => Use original logic
    # -----------------------------------------------------------
    elif folder_path.startswith('/nfs/hatops/ar0/hatpi-website/1-'):
        images.sort(key=lambda x: extract_ihu_number(x[0]))
        html_files.sort(key=lambda x: (
            0 if 'telescope_status' in x[0] else 1,
            extract_ihu_number(x[0])
        ))
        movies.sort(key=lambda x: extract_ihu_number(x[0]))

    # -----------------------------------------------------------
    #   Otherwise, fallback to creation-date sorting
    #   => (original else block)
    # -----------------------------------------------------------
    else:
        images.sort(key=lambda x: datetime.datetime.strptime(x[1], '%Y-%m-%d %H:%M:%S'), reverse=True)
        html_files.sort(key=lambda x: datetime.datetime.strptime(x[1], '%Y-%m-%d %H:%M:%S'), reverse=True)
        movies.sort(key=lambda x: datetime.datetime.strptime(x[1], '%Y-%m-%d %H:%M:%S'), reverse=True)

    # Cache the result
    cache.put(folder_path, (images, html_files, movies))
    logging.info("get_cached_files - Directory reading and caching time: %s seconds" % (time.time() - start_time))
    return images, html_files, movies

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
    folder_name = 'ihu-%s' % cell_number
    folder_path = os.path.join(BASE_DIR, folder_name)
    images, html_files, movies = get_cached_files(folder_path)
    return render_template('folder.html', folder_name=folder_name, images=images, html_files=html_files, movies=movies)

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

if __name__ == '__main__':
    polling_thread = threading.Thread(target=poll_directory)
    polling_thread.daemon = True
    polling_thread.start()
    
    app.run(debug=True, port=8080)