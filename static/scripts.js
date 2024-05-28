function loadFolder(folderName) {
    // Fetch the contents of the specified folder from the server
    fetch(`/api/folder/${folderName}`)
        .then(response => {
            // Check if the response is successful
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text(); // Convert response to text
        })
        .then(text => {
            try {
                // Parse the response text as JSON
                const data = JSON.parse(text);
                const images = data.images;
                const htmlFiles = data.html_files;
                // Display the contents of the folder
                displayFolderContents(images, htmlFiles, folderName);
            } catch (error) {
                // Log any errors that occur during JSON parsing
                console.error('Error parsing JSON:', error);
                console.error('Response text:', text);
            }
        })
        .catch(error => console.error('Error loading folder:', error)); // Log any errors that occur during the fetch process
}

function displayFolderContents(images, htmlFiles, folderName) {
    const imagesContainer = document.getElementById('images');
    const htmlFilesContainer = document.getElementById('html-files');

    // Clear existing content in the containers
    imagesContainer.innerHTML = '';
    htmlFilesContainer.innerHTML = '';

    // Create and append image elements to the images container
    images.forEach(image => {
        const div = document.createElement('div');
        div.className = 'file-item';
        div.innerHTML = `
            <div class="file-name">
                <a href="#" onclick="openGallery('/hatpi/${folderName}/${image[0]}'); return false;">${image[0]}</a>
            </div>
            <div class="file-date">${image[1]}</div>
        `;
        imagesContainer.appendChild(div);
    });

    // Create and append HTML file elements to the HTML files container
    htmlFiles.forEach(htmlFile => {
        const div = document.createElement('div');
        div.className = 'file-item';
        div.innerHTML = `
            <div class="file-name">
                <a href="#" onclick="loadPlot('/hatpi/${folderName}/${htmlFile[0]}'); return false;">${htmlFile[0]}</a>
            </div>
            <div class="file-date">${htmlFile[1]}</div>
        `;
        htmlFilesContainer.appendChild(div);
    });
}

function showTab(tabId) {
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
}

function openGallery(filePath) {
    // Get the overlay element or create a new one if it doesn't exist
    let overlay = document.getElementById('galleryOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'galleryOverlay';
        overlay.className = 'gallery-overlay';
        document.body.appendChild(overlay);
    } else {
        overlay.innerHTML = '';
    }

    // Extract the file name from the file path and create a title element
    const fileName = filePath.split('/').pop();
    const title = document.createElement('div');
    title.innerText = fileName;
    title.className = 'gallery-title';

    // Determine the file type and find the current file index in the list
    const fileType = filePath.split('.').pop();
    const files = document.querySelectorAll(fileType === 'html' ? '.html-files a' : '.images a');
    let currentIndex = Array.from(files).findIndex(file => file.onclick.toString().includes(filePath));

    if (currentIndex === -1) {
        console.error('File not found in list:', filePath);
        return;
    }

    // Create the appropriate content element based on the file type
    const content = document.createElement(fileType === 'html' ? 'iframe' : 'img');
    content.src = filePath;
    content.className = 'gallery-content';
    if (fileType === 'html') {
        content.classList.add('overlay-iframe');
    }

    // Function to create navigation arrows for the gallery
    const createArrow = (direction) => {
        const arrow = document.createElement('a');
        arrow.innerText = direction === -1 ? '❮' : '❯';
        arrow.className = `arrow ${direction === -1 ? 'left-arrow' : 'right-arrow'}`;
        arrow.onclick = () => {
            currentIndex = (currentIndex + direction + files.length) % files.length;
            let nextFile = null;

            // Determine the next file to display based on the onclick attribute
            const onclickString = files[currentIndex].getAttribute('onclick');
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
        };
        return arrow;
    };

    const leftArrow = createArrow(-1); // Create left arrow
    const rightArrow = createArrow(1); // Create right arrow

    // Create a close button to remove the overlay
    const closeButton = document.createElement('button');
    closeButton.innerText = 'X';
    closeButton.className = "closeButton";
    closeButton.onclick = () => document.body.removeChild(overlay);

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

    // Copy existing comments from the home comments container if it exists
    const homeCommentsContainer = document.querySelector('.comments-container');
    if (homeCommentsContainer) {
        commentContainer.innerHTML = homeCommentsContainer.innerHTML;
    }

    commentContainer.appendChild(commentBox);
    commentContainer.appendChild(submitButton);

    // Append elements to the overlay
    overlay.appendChild(title);
    overlay.appendChild(leftArrow);
    overlay.appendChild(content);
    overlay.appendChild(commentContainer);
    overlay.appendChild(rightArrow);
    overlay.appendChild(closeButton);
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
