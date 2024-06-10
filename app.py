from flask import Flask, render_template, send_from_directory, send_file, request, jsonify
import os
import datetime
import json
import logging
import time
import re
import threading
from collections import OrderedDict

app = Flask(__name__, static_folder='static', template_folder='templates')
BASE_DIR = '/nfs/hatops/ar0/hatpi-website'
EXCLUDE_FOLDERS = set(['static', 'templates', 'images', '.git', '__pycache__', 'scripts', 'movies'])

# Dynamically add all 'ihu' folders to the EXCLUDE_FOLDERS set
for folder in os.listdir(BASE_DIR):
    if folder.startswith('ihu'):
        EXCLUDE_FOLDERS.add(folder)

COMMENTS_FILE = '/nfs/hatops/ar0/hatpi-website/comments.json'

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
        elif 'flat' in parts[0] and 'ss' in parts[-1]:
            type_part = 'flat ss'
        elif 'flat' in parts[0] and 'ls' in parts[-1]:
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
        else:
            type_part = 'unknown'

        ihu_match = re.search(r'_(\d+)_', value)
        ihu_part = ihu_match.group(1) if ihu_match else 'IHU-'

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

# Keep track of the previous state of the directory
previous_state = set()

def poll_directory():
    global previous_state
    while True:
        current_state = set()
        for folder in os.listdir(BASE_DIR):
            folder_path = os.path.join(BASE_DIR, folder)
            if os.path.isdir(folder_path) and folder not in EXCLUDE_FOLDERS:
                current_state.add(folder_path)

        # Check if there are any changes
        if current_state != previous_state:
            cache.clear()
            print("Cache cleared due to directory change")
            previous_state = current_state
        
        # Poll every 30 minutes
        time.sleep(1800)

@app.route('/')
def home():
    start_time = time.time()
    folders = get_cached_dir_list(BASE_DIR)
    comments = load_comments()
    if not comments:
        comments = {}
    logging.info("Rendering template with folders: %s and comments: %s" % (folders, comments))
    logging.info("Home route processing time: %s seconds" % (time.time() - start_time))
    return render_template('index.html', folders=folders, comments=comments)

@app.route('/<folder_name>/')
def folder(folder_name):
    folder_path = os.path.join(BASE_DIR, folder_name)
    images, html_files, movies = get_cached_files(folder_path)
    return render_template('folder.html', images=images, html_files=html_files, movies=movies, folder_name=folder_name)

@app.route('/api/folder/<folder_name>')
def api_folder(folder_name):
    folder_path = os.path.join(BASE_DIR, folder_name)
    images, html_files, movies = get_cached_files(folder_path)
    return jsonify({'images': images, 'html_files': html_files, 'movies': movies})

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

    files.sort()
    images = [(file, get_creation_date(os.path.join(folder_path, file))) for file in files if file.endswith('.jpg')]
    html_files = [(file, get_creation_date(os.path.join(folder_path, file))) for file in files if file.endswith('.html')]
    movies = [(file, get_creation_date(os.path.join(folder_path, file))) for file in files if file.endswith('.mp4')]

    # Sort images, html_files, and movies by creation date in reverse order
    images.sort(key=lambda x: datetime.datetime.strptime(x[1], '%Y-%m-%d %H:%M:%S'), reverse=True)
    html_files.sort(key=lambda x: datetime.datetime.strptime(x[1], '%Y-%m-%d %H:%M:%S'), reverse=True)
    movies.sort(key=lambda x: datetime.datetime.strptime(x[1], '%Y-%m-%d %H:%M:%S'), reverse=True)

    cache.put(folder_path, (images, html_files, movies))
    logging.info("get_cached_files - Directory reading and caching time: %s seconds" % (time.time() - start_time))
    return images, html_files, movies

@app.route('/<folder_name>/<filename>')
def file(folder_name, filename):
    folder_path = os.path.join(BASE_DIR, folder_name)
    file_path = os.path.join(folder_path, filename)

    app.logger.info("Requested file: %s" % file_path)

    # Resolve symlink if it exists
    if os.path.islink(file_path):
        real_path = os.path.realpath(file_path)
        app.logger.info("Resolved symlink %s to %s" % (file_path, real_path))
        return send_file(real_path)

    return send_from_directory(folder_path, filename)

@app.route('/ihu/ihu-<cell_number>')
def ihu_cell(cell_number):
    folder_name = 'ihu-%s' % cell_number
    folder_path = os.path.join(BASE_DIR, folder_name)  # Ensure this path is correct
    images, html_files, movies = get_cached_files(folder_path)
    return render_template('folder.html', folder_name=folder_name, images=images, html_files=html_files, movies=movies)

@app.route('/submit_comment', methods=['POST'])
def submit_comment():
    data = request.json
    file_name = data.get('fileName')
    file_path = data.get('filePath')
    comment = data.get('comment')
    if file_name and comment:
        comments = load_comments()
        unique_key = '%s_%s' % (file_name, datetime.datetime.now().strftime('%Y%m%d%H%M%S%f'))
        comments[unique_key] = {
            'file_path': file_path,
            'comment': comment,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        save_comments(comments)
        return jsonify({'success': True})
    return jsonify({'success': False})

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
    # Start the polling thread
    polling_thread = threading.Thread(target=poll_directory)
    polling_thread.daemon = True
    polling_thread.start()
    
    # Start the Flask application
    app.run(debug=True, port=8080)
