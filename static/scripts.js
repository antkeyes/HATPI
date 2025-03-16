/***************************************
 * scripts.js
 ***************************************/

/**
 * 1) Apply alternating odd/even row colors for file-items
 */
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

// Store your original calibration filter buttons in a constant.
// This will be re-injected when returning to "Calibration" mode.
const CALIBRATION_BUTTONS_HTML = `
    <button class="filter-button active" onclick="filterImages('all')">All</button>
    <button class="filter-button" onclick="filterImages('bias')">Bias</button>
    <button class="filter-button" onclick="filterImages('dark')">Dark</button>
    <button class="filter-button" onclick="filterImages('flat-ss')">Flat</button>
    <!-- <button class="filter-button" onclick="filterImages('flat-ls')">Flat ls</button> -->
    <button class="filter-button" onclick="filterImages('globflat-ss')">Globflat ss</button>
    <button class="filter-button" onclick="filterImages('globflat-ls')">Globflat ls</button>
`;

/**
 * Load the default calibration data for the current folder.
 */
function loadFolder(folderName) {
    fetch(`/hatpi/api/folder/${folderName}`)
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

/**
 * Switch between "Calibration" mode and "RED/SUB" mode
 */
function switchDataMode(mode) {
    const calibrationBtn = document.getElementById('calibrationModeButton');
    const redSubBtn = document.getElementById('redSubModeButton');
    const imageFiltersContainer = document.getElementById('image-filters');
    const gridContainer = document.getElementById('grid-container-redsub');
    const imagesContainer = document.querySelector('.images-list .images');
    const folderName = document.querySelector('.page-title').getAttribute('data-folder');
    const isIHU = folderName.toLocaleLowerCase().startsWith('ihu-');

    if (mode === 'calibration') {
        calibrationBtn.classList.add('active');
        redSubBtn.classList.remove('active');

        // Return calibration filter buttons
        imageFiltersContainer.innerHTML = CALIBRATION_BUTTONS_HTML;
        gridContainer.style.display = 'none';

        // Clear out whatever is in the .images container
        imagesContainer.innerHTML = '';

        // Force the "Images" tab to be selected, so it doesn't remain on "Plots" or "Movies"
        document.getElementById('images').classList.add('active');
        document.getElementById('html-files').classList.remove('active');
        document.getElementById('movies').classList.remove('active');

        // Show the correct filter buttons
        document.getElementById('image-filters').classList.remove('hidden');
        document.getElementById('html-filters').classList.add('hidden');
        document.getElementById('movie-filters').classList.add('hidden');

        // Reload calibration folder images
        fetch(`/hatpi/api/folder/${folderName}`)
            .then(r => r.json())
            .then(data => {
                const images = data.images;
                const htmlFiles = data.html_files;
                const movies = data.movies;
                displayFolderContents(images, htmlFiles, movies, folderName);
                filterImages('all');
            })
            .catch(err => console.error('Error reloading calibration folder:', err));

    } else if (mode === 'redsub') {
        // RED / SUB logic
        calibrationBtn.classList.remove('active');
        redSubBtn.classList.add('active');

        imageFiltersContainer.innerHTML = `
            <button class="filter-button active" onclick="switchRedSubFilter('reduction')">Reduction</button>
            <button class="filter-button" onclick="switchRedSubFilter('subtraction')">Subtraction</button>
        `;

        imagesContainer.innerHTML = '';

        if (isIHU) {
            gridContainer.style.display = 'none';
            window.selectedCamera = folderName.replace("ihu-", "ihu");
            listRedSubDatesForIhu('RED');
        } else {
            gridContainer.style.display = 'block';
            createRedSubIHUGrid();
        }
    }
}

// Helper: Convert "1-YYYYMMDD" to "YYYY-MM-DD"
function formatDateFolderName(folderName) {
    // Check if the folder name starts with "1-" and has a total length of 10 characters
    if (folderName.startsWith("1-") && folderName.length === 10) {
        let digits = folderName.substring(2); // Get the "YYYYMMDD" part
        return digits.slice(0, 4) + '-' + digits.slice(4, 6) + '-' + digits.slice(6);
    }
    return folderName; // Fallback if the format is unexpected
}



function listRedSubDatesForIhu(redOrSub) {
    const imagesContainer = document.querySelector('.images-list .images');
    imagesContainer.innerHTML = '';
    removeBackButton(); // Remove any existing “⟵ Back” link

    // Fetch subfolders from the top-level RED or SUB directory
    const subfoldersApi = `/hatpi/api/subfolders/${redOrSub}`;
    fetch(subfoldersApi)
        .then(r => r.json())
        .then(data => {
            const subfolders = (data.subfolders || []).reverse();
            if (!subfolders.length) {
                imagesContainer.innerHTML = `<p>No date subfolders found for ${redOrSub}</p>`;
                return;
            }
            // For each date (e.g. "1-20250203"), create a link
            subfolders.forEach(dateName => {
                const div = document.createElement('div');
                div.className = 'file-item';
                div.innerHTML = `
                    <div class="file-name">
                        <a href="#" onclick="listRedSubFilesForIhu('${redOrSub}','${dateName}'); return false;">
                            ${formatDateFolderName(dateName)}
                        </a>
                    </div>
                    <div class="file-date"></div>
                `;
                imagesContainer.appendChild(div);
            });
            applyAlternatingColors('.images');
        })
        .catch(e => console.error("Error listing subfolders:", e));
}

function listRedSubFilesForIhu(redOrSub, dateName) {
    const imagesContainer = document.querySelector('.images-list .images');
    imagesContainer.innerHTML = '';
    createBackButton(() => listRedSubDatesForIhu(redOrSub));

    // Use the globally stored camera folder (e.g. "ihu48")
    const cameraFolder = window.selectedCamera;
    const apiPath = `${redOrSub}/${dateName}/${cameraFolder}`;

    fetch(`/hatpi/api/folder/${apiPath}`)
        .then(r => r.json())
        .then(data => {
            const images = data.images || [];
            if (!images.length) {
                imagesContainer.innerHTML = `<p>No .jpg files found in ${dateName}</p>`;
                return;
            }
            // Sort images by frame number in ascending order.
            images.sort((a, b) => {
                // a[0] and b[0] are the filenames.
                const matchA = a[0].match(/1-(\d+)_/);
                const matchB = b[0].match(/1-(\d+)_/);
                const frameA = matchA ? parseInt(matchA[1], 10) : Infinity;
                const frameB = matchB ? parseInt(matchB[1], 10) : Infinity;
                return frameA - frameB;
            });

            images.forEach(img => {
                const fileName = img[0];
                const fileDate = img[1];
                const fullPath = `/${redOrSub}/${dateName}/${cameraFolder}/${fileName}`;
                const prettyName = buildRedSubLinkText(dateName, redOrSub, cameraFolder, fileName);

                const div = document.createElement('div');
                div.className = 'file-item';
                div.setAttribute('data-filename', fileName);
                div.innerHTML = `
                    <div class="file-name">
                        <a href="#" onclick="openGallery('/hatpi${fullPath}'); return false;">
                            ${prettyName}
                        </a>
                    </div>
                    <div class="file-date">${fileDate}</div>
                `;
                imagesContainer.appendChild(div);
            });
            applyAlternatingColors('.images');
        })
        .catch(e => {
            console.error('Error listing files:', e);
            imagesContainer.innerHTML = `<p>Failed to list files for ${apiPath}</p>`;
        });
}


/**
 * Switch between "Reduction" and "Subtraction" within RED/SUB mode
 */
function switchRedSubFilter(selectedType) {
    // Mark the clicked button as active
    const buttons = document.querySelectorAll('#image-filters .filter-button');
    buttons.forEach(b => b.classList.remove('active'));

    const clickedButton = Array.from(buttons).find(b => b.textContent.toLowerCase() === selectedType);
    if (clickedButton) {
        clickedButton.classList.add('active');
    }

    const folderName = document.querySelector('.page-title').getAttribute('data-folder');
    const isIHU = folderName.toLowerCase().startsWith('ihu-');
    const redOrSub = (selectedType === 'reduction') ? 'RED' : 'SUB';
    const imagesContainer = document.querySelector('.images-list .images');
    imagesContainer.innerHTML = '';

    if (isIHU) {
        // In IHU mode, use our new functions
        window.selectedCamera = folderName.replace("ihu-", "ihu");
        listRedSubDatesForIhu(redOrSub);
    } else {
        // Otherwise, keep your existing flow (if any)
        // For example, you might call listRedSubDates(folderName, redOrSub)
    }
}


function listRedSubDates(folderName, redOrSub) {
    const imagesContainer = document.querySelector('.images-list .images');
    imagesContainer.innerHTML = '';
    removeBackButton(); // remove any existing "⟵ Back" link

    const isIHU = folderName.toLowerCase().startsWith('ihu-');

    // If user is on an IHU folder (e.g. "ihu-48"), we ignore it and do /RED or /SUB.
    // If user is on a date folder (e.g. "1-20250113"), we do "1-20250113/RED"
    let subfoldersApi;
    if (isIHU) {
        subfoldersApi = `/hatpi/api/subfolders/${redOrSub}`;
    } else {
        subfoldersApi = `/hatpi/api/subfolders/${folderName}/${redOrSub}`;
    }

    fetch(subfoldersApi)
        .then(r => r.json())
        .then(data => {
            const subfolders = data.subfolders || [];
            if (!subfolders.length) {
                imagesContainer.innerHTML = `<p>No date subfolders found for ${redOrSub}</p>`;
                return;
            }

            // For each date subfolder (like "1-20250113"),
            // we link to listRedSubFiles(...)
            subfolders.forEach(dateName => {
                const div = document.createElement('div');
                div.className = 'file-item';
                div.innerHTML = `
                    <div class="file-name">
                        <a href="#" onclick="listRedSubFiles('${folderName}','${redOrSub}','${dateName}'); return false;">
                            ${dateName}
                        </a>
                    </div>
                    <div class="file-date"></div>
                `;
                imagesContainer.appendChild(div);
            });

            applyAlternatingColors('.images');
        })
        .catch(e => console.error("Error listing subfolders:", e));
}


function listRedSubFiles(folderName, redOrSub, dateName) {
    const imagesContainer = document.querySelector('.images-list .images');
    imagesContainer.innerHTML = '';
    createBackButton(() => listRedSubDates(folderName, redOrSub));

    const isIHU = folderName.toLowerCase().startsWith('ihu-');

    // Build the API path
    let apiPath;
    if (isIHU) {
        const bareIhu = folderName.replace("ihu-", "ihu");
        apiPath = `${redOrSub}/${dateName}/${bareIhu}`;
    } else {
        apiPath = `${folderName}/${redOrSub}/${dateName}`;
    }

    console.log(`[listRedSubFiles] API path is: /hatpi/api/folder/${apiPath}`);

    fetch(`/hatpi/api/folder/${apiPath}`)
        .then(r => r.json())
        .then(data => {
            let images = data.images || [];

            if (!images.length) {
                imagesContainer.innerHTML = `<p>No .jpg files found in ${dateName}</p>`;
                return;
            }

            // *** Sort the images array by frame number (ascending) ***
            images.sort((a, b) => {
                // a[0] and b[0] are filenames.
                let matchA = a[0].match(/1-(\d+)_/);
                let matchB = b[0].match(/1-(\d+)_/);

                // If the first regex fails, try a fallback that simply grabs digits before an underscore.
                if (!matchA) {
                    matchA = a[0].match(/(\d+)_/);
                }
                if (!matchB) {
                    matchB = b[0].match(/(\d+)_/);
                }

                // If still no matches, let's log them so we see what's going on.
                if (!matchA && a[0]) {
                    console.warn(`[listRedSubFiles] Could not find frame for: ${a[0]}`);
                }
                if (!matchB && b[0]) {
                    console.warn(`[listRedSubFiles] Could not find frame for: ${b[0]}`);
                }

                const frameA = matchA ? parseInt(matchA[1], 10) : Infinity;
                const frameB = matchB ? parseInt(matchB[1], 10) : Infinity;

                // For debugging, print out the parse results
                console.log(`Comparing frames: A:${frameA}  B:${frameB}  filenames: "${a[0]}" "${b[0]}"`);
                return frameA - frameB;
            });

            // Now build the display.
            images.forEach(img => {
                const fileName = img[0];
                const fileDate = img[1];

                // Build final path
                let fullPath;
                if (isIHU) {
                    const bareIhu = folderName.replace("ihu-", "ihu");
                    fullPath = `/${redOrSub}/${dateName}/${bareIhu}/${fileName}`;
                } else {
                    fullPath = `/${folderName}/${redOrSub}/${dateName}/${fileName}`;
                }

                // Use your specialized formatting function.
                const prettyName = buildRedSubLinkText(
                    dateName,
                    redOrSub,
                    isIHU ? folderName.replace("ihu-", "ihu") : folderName,
                    fileName
                );

                const div = document.createElement('div');
                div.className = 'file-item';
                div.setAttribute('data-filename', fileName);
                div.innerHTML = `
            <div class="file-name">
                <a href="#" onclick="openGallery('/hatpi${fullPath}'); return false;">
                    ${prettyName}
                </a>
            </div>
            <div class="file-date">${fileDate}</div>
          `;
                imagesContainer.appendChild(div);
            });

            applyAlternatingColors('.images');
        })
        .catch(e => {
            console.error('Error listing files:', e);
            imagesContainer.innerHTML = `<p>Failed to list files for ${apiPath}</p>`;
        });
}






function createBackButton(onClickFn) {
    const imagesContainer = document.querySelector('.images-list .images');
    const backDiv = document.createElement('div');
    backDiv.className = 'file-item back-button';  // so it matches your styling
    backDiv.style.cursor = 'pointer';
    backDiv.innerHTML = `
        <div class="file-name">
          <p>⬅️ Back to Dates</p>
        </div>
        <div class="file-date"></div>
    `;
    backDiv.addEventListener('click', onClickFn);

    imagesContainer.appendChild(backDiv);
}

function removeBackButton() {
    const imagesContainer = document.querySelector('.images-list .images');
    // remove any "⟵ Back" item if present
    const backItems = imagesContainer.querySelectorAll('.file-item');
    backItems.forEach(item => {
        const fileNameDiv = item.querySelector('.file-name');
        if (fileNameDiv && fileNameDiv.innerText.includes('Back')) {
            imagesContainer.removeChild(item);
        }
    });
}


function toggleIHUView(view) {
    // Get all the buttons inside #index-ihu-buttons
    var buttons = document.querySelectorAll('#index-ihu-buttons .pill-button-unique');

    // Remove active class from all
    buttons.forEach(button => button.classList.remove('active'));

    // Depending on the view, toggle the grid display
    if (view === 'sequential') {
        document.getElementById('grid-container-ihu-sequential').style.display = 'grid';
        document.getElementById('grid-container-ihu-actual').style.display = 'none';
        // Add active class to the sequential button
        document.querySelector('#index-ihu-buttons .pill-button-unique[onclick="toggleIHUView(\'sequential\')"]').classList.add('active');
    } else if (view === 'actual') {
        document.getElementById('grid-container-ihu-sequential').style.display = 'none';
        document.getElementById('grid-container-ihu-actual').style.display = 'grid';
        // Add active class to the actual button
        document.querySelector('#index-ihu-buttons .pill-button-unique[onclick="toggleIHUView(\'actual\')"]').classList.add('active');
    }
}


/**
 * Creates the "Sequential" IHU grid layout inside #grid-container-redsub,
 * hooking each button to loadRedSubFolder() with "reduction" or "subtraction."
 */
function createRedSubIHUGrid() {
    const sequentialGridContainer = document.getElementById('grid-container-redsub');
    sequentialGridContainer.innerHTML = ''; // Clear any previous content
    sequentialGridContainer.style.display = 'grid';

    const sequentialRowColors = [
        "#D5A6BE", // row 1
        "#B4A7D6", // row 2
        "#CEE1F3", // row 3
        "#6FA7DC", // row 4
        "#77A5AF", // row 5
        "#93C47D", // row 6
        "#F9E499", // row 7
        "#F5B26B", // row 8
        "#E06566", // row 9
        "#CC4125"  // row 10
    ];
    const sequentialRowColumns = [3, 7, 8, 9, 9, 9, 8, 6, 4, 1];

    let textIndex = 64;
    for (let i = 0; i < sequentialRowColumns.length; i++) {
        const row = document.createElement('div');
        row.className = 'grid-row-ihu';
        row.style.display = 'grid';
        row.style.gridTemplateColumns = `repeat(${sequentialRowColumns[i]}, 45px)`;
        row.style.justifyContent = 'center';
        row.style.gap = '3px';
        row.style.marginBottom = '3px';

        const cells = [];
        for (let j = 0; j < sequentialRowColumns[i]; j++) {
            const cell = document.createElement('div');
            cell.className = 'grid-item-ihu';
            cell.style.backgroundColor = sequentialRowColors[i];

            const button = document.createElement('button');
            button.textContent = textIndex;
            button.style.width = '100%';
            button.style.height = '100%';
            button.style.border = 'none';
            button.style.cursor = 'pointer';

            (function (indexValue) {
                button.addEventListener('click', function () {
                    const cellNumber = indexValue.toString().padStart(2, '0');
                    const dateFolder = document.querySelector('.page-title').getAttribute('data-folder');
                    const activeFilterBtn = document.querySelector('#image-filters .filter-button.active');
                    const type = activeFilterBtn ? activeFilterBtn.textContent.toLowerCase() : 'reduction';

                    // Because physically the folder is named "ihu48" (no dash),
                    // we do 'ihu' + cellNumber => e.g. 'ihu48'
                    const cameraFolder = 'ihu' + cellNumber;

                    loadRedSubFolder(dateFolder, cameraFolder, type);
                });
            })(textIndex);

            cell.appendChild(button);
            textIndex--;
            cells.unshift(cell);
        }
        cells.forEach(cell => row.appendChild(cell));
        sequentialGridContainer.appendChild(row);
    }
}


/**
 * Load images for dateFolder, cameraFolder, and type (reduction/subtraction)
 * Then display them in .images-list .images
 */
function loadRedSubFolder(dateFolder, cameraFolder, type) {
    const folderPath = `${type === 'reduction' ? 'RED' : 'SUB'}/${dateFolder}/${cameraFolder}`;
    fetch(`/hatpi/api/folder/${folderPath}`)
        .then(response => {
            if (!response.ok) throw new Error('Network error');
            return response.json();
        })
        .then(data => {
            displayRedSubImages(data.images, dateFolder, type, cameraFolder);
            // After updating the images list, scroll down 100px.
            const container = document.querySelector('.images-list-container');
            if (container) {
                setTimeout(() => {
                    container.scrollTo({ top: 200, behavior: 'smooth' });
                }, 50);
            }
        })
        .catch(error => console.error('Error loading RED/SUB folder:', error));
}


/**
 * Display loaded RED/SUB images, each with link text like:
 *  "YYYY-MM-DD | reduction | IHU-01 | frame: 485376"
 */
function displayRedSubImages(images, dateFolder, type, cameraFolder) {
    images.sort((a, b) => {
        const matchA = a[0].match(/1-(\d+)_/);
        const matchB = b[0].match(/1-(\d+)_/);
        const frameA = matchA ? parseInt(matchA[1], 10) : Infinity;
        const frameB = matchB ? parseInt(matchB[1], 10) : Infinity;
        return frameA - frameB;
    });

    const imagesContainer = document.querySelector('.images-list .images');
    imagesContainer.innerHTML = '';

    images.forEach(image => {
        const fileName = image[0];
        const fileDate = image[1];
        const linkText = buildRedSubLinkText(dateFolder, type, cameraFolder, fileName);
        const fullPath = `/${type === 'reduction' ? 'RED' : 'SUB'}/${dateFolder}/${cameraFolder}/${fileName}`;

        const div = document.createElement('div');
        div.className = 'file-item';
        div.setAttribute('data-filename', fileName);
        div.innerHTML = `
            <div class="file-name">
                <a href="#" onclick="openGallery('/hatpi${fullPath}'); return false;">
                    ${linkText}
                </a>
            </div>
            <div class="file-date">${fileDate}</div>
        `;
        imagesContainer.appendChild(div);
    });

    applyAlternatingColors('.images');
}

/**
 * Build link text for RED/SUB images:
 *  "YYYY-MM-DD | reduction | IHU-01 | frame: ####"
 */
function buildRedSubLinkText(dateFolder, type, cameraFolder, fileName) {
    let match = fileName.match(/1-(\d+)_/);
    const frameText = match ? `frame: ${match[1]}` : fileName;

    // Convert "ihu01" => "IHU-01"
    let cameraDisplay = cameraFolder.toUpperCase();
    if (!cameraDisplay.includes('-')) {
        cameraDisplay = cameraDisplay.slice(0, 3) + '-' + cameraDisplay.slice(3);
    }

    // Convert "1-20250213" => "2025-02-13"
    let dateStr = dateFolder;
    if (dateFolder.indexOf('-') === 1 && dateFolder.length >= 10) {
        dateStr = dateFolder.substring(2, 6) + '-' +
            dateFolder.substring(6, 8) + '-' +
            dateFolder.substring(8, 10);
    }

    return `${dateStr} | ${type} | ${cameraDisplay} | ${frameText}`;
}

/**
 * Display calibration images, HTML files, movies (non-RED/SUB),
 * each name processed by formatTitle() to show the old formatting:
 *  "YYYY-MM-DD | dark | IHU-01"
 *  "YYYY-MM-DD | Aper Phot Quality | IHU-01"
 *  "YYYY-MM-DD | subframe | IHU-01"
 * etc.
 */
function displayFolderContents(images, htmlFiles, movies, folderName) {
    const imagesContainer = document.querySelector('.images');
    const htmlFilesContainer = document.querySelector('.plot-list');
    const moviesContainer = document.querySelector('.movies');

    imagesContainer.innerHTML = '';
    htmlFilesContainer.innerHTML = '';
    moviesContainer.innerHTML = '';

    // IMAGES
    images.forEach(image => {
        const fileName = image[0];
        const fileDate = image[1];
        const lines = formatTitle(fileName);  // Our custom formatting

        const listingLines = lines.filter(line =>
            !line.toLowerCase().startsWith('exposure time:') &&
            !line.toLowerCase().startsWith('ccd temp:')
        )

        const prettyName = listingLines.length ? listingLines.join(' | ') : fileName;

        const div = document.createElement('div');
        div.className = 'file-item';
        div.setAttribute('data-filename', fileName);
        div.innerHTML = `
            <div class="file-name">
                <a href="#" onclick="openGallery('/hatpi/${folderName}/${fileName}'); return false;">
                    ${prettyName}
                </a>
            </div>
            <div class="file-date">${fileDate}</div>
        `;
        imagesContainer.appendChild(div);
    });

    // HTML FILES (plots)
    htmlFiles.forEach(htmlFile => {
        const fileName = htmlFile[0];
        const fileDate = htmlFile[1];
        const lines = formatTitle(fileName);
        const prettyName = lines.length ? lines.join(' | ') : fileName;

        const div = document.createElement('div');
        div.className = 'file-item';
        div.setAttribute('data-filename', fileName);
        div.innerHTML = `
            <div class="file-name">
                <a href="#" onclick="loadPlot('/hatpi/${folderName}/${fileName}'); return false;">
                    ${prettyName}
                </a>
            </div>
            <div class="file-date">${fileDate}</div>
        `;
        htmlFilesContainer.appendChild(div);
    });

    // MOVIES
    movies.forEach(movie => {
        const fileName = movie[0];
        const fileDate = movie[1];
        const lines = formatTitle(fileName);
        const prettyName = lines.length ? lines.join(' | ') : fileName;

        const div = document.createElement('div');
        div.className = 'file-item';
        div.setAttribute('data-filename', fileName);
        div.innerHTML = `
            <div class="file-name">
                <a href="#" onclick="openGallery('/hatpi/${folderName}/${fileName}'); return false;">
                    ${prettyName}
                </a>
            </div>
            <div class="file-date">${fileDate}</div>
        `;
        moviesContainer.appendChild(div);
    });

    applyAlternatingColors('.images');
    applyAlternatingColors('.plot-list');
    applyAlternatingColors('.movies');
}

/** 
 * Tab switching for Images / Plots / Movies
 */
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

    // Only show the grid if we're in RED/SUB mode AND the Images tab is active.
    if (tabId === 'images' && document.getElementById('redSubModeButton').classList.contains('active')) {
        document.getElementById('grid-container-redsub').style.display = 'block';
    } else {
        document.getElementById('grid-container-redsub').style.display = 'none';
    }

    if (tabId === 'images') {
        document.getElementById('data-mode-buttons').style.display = 'block';
    } else {
        document.getElementById('data-mode-buttons').style.display = 'none';
    }


}

