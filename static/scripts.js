// Utility function to apply alternating colors
function applyAlternatingColors(containerSelector) {
    const items = document.querySelectorAll(`${containerSelector} .file-item`);
    let visibleItems = Array.from(items).filter(item => item.style.display !== 'none');
    
    visibleItems.forEach((item, index) => {
        item.classList.remove('odd', 'even');
        if (index % 2 === 0) {
            item.classList.add('even');
        } else {
            item.classList.add('odd');
        }
    });
}

function loadFolder(folderName) {
    fetch(`/api/folder/${folderName}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            const images = data.images;
            const htmlFiles = data.html_files;
            const movies = data.movies;
            displayFolderContents(images, htmlFiles, movies, folderName);
            filterImages('all');
            filterHtmlFiles('all');
            filterMovies('all');
        })
        .catch(error => console.error('Error loading folder:', error));
}

function displayFolderContents(images, htmlFiles, movies, folderName) {
    const imagesContainer = document.querySelector('.images');
    const htmlFilesContainer = document.querySelector('.plot-list'); 
    const moviesContainer = document.querySelector('.movies');

    imagesContainer.innerHTML = '';
    htmlFilesContainer.innerHTML = '';
    moviesContainer.innerHTML = '';

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
    var tabContents = document.getElementsByClassName('tab-content');
    for (var i = 0; i < tabContents.length; i++) {
        tabContents[i].classList.remove('active');
    }

    var pillButtons = document.getElementsByClassName('pill-button-unique');
    for (var i = 0; i < pillButtons.length; i++) {
        pillButtons[i].classList.remove('active');
    }

    document.getElementById(tabId).classList.add('active');
    event.target.classList.add('active');

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

let currentGalleryIndex = -1;
let currentGalleryFiles = [];
let galleryOverlay = null;
let magnifierActive = false;
let drawingActive = false;
let drawingOccurred = false; // Flag to track drawing on the canvas

function navigateGallery(direction) {
    currentGalleryIndex = (currentGalleryIndex + direction + currentGalleryFiles.length) % currentGalleryFiles.length;
    let nextFile = null;

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

const handleKeyDown = (event) => {
    if (currentGalleryIndex === -1 || !currentGalleryFiles.length) return;

    if (event.key === 'ArrowLeft') {
        navigateGallery(-1);
    } else if (event.key === 'ArrowRight') {
        navigateGallery(1);
    } else if (event.key === 'z') {
        magnifierActive = true;
        document.body.classList.add('hide-cursor');
    } else if (event.key == 'd') {
        drawingActive = true;
        document.body.style.cursor = 'crosshair';
    }
};

const handleKeyUp = (event) => {
    if (event.key === 'z') {
        magnifierActive = false;
        document.body.classList.remove('hide-cursor');
        const magnifier = document.getElementById('magnifier');
        if (magnifier) {
            magnifier.style.display = 'none';
        }
    } else if (event.key == 'd') {
        drawingActive = false;
        document.body.style.cursor = 'default';
    }
};

document.addEventListener('keydown', handleKeyDown);
document.addEventListener('keyup', handleKeyUp);
document.addEventListener('mousemove', showMagnifier);

function createMagnifier() {
    const magnifier = document.createElement('div');
    magnifier.id = 'magnifier';
    magnifier.className = 'magnifier';
    document.body.appendChild(magnifier);
}

function showMagnifier(event) {
    const magnifier = document.getElementById('magnifier');
    if (magnifierActive && magnifier) {
        const img = document.querySelector('.gallery-content');
        const imgRect = img.getBoundingClientRect();
        const magnifierSize = 400;
        const zoomLevel = 2;

        let magnifierX = event.clientX - magnifierSize / 2;
        let magnifierY = event.clientY - magnifierSize / 2;

        if (magnifierX < imgRect.left) magnifierX = imgRect.left;
        if (magnifierY < imgRect.top) magnifierY = imgRect.top;
        if (magnifierX + magnifierSize > imgRect.right) magnifierX = imgRect.right - magnifierSize;
        if (magnifierY + magnifierSize > imgRect.bottom) magnifierY = imgRect.bottom - magnifierSize;

        if (event.clientX > imgRect.left && event.clientX < imgRect.right &&
            event.clientY > imgRect.top && event.clientY < imgRect.bottom) {
            magnifier.style.display = 'block';
            magnifier.style.left = `${magnifierX}px`;
            magnifier.style.top = `${magnifierY}px`;

            let bgPosX = (event.clientX - imgRect.left) * zoomLevel - magnifierSize / 2;
            let bgPosY = (event.clientY - imgRect.top) * zoomLevel - magnifierSize / 2;

            if (bgPosX < 0) bgPosX = 0;
            if (bgPosY < 0) bgPosY = 0;
            if (bgPosX + magnifierSize > imgRect.width * zoomLevel) bgPosX = imgRect.width * zoomLevel - magnifierSize;
            if (bgPosY + magnifierSize > imgRect.height * zoomLevel) bgPosY = imgRect.height * zoomLevel - magnifierSize;

            magnifier.style.backgroundImage = `url(${img.src})`;
            magnifier.style.backgroundSize = `${imgRect.width * zoomLevel}px ${imgRect.height * zoomLevel}px`;
            magnifier.style.backgroundPosition = `-${bgPosX}px -${bgPosY}px`;
        } else {
            magnifier.style.display = 'none';
        }
    }
}

document.addEventListener('mousemove', showMagnifier);

function openGallery(filePath) {
    if (!galleryOverlay) {
        galleryOverlay = document.createElement('div');
        galleryOverlay.id = 'galleryOverlay';
        galleryOverlay.className = 'gallery-overlay';
        document.body.appendChild(galleryOverlay);
    } else {
        galleryOverlay.innerHTML = '';
    }

    const fileName = filePath.split('/').pop();
    const formattedTitle = formatTitle(fileName);
    const titleContainer = document.createElement('div');
    titleContainer.className = 'gallery-title-container';

    const instructionsContainer = document.createElement('div');
    instructionsContainer.className = 'instructions-container';
    instructionsContainer.style.textAlign = 'left';
    instructionsContainer.innerHTML = `
        <p>Press and hold 'z' to zoom</p>
        <p>Press and hold 'd' to draw</p>
    `;

    formattedTitle.forEach(line => {
        const lineElement = document.createElement('div');
        lineElement.className = 'gallery-title-line';
        lineElement.innerText = line;
        titleContainer.appendChild(lineElement);
    });

    // Extract the date and other parts from the filename
    const dateLine = formattedTitle.find(line => /\d{4}-\d{2}-\d{2}/.test(line));
    const date = dateLine ? dateLine.match(/\d{4}-\d{2}-\d{2}/)[0].replace(/-/g, '') : '';

    // Only show the copy link for .jpg files
    if (fileName.endsWith('.jpg')) {
        const copyLink = document.createElement('a');
        copyLink.href = '#';
        copyLink.innerText = 'Copy Image Link';
        copyLink.className = 'copy-link';
        copyLink.addEventListener('click', function (event) {
            event.preventDefault();
            const imageName = fileName.split('.')[0];
            const url = `https://hatops.astro.princeton.edu/hatpi/1-${date}/${fileName}`;
            copyToClipboard(url);
            copyLink.innerText = 'Copied ✅';
        });

        titleContainer.appendChild(copyLink);
    }

    // Append title container to the gallery overlay
    const fileType = filePath.split('.').pop();
    currentGalleryFiles = document.querySelectorAll(fileType === 'html' ? '.plot-list .file-item' : (fileType === 'mp4' ? '.movies .file-item' : '.images .file-item'));
    currentGalleryFiles = Array.from(currentGalleryFiles).filter(item => item.style.display !== 'none').map(item => item.querySelector('a'));
    currentGalleryIndex = currentGalleryFiles.findIndex(file => file.getAttribute('onclick').includes(filePath));

    if (currentGalleryIndex === -1) {
        console.error('File not found in list:', filePath);
        return;
    }

    let content;
    if (fileType === 'html') {
        content = document.createElement('iframe');
        content.src = filePath;
        content.className = 'overlay-iframe gallery-content';
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
        content.src = 'path_to_placeholder_image.jpg'; 
    };

    const closeButton = document.createElement('button');
    closeButton.innerText = 'X';
    closeButton.className = "closeButton";
    closeButton.onclick = () => {
        document.body.removeChild(galleryOverlay);
        galleryOverlay = null;
        currentGalleryIndex = -1;
        currentGalleryFiles = [];
    };

    const commentContainer = document.createElement('div');
    commentContainer.className = 'comment-container';

    const commentBox = document.createElement('textarea');
    commentBox.className = "commentBox";
    commentBox.placeholder = 'Add a comment...';

    const submitButton = document.createElement('button');
    submitButton.innerText = 'Submit';
    submitButton.className = 'submit-button';
    submitButton.onclick = () => submitCommentOrMarkup(filePath, commentBox.value);

    commentContainer.appendChild(commentBox);
    commentContainer.appendChild(submitButton);

    const createArrow = (direction) => {
        const arrow = document.createElement('a');
        arrow.innerText = direction === -1 ? '❮' : '❯';
        arrow.className = `arrow ${direction === -1 ? 'left-arrow' : 'right-arrow'}`;
        arrow.onclick = () => navigateGallery(direction);
        return arrow;
    };

    const leftArrow = createArrow(-1);
    const rightArrow = createArrow(1);

    const navContainer = document.createElement('div');
    navContainer.className = 'nav-container';
    navContainer.appendChild(leftArrow);
    navContainer.appendChild(rightArrow);

    const contentContainer = document.createElement('div');
    contentContainer.className = 'content-container';

    const leftContent = document.createElement('div');
    leftContent.className = 'left-content';
    const rightComments = document.createElement('div');
    rightComments.className = 'right-comments';

    leftContent.appendChild(content);
    rightComments.appendChild(titleContainer);
    rightComments.appendChild(commentContainer);
    rightComments.appendChild(navContainer);
    rightComments.appendChild(instructionsContainer);

    contentContainer.appendChild(leftContent);
    contentContainer.appendChild(rightComments);

    galleryOverlay.appendChild(contentContainer);
    galleryOverlay.appendChild(closeButton);

    adjustGalleryContent();

    if (fileType === 'jpg') {
        addCanvasOverlay(content);
    }
}

