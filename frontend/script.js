const API_ENDPOINT = 'https://uuh0u6vum4.execute-api.us-east-1.amazonaws.com/prod';
const API_KEY = 'GqljqurJQQm30OmqxckZ4vOfyThQEBg4U0kl7cD9';
const BUCKET_NAME = 'photo-storage-ml';

// ============================================
// Search Functionality
// ============================================
async function searchPhotos() {
    const queryInput = document.getElementById('searchQuery');
    if (!queryInput) {
        alert('Search input not found');
        return;
    }
    
    const query = queryInput.value.trim();
    
    if (!query) {
        showMessage('searchMessage', 'Please enter a search query', 'error');
        return;
    }
    
    // Show loading state
    const resultsSection = document.getElementById('resultsSection');
    const resultsDiv = document.getElementById('results');
    
    if (resultsSection) resultsSection.style.display = 'block';
    if (resultsDiv) resultsDiv.innerHTML = '<div class="loading"><div class="spinner"></div>Searching...</div>';
    
    try {
        console.log('Searching for:', query);
        
        const response = await fetch(
            `${API_ENDPOINT}/search?q=${encodeURIComponent(query)}`,
            {
                method: 'GET',
                headers: {
                    'x-api-key': API_KEY,
                    'Content-Type': 'application/json'
                }
            }
        );
        
        console.log('Search response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Search results:', data);
        
        displayResults(data.results || []);
        
    } catch (error) {
        console.error('Search error:', error);
        if (resultsDiv) {
            resultsDiv.innerHTML = `
                <div class="error-message">
                    Search failed: ${error.message}
                    <br><small>Check the browser console for details</small>
                </div>
            `;
        }
    }
}

function displayResults(results) {
    const resultsDiv = document.getElementById('results');
    if (!resultsDiv) return;
    
    if (results.length === 0) {
        resultsDiv.innerHTML = `
            <div class="no-results">
                <div class="no-results-icon">🔍</div>
                <p>No photos found matching your search.</p>
                <p><small>Try uploading some photos or searching for different terms.</small></p>
            </div>
        `;
        return;
    }
    
    resultsDiv.innerHTML = results.map(photo => `
        <div class="photo-card" onclick="openImage('${photo.url}')">
            <img 
                src="${photo.url}" 
                alt="Photo"
                onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22280%22 height=%22250%22><rect fill=%22%23ddd%22 width=%22280%22 height=%22250%22/><text x=%2250%%22 y=%2250%%22 font-size=%2218%22 text-anchor=%22middle%22 fill=%22%23999%22>Image Error</text></svg>'"
            >
            <div class="photo-info">
                <div class="labels">
                    ${photo.labels.map(label => 
                        `<span class="label-tag">${escapeHtml(label)}</span>`
                    ).join('')}
                </div>
            </div>
        </div>
    `).join('');
}

function openImage(url) {
    window.open(url, '_blank');
}

function handleSearchKeyPress(event) {
    if (event.key === 'Enter') {
        searchPhotos();
    }
}

// ============================================
// Upload Functionality
// ============================================
function handleFileSelect() {
    const fileInput = document.getElementById('photoFile');
    if (!fileInput) return;
    
    const file = fileInput.files[0];
    
    if (file) {
        console.log('File selected:', file.name, file.type, file.size);
        
        // Clear previous messages
        const uploadMessage = document.getElementById('uploadMessage');
        if (uploadMessage) uploadMessage.innerHTML = '';
        
        // Validate file type
        if (!file.type.startsWith('image/')) {
            showMessage('uploadMessage', 'Please select an image file', 'error');
            fileInput.value = '';
        }
    }
}