/**************************************************
 *  GALLERY / OVERLAY CODE
 **************************************************/
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

const KEY_TO_FLAG = {
    a: 'Airplane',
    b: "Beautiful",
    c: 'Clouds',
    f: 'Flash',
    g: 'Ghost',
    i: 'Ice',
    m: 'Meteor',
    r: 'Readout Issue',
    s: 'Shutter Failure',
    t: 'Trail',
    w: 'Weird',
    o: 'Other'
}

const handleKeyDown = (event) => {
    if (currentGalleryIndex === -1 || !currentGalleryFiles.length) return;

    // If user is typing in the comment box or any input/textarea, skip
    const activeEl = document.activeElement;
    const isTypingInInput =
        activeEl &&
        (activeEl.tagName.toLowerCase() === 'textarea' ||
         (activeEl.tagName.toLowerCase() === 'input' && activeEl.type !== 'checkbox'));

    if (isTypingInInput) {
        // If they’re typing in the comment box, do not toggle flags
        return;
    }


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
    } else if (KEY_TO_FLAG[event.key]) {
        toggleFlagCheckbox(KEY_TO_FLAG[event.key]);
        event.preventDefault(); //prevent default behavior (like scrolling for space bar press)
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
        if (!img) return;
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
            if (bgPosX + magnifierSize > imgRect.width * zoomLevel) {
                bgPosX = imgRect.width * zoomLevel - magnifierSize;
            }
            if (bgPosY + magnifierSize > imgRect.height * zoomLevel) {
                bgPosY = imgRect.height * zoomLevel - magnifierSize;
            }

            magnifier.style.backgroundImage = `url(${img.src})`;
            magnifier.style.backgroundSize = `${imgRect.width * zoomLevel}px ${imgRect.height * zoomLevel}px`;
            magnifier.style.backgroundPosition = `-${bgPosX}px -${bgPosY}px`;
        } else {
            magnifier.style.display = 'none';
        }
    }
}