function copyToClipboard(text) {
    const tempInput = document.createElement('input');
    tempInput.style.position = 'absolute';
    tempInput.style.left = '-9999px';
    tempInput.value = text;
    document.body.appendChild(tempInput);
    tempInput.select();
    document.execCommand('copy');
    document.body.removeChild(tempInput);
}





function submitCommentOrMarkup(filePath, comment) {
    if (!comment.trim()) {
        alert('Comment required to submit.');
        return;
    }

    const canvas = document.getElementById('drawingCanvas');
    const imageElement = document.querySelector('.gallery-content');

    if (drawingOccurred && canvas && imageElement) { // Check if drawing occurred
        const offScreenCanvas = document.createElement('canvas');
        offScreenCanvas.width = imageElement.naturalWidth;
        offScreenCanvas.height = imageElement.naturalHeight;
        const offScreenCtx = offScreenCanvas.getContext('2d');

        offScreenCtx.drawImage(imageElement, 0, 0, offScreenCanvas.width, offScreenCanvas.height);
        offScreenCtx.drawImage(canvas, 0, 0, canvas.width, canvas.height, 0, 0, offScreenCanvas.width, offScreenCanvas.height);

        const dataURL = offScreenCanvas.toDataURL('image/jpeg', 1.0);

        fetch('/hatpi/api/save_markups', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                fileName: filePath.split('/').pop(),
                imageData: dataURL,
                comment: comment,
                markup_true: '✏️'
            }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert('Markups and comment saved successfully!');
                loadComments();
                resetDrawingOccurred(); // Reset flag after successful submission
            } else {
                alert('Failed to save markups and comment.');
            }
        })
        .catch(error => {
            console.error('Error saving markups:', error);
            alert('Error saving markups and comment.');
        });
    } else {
        // Submit comment only
        fetch('/hatpi/submit_comment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ fileName: filePath.split('/').pop(), filePath, comment }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert('Comment submitted successfully!');
                loadComments();
                resetDrawingOccurred(); // Reset flag after successful submission
            } else {
                alert('Failed to submit comment.');
            }
        })
        .catch(error => {
            console.error('Error submitting comment:', error);
            alert('Error submitting comment.');
        });
    }
}

