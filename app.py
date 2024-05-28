from flask import Flask, render_template, send_from_directory, request, jsonify
import os
import datetime
import json
from collections import OrderedDict
import logging
import time

app = Flask(__name__, static_folder='static', template_folder='templates')
BASE_DIR = '/nfs/hatops/ar0/hatpi-website'  # Directory for data
EXCLUDE_FOLDERS = set(['static', 'templates', 'images', '.git', '__pycache__', 'scripts'])  # Folders to exclude
COMMENTS_FILE = '/nfs/hatops/ar0/hatpi-website/comments.json'  # Path to comments file

# setup basic logging
logging.basicConfig(level=logging.INFO)

class LRUCache:
    def __init__(self, capacity=128):
        self.cache = OrderedDict()  # Initialize an ordered dictionary to store cache
        self.capacity = capacity  # Set the capacity of the cache

    def get(self, key):
        if key not in self.cache:
            return None  # Return None if key is not in cache
        value = self.cache.pop(key)  # Remove the key and get its value
        self.cache[key] = value  # Reinsert the key to mark it as recently used
        return value

    def put(self, key, value):
        if key in self.cache:
            self.cache.pop(key)  # Remove the key if it already exists in cache
        elif len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)  # Remove the oldest item if cache is full
        self.cache[key] = value  # Insert the new key-value pair

cache = LRUCache()  # Create an instance of LRUCache

def get_cached_dir_list(base_dir):
    cached_result = cache.get(base_dir)
    if cached_result is not None:
        return cached_result  # Return cached result if it exists

    folders = []
    for folder in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder)
        if os.path.isdir(folder_path) and folder not in EXCLUDE_FOLDERS:
            creation_date = get_creation_date(folder_path)
            folders.append((folder, creation_date))  # Collect folders and their creation dates
    folders.sort(key=lambda x: x[0], reverse=True)  # Sort folders by name in reverse order
    cache.put(base_dir, folders)  # Cache the result
    return folders

def format_folder_name(value):
    """Custom filter to format folder name from '1-YYYYMMDD' to 'YYYY-MM-DD'"""
    parts = value.split('-')
    if len(parts) == 2 and len(parts[1]) == 8:
        return "{}-{}-{}".format(parts[1][:4], parts[1][4:6], parts[1][6:])
    return value

# Register the custom filter with Jinja2
app.jinja_env.filters['format_folder'] = format_folder_name

@app.route('/')
def home():
    start_time = time.time()  # Record start time
    folders = get_cached_dir_list(BASE_DIR)
    comments = load_comments()
    if comments is None:
        comments = {}
    logging.info("Rendering template with folders: {} and comments: {}".format(folders, comments))
    logging.info("Home route processing time: {} seconds".format(time.time() - start_time))  # Log processing time
    return render_template('index.html', folders=folders, comments=comments)

@app.route('/api/folder/<folder_name>')
def api_folder(folder_name):
    folder_path = os.path.join(BASE_DIR, folder_name)
    images, html_files = get_cached_files(folder_path)
    return jsonify({
        'images': images,
        'html_files': html_files
    })

def get_cached_files(folder_path):
    start_time = time.time()  # Record start time
    cached_result = cache.get(folder_path)
    if cached_result is not None:
        logging.info("get_cached_files - Cached result time: {} seconds".format(time.time() - start_time))  # Log cache hit time
        return cached_result

    files = os.listdir(folder_path)
    images = [(file, get_creation_date(os.path.join(folder_path, file))) for file in files if file.endswith('.jpg')]
    html_files = [(file, get_creation_date(os.path.join(folder_path, file))) for file in files if file.endswith('.html')]
    cache.put(folder_path, (images, html_files))  # Cache the result
    logging.info("get_cached_files - Directory reading and caching time: {} seconds".format(time.time() - start_time))  # Log processing time
    return images, html_files

@app.route('/<folder_name>/')
def folder(folder_name):
    folder_path = os.path.join(BASE_DIR, folder_name)
    images, html_files = get_cached_files(folder_path)
    return render_template('folder.html', images=images, html_files=html_files, folder_name=folder_name)

@app.route('/<folder_name>/<filename>')
def file(folder_name, filename):
    return send_from_directory(os.path.join(BASE_DIR, folder_name), filename)  # Serve file from directory

@app.route('/submit_comment', methods=['POST'])
def submit_comment():
    data = request.json
    file_name = data.get('fileName')
    file_path = data.get('filePath')
    comment = data.get('comment')
    if file_name and comment:
        comments = load_comments()
        unique_key = '{}_{}'.format(file_name, datetime.datetime.now().strftime('%Y%m%d%H%M%S%f'))
        comments[unique_key] = {
            'file_path': file_path,
            'comment': comment,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        save_comments(comments)  # Save updated comments
        return jsonify({'success': True})
    return jsonify({'success': False})

def get_creation_date(file_path):
    return datetime.datetime.fromtimestamp(os.path.getctime(file_path)).strftime('%Y-%m-%d %H:%M:%S')  # Get file creation date

def load_comments():
    if os.path.exists(COMMENTS_FILE):
        try:
            with open(COMMENTS_FILE, 'r') as file:
                comments = json.load(file)
            sorted_comments = OrderedDict(
                sorted(comments.items(), key=lambda item: datetime.datetime.strptime(item[1]['timestamp'], '%Y-%m-%d %H:%M:%S'), reverse=True)
            )
            logging.info("Comments loaded and sorted: {}".format(sorted_comments))  # Log loaded comments
            return sorted_comments
        except json.JSONDecodeError as e:
            logging.error("Error loading JSON: {}".format(e))  # Log JSON loading error
            return {}
    logging.info("No comments file found, returning empty dictionary")  # Log missing comments file
    return {}

def save_comments(comments):
    with open(COMMENTS_FILE, 'w') as file:
        json.dump(comments, file, indent=4)  # Save comments to file

if __name__ == '__main__':
    app.run(debug=True, port=8080)  # Run the Flask application