document.addEventListener('mousemove', showMagnifier);

/** Copy link to clipboard utility (restored) */
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

/**
 * RESTORED openGallery function with copy link for .jpg, 
 * plus ccd temp & exposure time lines from formatTitle
 */
function openGallery(filePath) {
    if (!galleryOverlay) {
        galleryOverlay = document.createElement('div');
        galleryOverlay.id = 'galleryOverlay';
        galleryOverlay.className = 'gallery-overlay';
        document.body.appendChild(galleryOverlay);
    } else {
        galleryOverlay.innerHTML = '';
    }

    window.currentFilePath = filePath;

    const fileName = filePath.split('/').pop();
    let folderForTitle;
    if (filePath.includes('/RED/') || filePath.includes('/SUB/')) {
        let parts = filePath.split('/');
        folderForTitle = parts[3] || "";
    } else {
        folderForTitle = document.querySelector('.page-title').getAttribute('data-folder');
    }
    const formattedTitle = formatTitle(fileName, folderForTitle);

    // We'll create a container for the "title lines"
    const titleContainer = document.createElement('div');
    titleContainer.className = 'gallery-title-container';

    formattedTitle.forEach(line => {
        const lineElement = document.createElement('div');
        lineElement.className = 'gallery-title-line';
        lineElement.innerText = line;
        titleContainer.appendChild(lineElement);
    });

    // Extract the date (YYYYMMDD) from the lines for the copy-link logic
    // The user previously grabbed a date from something like "YYYY-MM-DD"
    // Then stripped out dashes => "YYYYMMDD"
    let date = '';
    const dateLine = formattedTitle.find(line => /\d{4}-\d{2}-\d{2}/.test(line));
    if (dateLine) {
        // e.g. "2025-02-14" => "20250214"
        date = dateLine.replace(/-/g, '');
    }

    // Only show the copy link for .jpg files
    if (fileName.endsWith('.jpg')) {
        const copyLink = document.createElement('a');
        copyLink.href = '#';
        copyLink.innerText = 'Copy Image Link';
        copyLink.className = 'copy-link';
        copyLink.addEventListener('click', function (event) {
            event.preventDefault();
            // The user’s old logic used "1-YYYYMMDD" in the link
            // const url = `https://hatops.astro.princeton.edu/hatpi/1-${date}/${fileName}`;
            const url = `https://hatops.astro.princeton.edu${filePath}`;
            copyToClipboard(url);
            copyLink.innerText = 'Copied ✅';
        });

        titleContainer.appendChild(copyLink);
    }

    let content;
    const fileType = filePath.split('.').pop();

    // Identify which set of .file-item links to get for left/right nav
    currentGalleryFiles = document.querySelectorAll(
        fileType === 'html'
            ? '.plot-list .file-item'
            : (fileType === 'mp4'
                ? '.movies .file-item'
                : '.images .file-item'
            )
    );
    // First get all .file-item elements:
    let allItems = document.querySelectorAll(
        fileType === 'html'
            ? '.plot-list .file-item'
            : fileType === 'mp4'
                ? '.movies .file-item'
                : '.images .file-item'
    );

    // Convert NodeList to an array:
    allItems = Array.from(allItems);

    // Filter out hidden .file-item parents:
    allItems = allItems.filter(item => {
        // Is the parent hidden?
        return window.getComputedStyle(item).display !== 'none';
    });

    // Then map to the anchor for the openGallery(...) path
    // currentGalleryFiles = allItems.map(item => item.querySelector('a'));
    currentGalleryFiles = allItems
        .map(item => item.querySelector('a'))
        .filter(a => a !== null);


    currentGalleryIndex = currentGalleryFiles.findIndex(file =>
        file.getAttribute('onclick') && file.getAttribute('onclick').includes(filePath)
    );

    if (currentGalleryIndex === -1) {
        console.error('File not found in list:', filePath);
        return;
    }

    // Build our overlay content
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

    // If there's an error loading the resource, fallback
    content.onerror = () => {
        console.error('Error loading file:', filePath);
        content.alt = 'Failed to load';
        content.src = '/hatpi/static/placeholder.jpg';
    };

    // Function to close gallery overlay
    function closeGalleryOverlay() {
        if (galleryOverlay) {
            document.body.removeChild(galleryOverlay);
            galleryOverlay = null;
            currentGalleryIndex = -1;
            currentGalleryFiles = [];
        }
    }

    // Create 'esc' button
    const closeButton = document.createElement('button');
    closeButton.innerText = 'esc';
    closeButton.className = "closeButton";
    closeButton.onclick = closeGalleryOverlay;

    // Keydown listener for Escape key
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeGalleryOverlay();
        }
    }, { once: true });

    // Comments + nav container
    const commentContainer = document.createElement('div');
    commentContainer.className = 'comment-container';

    const commentBox = document.createElement('textarea');
    commentBox.className = "commentBox";
    commentBox.placeholder = 'Add a comment...';

    // author dropdown
    const authorDropdown = document.createElement('select');
    authorDropdown.className = 'author-dropdown';

    // 'author' as default label
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Author';
    defaultOption.disabled = true;
    defaultOption.selected = true;
    authorDropdown.appendChild(defaultOption);

    // authors (example list, add any missing names)
    const authors = ['Adriana', 'Anthony', 'Antoine', 'Attila', 'Gaspar', 'Geert Jan', 'Joel', 'Zoli', 'Guest'];
    authors.forEach(author => {
        const option = document.createElement('option');
        option.value = author;
        option.textContent = author;
        authorDropdown.appendChild(option);
    });

    const submitButton = document.createElement('button');
    submitButton.innerText = 'Submit';
    submitButton.className = 'submit-button';
    submitButton.onclick = () => submitCommentOrMarkup(filePath, commentBox.value, authorDropdown.value);

    commentContainer.appendChild(commentBox);
    commentContainer.appendChild(authorDropdown);
    commentContainer.appendChild(submitButton);

    // Left/right nav arrows
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

    // Construct overall content container
    const contentContainer = document.createElement('div');
    contentContainer.className = 'content-container';

    const leftContent = document.createElement('div');
    leftContent.className = 'left-content';
    const rightComments = document.createElement('div');
    rightComments.className = 'right-comments';

    leftContent.appendChild(content);
    rightComments.appendChild(titleContainer);
    rightComments.appendChild(commentContainer);

    const flagsContainer = document.createElement('div');
    flagsContainer.id = 'flags-container';
    flagsContainer.className = 'flags-container';
    flagsContainer.innerHTML = `
        <h3>Flag Selections</h3>
        <div class="flags-grid">
            <label><input type="checkbox" value="Airplane"> Airplane (a)</label>
            <label><input type="checkbox" value="Beautiful"> Beautiful (b)</label>
            <label><input type="checkbox" value="Clouds"> Clouds (c)</label>
            <label><input type="checkbox" value="Flash"> Flash (f)</label>
            <label><input type="checkbox" value="Ghost"> Ghost (g)</label>
            <label><input type="checkbox" value="Ice"> Ice (i)</label>
            <label><input type="checkbox" value="Meteor"> Meteor (m)</label>
            <label><input type="checkbox" value="Readout Issue"> Readout Issue (r)</label>
            <label><input type="checkbox" value="Shutter Failure"> Shutter Failure (s)</label>
            <label><input type="checkbox" value="Trail"> Trail (t)</label>
            <label><input type="checkbox" value="Other"> Other (o) (unusual / unknown)</label>
            <label><input type="checkbox" value="Weird"> Weird (w)</label>
        </div>
        `;
    rightComments.appendChild(flagsContainer);

    rightComments.appendChild(navContainer);

    // Only add instructions if the file type is .jpg
    if (fileType === 'jpg') {
        const instructionsContainer = document.createElement('div');
        instructionsContainer.className = 'instructions-container';
        instructionsContainer.style.textAlign = 'left';
        instructionsContainer.innerHTML = `
            <p>Press and hold 'z' to zoom</p>
            <p>Press and hold 'd' to draw</p>
        `;
        rightComments.appendChild(instructionsContainer);
    }

    contentContainer.appendChild(leftContent);
    contentContainer.appendChild(rightComments);

    galleryOverlay.appendChild(contentContainer);
    galleryOverlay.appendChild(closeButton);

    adjustGalleryContent();

    // If it's a JPG, set up the drawing canvas
    if (fileType === 'jpg') {
        addCanvasOverlay(content);
    }

    const checkboxNodes = document.querySelectorAll('#flags-container .flags-grid input[type="checkbox"]');
    checkboxNodes.forEach(cb => {
        cb.addEventListener('change', () => {
            const label = cb.closest('label');
            if (!label) return;
            // toggle highlight class based on whether it's checked
            label.classList.toggle('flag-selected', cb.checked);
            pendingFlagChanges = true; // so we know to save
        });
    });

    precheckKeyboardFlags(filePath);
}