function resetDrawingOccurred() {
    drawingOccurred = false; // Reset the drawing flag
}

function addCanvasOverlay(imageElement) {
    if (imageElement.complete) {
        setupCanvas(imageElement);
    } else {
        imageElement.onload = () => {
            setupCanvas(imageElement);
        };
    }
}

function setupCanvas(imageElement) {
    const canvas = document.createElement('canvas');
    canvas.id = 'drawingCanvas';
    canvas.width = imageElement.clientWidth;
    canvas.height = imageElement.clientHeight;

    const rect = imageElement.getBoundingClientRect();
    const leftContentRect = imageElement.parentElement.getBoundingClientRect();

    canvas.style.position = 'absolute';
    canvas.style.top = (rect.top - leftContentRect.top) + 'px';
    canvas.style.left = (rect.left - leftContentRect.left) + 'px';
    canvas.style.width = imageElement.clientWidth + 'px';
    canvas.style.height = imageElement.clientHeight + 'px';
    canvas.style.pointerEvents = 'auto';

    imageElement.parentElement.style.position = 'relative';
    imageElement.parentElement.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    ctx.strokeStyle = 'red';
    ctx.lineWidth = 2;

    let drawing = false;

    const getCanvasCoordinates = (e) => {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        return {
            x: (e.clientX - rect.left) * scaleX,
            y: (e.clientY - rect.top) * scaleY
        };
    };

    canvas.addEventListener('mousedown', (e) => {
        if (drawingActive) {
            drawing = true;
            drawingOccurred = true; // Set the flag when drawing starts
            const { x, y } = getCanvasCoordinates(e);
            ctx.beginPath();
            ctx.moveTo(x, y);
        }
    });

    canvas.addEventListener('mousemove', (e) => {
        if (drawing && drawingActive) {
            const { x, y } = getCanvasCoordinates(e);
            ctx.lineTo(x, y);
            ctx.stroke();
        }
    });

    canvas.addEventListener('mouseup', () => {
        drawing = false;
    });

    canvas.addEventListener('mouseout', () => {
        drawing = false;
    });
}

