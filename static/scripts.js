// Utility function to apply alternating colors
function applyAlternatingColors(containerSelector) {
    const items = document.querySelectorAll(`${containerSelector} .file-item`);
    let visibleItems = Array.from(items).filter(item => item.style.display !== 'none');
    
    visibleItems.forEach((item, index) => {
        // Remove existing odd/even classes
        item.classList.remove('odd', 'even');
        
        // Apply odd/even classes based on the current index
        if (index % 2 === 0) {
            item.classList.add('even');
        } else {
            item.classList.add('odd');
        }
    });
}

function loadFolder(folderName) {
    // Fetch the contents of the specified folder from the server
    fetch(`/api/folder/${folderName}`)
        .then(response => {
            // Check if the response is successful
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json(); // Convert response to JSON
        })
        .then(data => {
            const images = data.images;
            const htmlFiles = data.html_files;
            const movies = data.movies;
            // Display the contents of the folder
            displayFolderContents(images, htmlFiles, movies, folderName);
            // Set "All" filter as active by default
            filterImages('all');
            filterHtmlFiles('all');
            filterMovies('all');
        })
        .catch(error => console.error('Error loading folder:', error)); // Log any errors that occur during the fetch process
}

function displayFolderContents(images, htmlFiles, movies, folderName) {
    const imagesContainer = document.querySelector('.images');
    const htmlFilesContainer = document.querySelector('.plot-list'); 
    const moviesContainer = document.querySelector('.movies');

    imagesContainer.innerHTML = '';
    htmlFilesContainer.innerHTML = '';
    moviesContainer.innerHTML = '';

    images.sort((a, b) => new Date(b[1]) - new Date(a[1]));
    htmlFiles.sort((a, b) => new Date(b[1]) - new Date(a[1]));
    movies.sort((a, b) => new Date(b[1]) - new Date(a[1]));

    images.forEach(image => {
        const div = document.createElement('div');
        div.className = 'file-item';
        div.setAttribute('data-filename', image[0]);
        div.innerHTML = `
            <div class="file-name">
                <a href="#" onclick="openGallery('/hatpi/${folderName}/${image[0]}'); return false;">${image[0]}</a>
            </div>
            <div class="file-date">${image[1]}</div>
        `;
        imagesContainer.appendChild(div);
    });

    htmlFiles.forEach(htmlFile => {
        const div = document.createElement('div');
        div.className = 'file-item';
        div.setAttribute('data-filename', htmlFile[0]);
        div.innerHTML = `
            <div class="file-name">
                <a href="#" onclick="loadPlot('/hatpi/${folderName}/${htmlFile[0]}'); return false;">${htmlFile[0]}</a>
            </div>
            <div class="file-date">${htmlFile[1]}</div>
        `;
        htmlFilesContainer.appendChild(div);
    });

    movies.forEach(movie => {
        const div = document.createElement('div');
        div.className = 'file-item';
        div.setAttribute('data-filename', movie[0]);
        div.innerHTML = `
            <div class="file-name">
                <a href="#" onclick="openGallery('/hatpi/${folderName}/${movie[0]}'); return false;">${movie[0]}</a>
            </div>
            <div class="file-date">${movie[1]}</div>
        `;
        moviesContainer.appendChild(div);
    });

    applyAlternatingColors('.images');
    applyAlternatingColors('.plot-list');
    applyAlternatingColors('.movies');
}


function showTab(tabId, event) {
    // Get all tab contents and deactivate them
    var tabContents = document.getElementsByClassName('tab-content');
    for (var i = 0; i < tabContents.length; i++) {
        tabContents[i].classList.remove('active');
    }

    // Get all pill buttons and deactivate them
    var pillButtons = document.getElementsByClassName('pill-button-unique');
    for (var i = 0; i < pillButtons.length; i++) {
        pillButtons[i].classList.remove('active');
    }

    // Activate the selected tab and its corresponding button
    document.getElementById(tabId).classList.add('active');
    event.target.classList.add('active');

    // Show or hide filter buttons based on the selected tab
    if (tabId === 'images') {
        document.getElementById('image-filters').classList.remove('hidden');
        document.getElementById('html-filters').classList.add('hidden');
        document.getElementById('movie-filters').classList.add('hidden');
    } else if (tabId === 'html-files') {
        document.getElementById('html-filters').classList.remove('hidden');
        document.getElementById('image-filters').classList.add('hidden');
        document.getElementById('movie-filters').classList.add('hidden');
    } else if (tabId === 'movies') {
        document.getElementById('movie-filters').classList.remove('hidden');
        document.getElementById('image-filters').classList.add('hidden');
        document.getElementById('html-filters').classList.add('hidden');
    } else {
        document.getElementById('image-filters').classList.add('hidden');
        document.getElementById('html-filters').classList.add('hidden');
        document.getElementById('movie-filters').classList.add('hidden');
    }
}