function precheckKeyboardFlags(filePath) {
    // Must remove "/hatpi" if that's what you do before saving:
    const pathKey = filePath.replace('/hatpi', '');

    fetch('/hatpi/keyboard_flags.json')
      .then(r => r.json())
      .then(data => {
          // Now lookup using pathKey instead of fileName
          if (data[pathKey] && data[pathKey].flags) {
              const savedFlags = data[pathKey].flags;
              // Then check your checkboxes accordingly
              const checkboxes = document.querySelectorAll('#flags-container .flags-grid input[type="checkbox"]');
              checkboxes.forEach(cb => {
                  if (savedFlags.includes(cb.value)) {
                      cb.checked = true;
                      cb.closest('label').classList.add('flag-selected');
                  } else {
                      cb.checked = false;
                      cb.closest('label').classList.remove('flag-selected');
                  }
              });
          } else {
              // If there's no entry for this path, uncheck everything
              const checkboxes = document.querySelectorAll('#flags-container .flags-grid input[type="checkbox"]');
              checkboxes.forEach(cb => {
                  cb.checked = false;
                  cb.closest('label').classList.remove('flag-selected');
              });
          }
      })
      .catch(err => console.error("Error loading keyboard flags:", err));
}


/**
 * Submit comment or markup to the server
 */