document.addEventListener('keydown', handleKeyDown);
document.addEventListener('keyup', handleKeyUp);
document.addEventListener('mousemove', showMagnifier);

function formatTitle(fileName) {
    const parts = fileName.split('_');
    let titleLines = [];

    if (fileName.endsWith('.mp4')) {
        const dateMatch = fileName.match(/(\d{4})(\d{2})(\d{2})/);
        const ihuMatch = fileName.match(/_(\d+)_/); 
        let description = '';

        if (fileName.includes('subframe_stamps_movie')) {
            description = 'subframe stamps';
        } else if (fileName.includes('subframe_movie')) {
            description = 'subframe';
        } else if (fileName.includes('calframe_stamps_movie')) {
            description = 'calframe stamps';
        } else if (fileName.includes('calframe_movie')) {
            description = 'calframe';
        } else {
            description = 'unknown';
        }

        if (description) {
            titleLines.push(description);
        }

        if (ihuMatch) {
            titleLines.push(`ihu-${ihuMatch[1]}`);
        }

        if (dateMatch) {
            titleLines.push(`${dateMatch[1]}-${dateMatch[2]}-${dateMatch[3]}`);
        }
    } else {
        if (fileName.includes('masterdark')) {
            titleLines.push('dark');
        } else if (fileName.includes('masterbias')) {
            titleLines.push('bias');
        } else if (fileName.includes('masterflat') && fileName.includes('-ss')) {
            titleLines.push('flat-ss');
        } else if (fileName.includes('masterglobflat') && fileName.includes('-ls')) {
            titleLines.push('flat-ls');
        } else {
            titleLines.push(parts[0]);
        }

        const ihuMatch = fileName.match(/ihu-\d+/);
        if (ihuMatch) {
            titleLines.push(ihuMatch[0]);
        }

        const dateMatch = fileName.match(/\d{8}/);
        const dateNumberMatch = fileName.match(/(\d{8})-(\d+)/);
        if (dateMatch && dateNumberMatch) {
            const date = dateMatch[0];
            const number = dateNumberMatch[2];
            titleLines.push(`${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)} | ${number}`);
        }

        const exptimeMatch = fileName.match(/EXPTIME\d+\.\d+/);
        if (exptimeMatch) {
            titleLines.push(`exposure time: ${exptimeMatch[0].replace('EXPTIME', '')}`);
        }

        const tempMatch = fileName.match(/CCDTEMP-?\d+\.\d+/);
        if (tempMatch) {
            titleLines.push(`ccd temp: ${tempMatch[0].replace('CCDTEMP', '')}`);
        }
    }

    return titleLines;
}

