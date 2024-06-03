from flask import Flask, render_template, send_from_directory, send_file, request, jsonify
import os
import datetime
import json
from collections import OrderedDict
import logging
import time
import re

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
    # Split the filename into parts
    parts = value.split('-')

    # Extract date part and reformat it
    date_part = parts[3][:4] + '-' + parts[3][4:6] + '-' + parts[3][6:8]

    # Extract type part (bias, dark, flat ss, flat ls)
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

    # Extract IHU part and number using regular expressions
    ihu_match = re.search(r'ihu-(\d+)', value)
    ihu_part = ihu_match.group(1) if ihu_match else 'IHU-'

    # Format the final string
    formatted_string = "{} | {} | IHU-{}".format(date_part, type_part, ihu_part)

    return formatted_string

app.jinja_env.filters['format_folder'] = format_folder_name
app.jinja_env.filters['format_filename'] = format_filename

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

@app.route('/api/folder/<folder_name>')
def api_folder(folder_name):
    folder_path = os.path.join(BASE_DIR, folder_name)
    images, html_files = get_cached_files(folder_path)
    return jsonify({'images': images, 'html_files': html_files})

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
        return [], []

    files.sort()
    images = [(file, get_creation_date(os.path.join(folder_path, file))) for file in files if file.endswith('.jpg')]
    html_files = [(file, get_creation_date(os.path.join(folder_path, file))) for file in files if file.endswith('.html')]
    cache.put(folder_path, (images, html_files))
    logging.info("get_cached_files - Directory reading and caching time: %s seconds" % (time.time() - start_time))
    return images, html_files

@app.route('/<folder_name>/')
def folder(folder_name):
    folder_path = os.path.join(BASE_DIR, folder_name)
    images, html_files = get_cached_files(folder_path)
    return render_template('folder.html', images=images, html_files=html_files, folder_name=folder_name)

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
    folder_path = os.path.join(BASE_DIR, 'ihu', folder_name)
    images, html_files = get_cached_files(folder_path)
    return render_template('folder.html', folder_name=folder_name, images=images, html_files=html_files)

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
    app.run(debug=True, port=8080)