function submitCommentOrMarkup(filePath, comment, author) {
    if (!comment.trim()) {
        alert('Comment required to submit.');
        return;
    }
    if (!author) {
        alert('Please select an author.');
        return;
    }

    const flags = getSelectedFlags();

    const canvas = document.getElementById('drawingCanvas');
    const imageElement = document.querySelector('.gallery-content');

    if (drawingOccurred && canvas && imageElement) {
        // We have drawn on the canvas
        const offScreenCanvas = document.createElement('canvas');
        offScreenCanvas.width = imageElement.naturalWidth;
        offScreenCanvas.height = imageElement.naturalHeight;
        const offScreenCtx = offScreenCanvas.getContext('2d');

        offScreenCtx.drawImage(imageElement, 0, 0, offScreenCanvas.width, offScreenCanvas.height);
        offScreenCtx.drawImage(canvas, 0, 0, canvas.width, canvas.height,
            0, 0, offScreenCanvas.width, offScreenCanvas.height);

        const dataURL = offScreenCanvas.toDataURL('image/jpeg', 1.0);

        fetch('/hatpi/api/save_markups', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                fileName: filePath.split('/').pop(),
                imageData: dataURL,
                // Append flags using a unique delimiter (here "--FLAGS--")
                comment: comment,
                author: author,
                markup_true: '✏️',
                flags: flags
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
                    resetDrawingOccurred();
                } else {
                    alert('Failed to save markups and comment.');
                }
            })
            .catch(error => {
                console.error('Error saving markups:', error);
                alert('Error saving markups and comment.');
            });
    } else {
        // No drawing, just submit comment
        fetch('/hatpi/submit_comment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                fileName: filePath.split('/').pop(),
                filePath,
                comment,
                author,
                flags: flags
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
                    alert('Comment submitted successfully!');
                    loadComments();
                    resetDrawingOccurred();
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
    drawingOccurred = false;
}

/**
 * Add a canvas overlay for drawing if it's a JPG
 */
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
            drawingOccurred = true;
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

/**
 * Format filename to include ccd temp & exposure time lines (restored),
 * plus date, type, IHU, etc.
 */
function formatTitle(fileName, folderName) {
    let titleLines = [];
    let dateStr = '';
    let typeStr = '';
    let ihuStr = '';
  
    // Attempt to extract date from the file name first.
    let dateMatch = fileName.match(/(\d{4})(\d{2})(\d{2})/);
    if (dateMatch) {
        dateStr = `${dateMatch[1]}-${dateMatch[2]}-${dateMatch[3]}`;
    } else if (folderName && /^1-\d{8}$/.test(folderName)) {
        // If file name doesn’t have a date, extract it from folder name.
        // Folder name "1-20250310" becomes "2025-03-10".
        dateStr = folderName.substring(2,6) + '-' + folderName.substring(6,8) + '-' + folderName.substring(8,10);
    }
  
    // Extract IHU number from file name.
    let ihuMatch = fileName.match(/ihu-(\d+)/i);
    if (ihuMatch) {
        ihuStr = `IHU-${ihuMatch[1].padStart(2, '0')}`;
    } else {
        // Fallback: look for a number after an underscore.
        let underscoreMatch = fileName.match(/_(\d+)[-_]/);
        if (underscoreMatch) {
            ihuStr = `IHU-${underscoreMatch[1].padStart(2, '0')}`;
        }
    }
  
    // Determine file type.
    if (fileName.endsWith('.mp4')) {
        if (fileName.includes('subframe_stamps_movie')) {
            typeStr = 'Subframe Stamps';
        } else if (fileName.includes('subframe_movie')) {
            typeStr = 'Subframe';
        } else if (fileName.includes('calframe_stamps_movie')) {
            typeStr = 'Calframe Stamps';
        } else if (fileName.includes('calframe_movie')) {
            typeStr = 'Calframe';
        } else {
            typeStr = 'Movie';
        }
    } else if (fileName.endsWith('.html')) {
        if (fileName.includes('aper_phot_quality')) {
            typeStr = 'Aper Phot Quality';
        } else if (fileName.includes('astrometry_sip_quality')) {
            typeStr = 'Astrometry SIP Quality';
        } else if (fileName.includes('astrometry_wcs_quality')) {
            typeStr = 'Astrometry WCS Quality';
        } else if (fileName.includes('calframe_quality')) {
            typeStr = 'Calframe Quality';
        } else if (fileName.includes('ihu_status')) {
            typeStr = 'IHU Status';
        } else if (fileName.includes('psf_sources_model')) {
            typeStr = 'PSF Sources Model';
        } else if (fileName.includes('subframe_quality')) {
            typeStr = 'Subframe Quality';
        } else {
            typeStr = 'Station Status';
        }
    } else {
        // For .jpg files (calibration or red/subtraction)
        if (fileName.toLowerCase().includes('-red-')) {
            typeStr = 'Reduction';
        } else if (fileName.toLowerCase().includes('-sub-')) {
            typeStr = 'Subtraction';
        } else if (fileName.includes('masterdark')) {
            typeStr = 'Dark';
        } else if (fileName.includes('masterbias')) {
            typeStr = 'Bias';
        } else if (fileName.includes('masterflat') && fileName.includes('-ss')) {
            typeStr = 'Flat-ss';
        } else if (fileName.includes('masterflat') && fileName.includes('-ls')) {
            typeStr = 'Flat-ls';
        } else if (fileName.includes('masterglobflat') && fileName.includes('-ss')) {
            typeStr = 'Globflat-ss';
        } else if (fileName.includes('masterglobflat') && fileName.includes('-ls')) {
            typeStr = 'Globflat-ls';
        } else {
            typeStr = 'Image';
        }
    }
  
    // Extract frame number for JPEGs.
    let frameStr = '';
    if (!fileName.endsWith('.html') && !fileName.endsWith('.mp4')) {
        let frameMatch = fileName.match(/1-(\d+)_/);
        if (frameMatch) {
            frameStr = `frame: ${frameMatch[1]}`;
        }
    }
  
    if (dateStr) titleLines.push(dateStr);
    if (typeStr) titleLines.push(typeStr);
    if (ihuStr) titleLines.push(ihuStr);
    if (frameStr) titleLines.push(frameStr);
  
    // If no title lines were created, just return the raw file name.
    if (!titleLines.length) {
        return [fileName];
    }
    return titleLines;
}


function loadComments() {
    fetch('/hatpi/comments.json')
        .then(response => response.json())
        .then(data => {
            const commentsContainer = document.querySelector('.comments-container');
            if (!commentsContainer) return;
            commentsContainer.innerHTML = '';

            // Convert the object of comments into an array
            const commentsArray = Object.entries(data).map(([key, comment]) => ({
                ...comment,
                uniqueKey: key
            }));
            // Sort by newest first
            commentsArray.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

            for (const comment of commentsArray) {
                // 1) Get the filename from comment.file_path:
                const rawFilename = comment.file_path.split('/').pop();

                // 2) Check if path includes '/RED/' or '/SUB/'
                let prettyName;
                if (comment.file_path.includes('/RED/') || comment.file_path.includes('/SUB/')) {
                    // Just show the raw filename for RED/SUB:
                    prettyName = rawFilename;
                } else {
                    // For calibration files, keep using your existing formatTitle() logic:
                    const lines = formatTitle(rawFilename);
                    prettyName = lines.join(' | ');
                }

                // 3) Build the comment DOM:
                const iconDiv = document.createElement('div');
                iconDiv.className = 'markup-icon';
                iconDiv.innerText = comment.markup_true || '';

                const commentItem = document.createElement('div');
                commentItem.className = 'comment-item';
                commentItem.setAttribute('data-comment-id', comment.uniqueKey);
                commentItem.innerHTML = `
                    <div class="comment-header">
                        <span class="comment-filename">
                            <a href="${comment.file_path}" target="_blank">
                                ${prettyName}
                            </a>
                        </span>
                        <span class="comment-timestamp">${comment.timestamp}</span>
                    </div>
                    <div class="comment-body">
                        <p>${comment.comment}</p>
                        <button class="delete-comment-button" onclick="deleteComment('${comment.uniqueKey}')">
                            Delete
                        </button>
                    </div>
                `;

                // 4) Insert the "markup icon" if any:
                const filenameElement = commentItem.querySelector('.comment-filename');
                filenameElement.insertBefore(iconDiv, filenameElement.firstChild);

                // 5) If you also want to show flags, do something like:
                if (comment.flags && comment.flags.length) {
                    const flagsContainer = document.createElement('div');
                    flagsContainer.className = 'comment-flags';
                    comment.flags.forEach(flag => {
                        const flagSpan = document.createElement('span');
                        flagSpan.className = 'flag';
                        flagSpan.innerText = flag;
                        flagsContainer.appendChild(flagSpan);
                    });
                    commentItem.querySelector('.comment-body').appendChild(flagsContainer);
                }

                commentsContainer.appendChild(commentItem);
            }
        })
        .catch(error => console.error('Error loading comments:', error));
}



/**
 * Delete a comment (server call)
 */
function deleteComment(commentId) {
    const isConfirmed = confirm('Are you sure you want to delete this comment?');
    if (isConfirmed) {
        fetch('/hatpi/delete_comment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ commentId }),
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
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
}

/** Filter calibration images */
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

    imageItems.forEach(item => item.style.display = 'none');
    filteredItems.forEach(item => item.style.display = 'flex');

    applyAlternatingColors('.images');
}

/** Filter calibration HTML files */
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

    htmlFileItems.forEach(item => item.style.display = 'none');
    filteredItems.forEach(item => item.style.display = 'flex');

    applyAlternatingColors('.plot-list');
}

/** Filter calibration movies */
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
        if (filter === 'all') return true;
        if (filter === 'subframe') {
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

    movieItems.forEach(item => item.style.display = 'none');
    filteredItems.forEach(item => item.style.display = 'flex');

    applyAlternatingColors('.movies');
}

function getSelectedFlags() {
    const flags = [];
    const checkboxes = document.querySelectorAll('#flags-container .flags-grid input[type="checkbox"]');
    checkboxes.forEach(cb => {
        if (cb.checked) {
            flags.push(cb.value);
        }
    });
    return flags;
}

function submitComment() {
    const commentData = {
        // Collect other comment data...
        comment: document.getElementById('comment-input').value,
        author: document.getElementById('author-input').value,
        timestamp: new Date().toISOString().slice(0, 19).replace('T', ' '),
        // Get the flags selected:
        flags: getSelectedFlags()
    };

    // Now send commentData via AJAX/fetch or your preferred method to your server to update comments.json
    fetch('/path/to/api/submit-comment', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(commentData)
    })
        .then(response => response.json())
        .then(data => {
            // Handle the response
        })
        .catch(error => {
            console.error('Error submitting comment:', error);
        });
}