function loadPlot(filePath) {
    const script = document.createElement('script');
    script.src = "https://cdn.bokeh.org/bokeh/release/bokeh-3.1.0.min.js";
    script.onload = () => {
        Bokeh.set_log_level("warning");
        openGallery(filePath);
    };
    document.head.appendChild(script);
}

function loadComments() {
    fetch('/hatpi/comments.json')
        .then(response => response.json())
        .then(data => {
            const commentsContainer = document.querySelector('.comments-container');
            commentsContainer.innerHTML = '';

            const commentsArray = Object.entries(data).map(([key, comment]) => ({
                ...comment,
                uniqueKey: key
            }));
            commentsArray.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

            for (const comment of commentsArray) {
                const filename = comment.file_path.split('/').pop();
                const iconDiv = document.createElement('div');
                iconDiv.className = 'markup-icon';
                iconDiv.innerText = comment.markup_true || '';

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

                const filenameElement = commentItem.querySelector('.comment-filename');
                filenameElement.insertBefore(iconDiv, filenameElement.firstChild);

                commentsContainer.appendChild(commentItem);
            }
        })
        .catch(error => console.error('Error loading comments:', error));
}

document.addEventListener('DOMContentLoaded', () => {
    loadComments();
});

function deleteComment(commentId) {
    fetch('/hatpi/delete_comment', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ commentId: commentId }),
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Remove the comment element from the DOM
            const commentElement = document.querySelector(`.comment-item[data-comment-id='${commentId}']`);
            if (commentElement) {
                commentElement.remove();
            }
        } else {
            alert('Failed to delete comment.');
        }
    })
    .catch(error => {
        console.error('Error deleting comment:', error);
        alert('Error deleting comment.');
    });
}

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
        if (filter === 'all') return true;
        if (filter === 'flat-ss') return filename.startsWith('masterflat') && filename.endsWith('ss.jpg');
        if (filter === 'flat-ls') return filename.startsWith('masterflat') && filename.endsWith('ls.jpg');
        if (filter === 'globflat-ss') return filename.startsWith('masterglobflat') && filename.endsWith('ss.jpg');
        if (filter === 'globflat-ls') return filename.startsWith('masterglobflat') && filename.endsWith('ls.jpg');
        return filename.includes(filter);
    });

    filteredItems.sort((a, b) => {
        const dateA = new Date(a.querySelector('.file-date').textContent);
        const dateB = new Date(b.querySelector('.file-date').textContent);
        return dateB - dateA;
    });

    imageItems.forEach(item => item.style.display = 'none');
    filteredItems.forEach(item => item.style.display = 'flex');

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

    applyAlternatingColors('.movies');
}

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

window.addEventListener('resize', adjustGalleryContent);
adjustGalleryContent();
createMagnifier();