// Global variable to track the current gallery state
let currentGalleryIndex = -1;
let currentGalleryFiles = [];
let galleryOverlay = null;

// Function to navigate the gallery
function navigateGallery(direction) {
    currentGalleryIndex = (currentGalleryIndex + direction + currentGalleryFiles.length) % currentGalleryFiles.length;
    let nextFile = null;

    // Determine the next file to display based on the onclick attribute
    const onclickString = currentGalleryFiles[currentGalleryIndex].getAttribute('onclick');
    const openGalleryMatch = onclickString.match(/openGallery\('([^']+)'\)/);
    const loadPlotMatch = onclickString.match(/loadPlot\('([^']+)'\)/);

    if (openGalleryMatch) {
        nextFile = openGalleryMatch[1];
    } else if (loadPlotMatch) {
        nextFile = loadPlotMatch[1];
    }

    if (nextFile) {
        openGallery(nextFile);
    } else {
        console.error('No matching file path found in onclick attribute:', onclickString);
    }
}

// Event listener for keyboard navigation
const handleKeyDown = (event) => {
    if (currentGalleryIndex === -1 || !currentGalleryFiles.length) return;

    if (event.key === 'ArrowLeft') {
        navigateGallery(-1);
    } else if (event.key === 'ArrowRight') {
        navigateGallery(1);
    }
};

// Attach the event listener to the document once
document.addEventListener('keydown', handleKeyDown);

function openGallery(filePath) {
    if (!galleryOverlay) {
        // Create the overlay element if it doesn't exist
        galleryOverlay = document.createElement('div');
        galleryOverlay.id = 'galleryOverlay';
        galleryOverlay.className = 'gallery-overlay';
        document.body.appendChild(galleryOverlay);
    } else {
        // Clear existing content in the overlay
        galleryOverlay.innerHTML = '';
    }

    // Extract the file name from the file path and create a title element
    const fileName = filePath.split('/').pop();
    const title = document.createElement('div');
    title.innerText = fileName;
    title.className = 'gallery-title';

    // Determine the file type and find the current file index in the list
    const fileType = filePath.split('.').pop();
    currentGalleryFiles = document.querySelectorAll(fileType === 'html' ? '.plot-list .file-item' : (fileType === 'mp4' ? '.movies .file-item' : '.images .file-item'));
    currentGalleryFiles = Array.from(currentGalleryFiles).filter(item => item.style.display !== 'none').map(item => item.querySelector('a'));
    currentGalleryIndex = currentGalleryFiles.findIndex(file => file.getAttribute('onclick').includes(filePath));

    if (currentGalleryIndex === -1) {
        console.error('File not found in list:', filePath);
        return;
    }

    // Create the appropriate content element based on the file type
    let content;
    if (fileType === 'html') {
        content = document.createElement('iframe');
        content.src = filePath;
        content.className = 'overlay-iframe';
    } else if (fileType === 'mp4') {
        content = document.createElement('video');
        content.src = filePath;
        content.className = 'gallery-content';
        content.controls = true;
    } else {
        content = document.createElement('img');
        content.src = filePath;
        content.className = 'gallery-content';
    }
    content.onerror = () => {
        console.error('Error loading file:', filePath);
        content.alt = 'Failed to load';
        content.src = 'path_to_placeholder_image.jpg'; // Use a placeholder image for failed loads
    };

    // Create navigation arrows
    const createArrow = (direction) => {
        const arrow = document.createElement('a');
        arrow.innerText = direction === -1 ? '❮' : '❯';
        arrow.className = `arrow ${direction === -1 ? 'left-arrow' : 'right-arrow'}`;
        arrow.onclick = () => navigateGallery(direction);
        return arrow;
    };

    const leftArrow = createArrow(-1);
    const rightArrow = createArrow(1);

    // Create a close button to remove the overlay
    const closeButton = document.createElement('button');
    closeButton.innerText = 'X';
    closeButton.className = "closeButton";
    closeButton.onclick = () => {
        document.body.removeChild(galleryOverlay);
        galleryOverlay = null; // Reset the overlay
        currentGalleryIndex = -1; // Reset the gallery state
        currentGalleryFiles = []; // Clear the files list
    };

    // Create the comment container and its elements
    const commentContainer = document.createElement('div');
    commentContainer.className = 'comment-container';

    const commentBox = document.createElement('textarea');
    commentBox.className = "commentBox";
    commentBox.placeholder = 'Add a comment...';

    const submitButton = document.createElement('button');
    submitButton.innerText = 'Submit';
    submitButton.className = 'submit-button';
    submitButton.onclick = () => submitComment(filePath, commentBox.value);

    commentContainer.appendChild(commentBox);
    commentContainer.appendChild(submitButton);

    // Create the container structure
    const topRow = document.createElement('div');
    topRow.className = 'top-row';
    const bottomRow = document.createElement('div');
    bottomRow.className = 'bottom-row';

    const leftEmpty = document.createElement('div');
    leftEmpty.className = 'left-empty';
    const middleCenter = document.createElement('div');
    middleCenter.className = 'middle-center';
    const rightClose = document.createElement('div');
    rightClose.className = 'right-close';

    const leftContent = document.createElement('div');
    leftContent.className = 'left-content';
    const rightComments = document.createElement('div');
    rightComments.className = 'right-comments';

    // Append elements to the structure
    middleCenter.appendChild(leftArrow);
    middleCenter.appendChild(title);
    middleCenter.appendChild(rightArrow);
    rightClose.appendChild(closeButton);

    leftContent.appendChild(content);
    rightComments.appendChild(commentContainer);

    topRow.appendChild(leftEmpty);
    topRow.appendChild(middleCenter);
    topRow.appendChild(rightClose);

    bottomRow.appendChild(leftContent);
    bottomRow.appendChild(rightComments);

    galleryOverlay.appendChild(topRow);
    galleryOverlay.appendChild(bottomRow);
}