// check/uncheck the correct checkbox. add/remove the highlighted class on the label
function toggleFlagCheckbox(flagLabel) {
    const checkboxes = document.querySelectorAll('#flags-container .flags-grid input[type="checkbox"]');
    for (let cb of checkboxes) {
        if (cb.value === flagLabel) {
            cb.checked = !cb.checked; // Toggle checked status
            // Find the parent <label> and toggle the highlight
            const label = cb.closest('label');
            if (label) {
                label.classList.toggle('flag-selected', cb.checked);
            }
            break;
        }
    }
}

let pendingFlagChanges = false;
window.currentFilePath = null; // So we know which file is open

function toggleFlagCheckbox(flagLabel) {
    const checkboxes = document.querySelectorAll('#flags-container .flags-grid input[type="checkbox"]');
    for (let cb of checkboxes) {
        if (cb.value === flagLabel) {
            cb.checked = !cb.checked;
            const label = cb.closest('label');
            if (label) {
                label.classList.toggle('flag-selected', cb.checked);
            }
            pendingFlagChanges = true; // Mark unsaved
            break;
        }
    }
}

// Called by the arrow key nav:
function navigateGallery(direction) {
    if (pendingFlagChanges) {
        saveKeyboardFlagsForCurrentImage()
            .then(() => {
                pendingFlagChanges = false;
                goToNextOrPrev(direction);
            })
            .catch(err => {
                console.error("Error auto-saving flags:", err);
                // still navigate so user isn't stuck
                goToNextOrPrev(direction);
            });
    } else {
        goToNextOrPrev(direction);
    }
}

function goToNextOrPrev(direction) {
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
    }
}

function saveKeyboardFlagsForCurrentImage() {
    return new Promise((resolve, reject) => {
        // Gather currently checked flags
        const flags = [];
        const checkboxes = document.querySelectorAll('#flags-container .flags-grid input[type="checkbox"]');
        checkboxes.forEach(cb => {
            if (cb.checked) {
                flags.push(cb.value);
            }
        });

        let filePath = window.currentFilePath;
        if (!filePath) {
            return resolve();
        }

        filePath = filePath.replace('/hatpi', '');

        // Post to new /api/keyboard_flags route
        fetch('/hatpi/api/keyboard_flags', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                // fileName: fileName,
                filePath: filePath,
                flags: flags,
                author: '' // or "KeyboardUser"
            })
        })
        .then(r => r.json())
        .then(data => {
            if (!data.success) {
                console.warn("Keyboard flags not saved:", data.message);
            }
            resolve();
        })
        .catch(err => reject(err));
    });
}


/** Adjust overlay content on window resize */
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