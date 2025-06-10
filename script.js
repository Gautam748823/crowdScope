document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const videoFeed = document.getElementById('video-feed');
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    const headCount = document.getElementById('head-count');
    const recordingStatus = document.getElementById('recording-status');
    const motionStatus = document.getElementById('motion-status');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const refreshBtn = document.getElementById('refresh-btn');
    const recordingsList = document.getElementById('recordings-list');
    
    // API endpoints
    const API_BASE_URL = window.location.origin;
    const VIDEO_FEED_URL = `${API_BASE_URL}/video_feed`;
    const STATUS_URL = `${API_BASE_URL}/status`;
    const RECORDINGS_URL = `${API_BASE_URL}/recordings`;
    
    // State variables
    let isRunning = true;
    let statusInterval = null;
    
    // Fetch system status periodically
    function startStatusUpdates() {
        // Clear any existing interval
        if (statusInterval) {
            clearInterval(statusInterval);
        }
        
        // Update status immediately
        updateStatus();
        
        // Set interval for status updates
        statusInterval = setInterval(updateStatus, 1000);
    }
    
    // Stop status updates
    function stopStatusUpdates() {
        if (statusInterval) {
            clearInterval(statusInterval);
            statusInterval = null;
        }
    }
    
    // Update system status
    async function updateStatus() {
        try {
            const response = await fetch(STATUS_URL);
            const data = await response.json();
            
            // Update head count
            headCount.textContent = data.headCount;
            
            // Update recording status
            if (data.recording) {
                recordingStatus.textContent = 'Recording';
                statusIndicator.className = 'status-indicator recording';
            } else {
                recordingStatus.textContent = 'Not Recording';
                statusIndicator.className = 'status-indicator monitoring';
            }
            
            // Update status text
            statusText.textContent = data.status;
            
            // Update motion status
            motionStatus.textContent = data.motionStatus;
            
        } catch (error) {
            console.error('Error fetching status:', error);
        }
    }
    
    // Fetch and display recordings
    async function fetchRecordings() {
        try {
            const response = await fetch(RECORDINGS_URL);
            const recordings = await response.json();
            
            // Clear current list
            recordingsList.innerHTML = '';
            
            if (recordings.length === 0) {
                recordingsList.innerHTML = '<p>No recordings found.</p>';
                return;
            }
            
            // Add each recording to the list
            recordings.forEach(recording => {
                const recordingItem = document.createElement('div');
                recordingItem.className = 'recording-item';
                
                // Parse the date from the filename (format: motion_YYYYMMDD_HHMMSS.avi)
                const dateMatch = recording.match(/motion_(\d{8})_(\d{6})\.avi/);
                let dateStr = recording;
                
                if (dateMatch) {
                    const year = dateMatch[1].substring(0, 4);
                    const month = dateMatch[1].substring(4, 6);
                    const day = dateMatch[1].substring(6, 8);
                    const hour = dateMatch[2].substring(0, 2);
                    const minute = dateMatch[2].substring(2, 4);
                    const second = dateMatch[2].substring(4, 6);
                    
                    dateStr = `${year}-${month}-${day} ${hour}:${minute}:${second}`;
                }
                
                recordingItem.innerHTML = `
                    <div class="title">${dateStr}</div>
                    <div class="actions">
                        <button class="btn" onclick="window.location.href='/${OUTPUT_FOLDER}/${recording}'">
                            <i class="fas fa-download"></i> Download
                        </button>
                    </div>
                `;
                
                recordingsList.appendChild(recordingItem);
            });
            
        } catch (error) {
            console.error('Error fetching recordings:', error);
            recordingsList.innerHTML = '<p>Error loading recordings.</p>';
        }
    }
    
    // Initialize the application
    function init() {
        // Set video source
        videoFeed.src = VIDEO_FEED_URL;
        
        // Start status updates
        startStatusUpdates();
        
        // Load initial recordings
        fetchRecordings();
        
        // Event listeners
        startBtn.addEventListener('click', function() {
            if (!isRunning) {
                videoFeed.src = VIDEO_FEED_URL;
                startStatusUpdates();
                isRunning = true;
            }
        });
        
        stopBtn.addEventListener('click', function() {
            if (isRunning) {
                videoFeed.src = '';
                stopStatusUpdates();
                isRunning = false;
                
                // Update UI to show stopped state
                statusText.textContent = 'Stopped';
                statusIndicator.className = 'status-indicator monitoring';
                recordingStatus.textContent = 'Not Recording';
                headCount.textContent = '0';
                motionStatus.textContent = 'System Stopped';
            }
        });
        
        refreshBtn.addEventListener('click', fetchRecordings);
        
        // Handle video errors
        videoFeed.addEventListener('error', function() {
            console.error('Video feed error');
            statusText.textContent = 'Connection Error';
        });
    }
    
    // Start the application
    init();
});