function loadPlot(filePath) {
    // Load the Bokeh library and then open the gallery with the specified file
    const script = document.createElement('script');
    script.src = "https://cdn.bokeh.org/bokeh/release/bokeh-3.1.0.min.js";
    script.onload = () => {
        Bokeh.set_log_level("warning");
        openGallery(filePath);
    };
    document.head.appendChild(script);
}

function submitComment(filePath, comment) {
    // Submit the comment to the server
    fetch('/hatpi/submit_comment', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ fileName: filePath.split('/').pop(), filePath, comment }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Comment submitted successfully!');
            loadComments();
        } else {
            alert('Failed to submit comment.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error submitting comment.');
    });
}

function loadComments() {
    // Load comments from the server and display them
    fetch('/path/to/comments.json')
        .then(response => response.json())
        .then(data => {
            const commentsContainer = document.querySelector('.comments-container');
            commentsContainer.innerHTML = ''; // Clear existing comments

            // Convert comments object to array and sort by timestamp
            const commentsArray = Object.entries(data).map(([key, comment]) => ({
                ...comment,
                uniqueKey: key
            }));
            commentsArray.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

            // Create and append comment elements to the comments container
            for (const comment of commentsArray) {
                const filename = comment.file_path.split('/').pop();
                const commentItem = document.createElement('div');
                commentItem.className = 'comment-item';
                commentItem.innerHTML = `
                    <div class="comment-header">
                        <span class="comment-filename">
                            <a href="${comment.file_path}" target="_blank">
                                ${filename}
                            </a>
                        </span>
                        <span class="comment-timestamp">${comment.timestamp}</span>
                    </div>
                    <div class="comment-body">
                        <p>${comment.comment}</p>
                    </div>
                `;
                commentsContainer.appendChild(commentItem);
            }
        })
        .catch(error => console.error('Error loading comments:', error)); // Log any errors that occur during the fetch process
}

// Load comments when the document is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    loadComments();
});