async function uploadPhoto() {
    const fileInput = document.getElementById('photoFile');
    const customLabelsInput = document.getElementById('customLabels');
    
    if (!fileInput) {
        alert('File input not found');
        return;
    }
    
    const customLabels = customLabelsInput ? customLabelsInput.value.trim() : '';
    
    // Validate file selection
    if (!fileInput.files || !fileInput.files[0]) {
        showMessage('uploadMessage', 'Please select a file to upload', 'error');
        return;
    }
    
    const file = fileInput.files[0];
    
    // Validate file size (max 5MB)
    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
        showMessage('uploadMessage', 'File is too large. Maximum size is 5MB.', 'error');
        return;
    }

    // Validate file type
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
    if (!validTypes.includes(file.type.toLowerCase())) {
        showMessage('uploadMessage', 'Invalid file type. Please upload JPEG, PNG, or GIF images.', 'error');
        return;
    }
    
    // Create unique filename with timestamp
    const timestamp = Date.now();
    const extension = file.name.split('.').pop().toLowerCase();
    const baseName = file.name.replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9]/g, '-');
    const fileName = `${baseName}-${timestamp}.${extension}`;

    // const cleanFileName = file.name.replace(/[^a-zA-Z0-9.-]/g, '-');
    // const fileName = `${timestamp}-${cleanFileName}`;
    
    // Show loading state
    showMessage('uploadMessage', '<div class="spinner"></div>Uploading...', 'info');
    
    try {
        console.log('Uploading file:', fileName);
        console.log('File name:', fileName);
        console.log('File type:', file.type);
        console.log('File size:', file.size, 'bytes');
        console.log('Custom labels:', customLabels || '(none)');
        
        const headers = {
            'x-api-key': API_KEY,
            'Content-Type': file.type,
            'x-amz-meta-key': fileName
        };
        
        // Add custom labels if provided
        if (customLabels) {
            headers['x-amz-meta-customLabels'] = customLabels;
        }

        console.log('Request headers:', headers);
        console.log('Endpoint:', `${API_ENDPOINT}/upload`);
        
        // Upload to API Gateway S3 Proxy
        const response = await fetch(
            `${API_ENDPOINT}/upload`,
            {
                method: 'PUT',
                headers: headers,
                body: file
            }
        );
        
        console.log('Upload response status:', response.status);
        console.log('Response headers:', Object.fromEntries([...response.headers.entries()]));
        
        if (response.ok || response.status === 200) {
            showMessage(
                'uploadMessage', 
                `Photo uploaded successfully! It will be indexed in a few seconds. You can then search for it.`,
                'success'
            );
            
            // Clear form
            fileInput.value = '';
            if (customLabelsInput) customLabelsInput.value = '';

            console.log('=== Upload Successful ===');
            
        } else {
            const errorText = await response.text();
            console.error('Upload failed - Status:', response.status);
            console.error('Upload failed - Response:', errorText);
            throw new Error(`Upload failed with status ${response.status}`);
        }
        
    } catch (error) {
        console.error('Upload error:', error);
        showMessage(
            'uploadMessage',
            `Upload failed: ${error.message}. Check the browser console for details.`,
            'error'
        );
    }
}

// ============================================
// Utility Functions
// ============================================
function showMessage(elementId, message, type) {
    const element = document.getElementById(elementId);
    
    // If element doesn't exist, just log and alert
    if (!element) {
        console.error(`Element with id '${elementId}' not found`);
        console.log(message);
        if (type === 'error') {
            alert(message);
        }
        return;
    }
    
    let className = 'success-message';
    if (type === 'error') className = 'error-message';
    if (type === 'info') className = 'loading';
    
    element.innerHTML = `<div class="${className}">${message}</div>`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// Initialization
// ============================================
console.log('Photo Album App Initialized');
console.log('API Endpoint:', API_ENDPOINT);
console.log('Bucket:', BUCKET_NAME);

// Check if configuration is set
if (API_ENDPOINT.includes('YOUR-API-ID')) {
    console.warn('WARNING: Please update the API_ENDPOINT in script.js with your actual API Gateway URL');
}
if (API_KEY === 'YOUR-API-KEY-HERE') {
    console.warn('WARNING: Please update the API_KEY in script.js with your actual API key');
}
if (BUCKET_NAME === 'YOUR-PHOTO-BUCKET-NAME') {
    console.warn('WARNING: Please update the BUCKET_NAME in script.js with your actual S3 bucket name');
}