function filterImages(filter) {
    const filterButtons = document.querySelectorAll('#image-filters .filter-button');
    filterButtons.forEach(button => {
        button.classList.remove('active');
    });

    const activeButton = Array.from(filterButtons).find(button => {
        const buttonText = button.textContent.trim().toLowerCase().replace(' ', '-');
        return buttonText === filter;
    });
    if (activeButton) {
        activeButton.classList.add('active');
    }

    const imageItems = document.querySelectorAll('.images .file-item');
    const filteredItems = Array.from(imageItems).filter(item => {
        const filename = item.getAttribute('data-filename').toLowerCase();
        return filter === 'all' || filename.includes(filter);
    });

    filteredItems.sort((a, b) => {
        const dateA = new Date(a.querySelector('.file-date').textContent);
        const dateB = new Date(b.querySelector('.file-date').textContent);
        return dateB - dateA;
    });

    imageItems.forEach(item => item.style.display = 'none');
    filteredItems.forEach(item => item.style.display = 'flex');

    // Apply alternating colors
    applyAlternatingColors('.images');
}

function filterHtmlFiles(filter) {
    const filterButtons = document.querySelectorAll('#html-filters .filter-button');
    filterButtons.forEach(button => {
        button.classList.remove('active');
    });

    const activeButton = Array.from(filterButtons).find(button => {
        const buttonText = button.textContent.trim().toLowerCase().replace(' ', '_');
        return buttonText === filter;
    });
    if (activeButton) {
        activeButton.classList.add('active');
    }

    const htmlFileItems = document.querySelectorAll('.plot-list .file-item');
    const filteredItems = Array.from(htmlFileItems).filter(item => {
        const filename = item.getAttribute('data-filename').toLowerCase();
        return filter === 'all' || filename.includes(filter);
    });

    filteredItems.sort((a, b) => {
        const dateA = new Date(a.querySelector('.file-date').textContent);
        const dateB = new Date(b.querySelector('.file-date').textContent);
        return dateB - dateA;
    });

    htmlFileItems.forEach(item => item.style.display = 'none');
    filteredItems.forEach(item => item.style.display = 'flex');

    // Apply alternating colors
    applyAlternatingColors('.plot-list');
}

function filterMovies(filter) {
    const filterButtons = document.querySelectorAll('#movie-filters .filter-button');
    filterButtons.forEach(button => {
        button.classList.remove('active');
    });

    const activeButton = Array.from(filterButtons).find(button => {
        const buttonText = button.textContent.trim().toLowerCase().replace(' ', '-');
        return buttonText === filter;
    });
    if (activeButton) {
        activeButton.classList.add('active');
    }

    const movieItems = document.querySelectorAll('.movies .file-item');
    const filteredItems = Array.from(movieItems).filter(item => {
        const filename = item.getAttribute('data-filename').toLowerCase();

        if (filter === 'all') {
            return true;
        } else if (filter === 'subframe') {
            return filename.includes('subframe') && !filename.includes('subframe_stamps');
        } else if (filter === 'subframe-stamps') {
            return filename.includes('subframe_stamps');
        } else if (filter === 'calframe') {
            return filename.includes('calframe') && !filename.includes('calframe_stamps');
        } else if (filter === 'calframe-stamps') {
            return filename.includes('calframe_stamps');
        }
        return false;
    });

    filteredItems.sort((a, b) => {
        const dateA = new Date(a.querySelector('.file-date').textContent);
        const dateB = new Date(b.querySelector('.file-date').textContent);
        return dateB - dateA;
    });

    movieItems.forEach(item => item.style.display = 'none');
    filteredItems.forEach(item => item.style.display = 'flex');

    // Apply alternating colors
    applyAlternatingColors('.movies');
}


// Ensure the gallery overlay content scales properly
function adjustGalleryContent() {
    const galleryContent = document.querySelector('.gallery-content');
    const overlayIframe = document.querySelector('.overlay-iframe');

    if (galleryContent) {
        galleryContent.style.maxWidth = '100%';
        galleryContent.style.maxHeight = '100%';
        galleryContent.style.objectFit = 'contain';
    }

    if (overlayIframe) {
        overlayIframe.style.width = '100%';
        overlayIframe.style.height = '100%';
    }
}

// Attach the adjustGalleryContent function to the window resize event
window.addEventListener('resize', adjustGalleryContent);

// Call adjustGalleryContent once when the script is loaded to ensure initial sizing
adjustGalleryContent();
