document.addEventListener('DOMContentLoaded', () => {
    const videoUpload = document.getElementById('videoUpload');
    const fileNameSpan = document.getElementById('fileName');
    const processButton = document.getElementById('processVideo');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const qualitySelect = document.getElementById('quality');
    const modelDisplayDiv = document.querySelector('.model-display');
    const modelDisplayPlaceholder = document.getElementById('modelDisplayPlaceholder');

    // New export elements
    const exportSection = document.querySelector('.export-section');
    const exportIngpButton = document.getElementById('exportIngp');
    const exportObjButton = document.getElementById('exportObj');
    const exportPlyButton = document.getElementById('exportPly');

    let selectedFile = null;
    let uploadedFilename = null; // Store the filename returned by the backend
    let currentTaskId = null; // Store the current task ID for exports

    videoUpload.addEventListener('change', async (event) => {
        selectedFile = event.target.files[0];
        if (selectedFile) {
            fileNameSpan.textContent = selectedFile.name;
            // Upload the file to the backend
            try {
                const formData = new FormData();
                formData.append('video', selectedFile);

                const uploadResponse = await fetch('/upload_video', {
                    method: 'POST',
                    body: formData,
                });

                if (!uploadResponse.ok) {
                    throw new Error(`HTTP error! status: ${uploadResponse.status}`);
                }

                const uploadResult = await uploadResponse.json();
                uploadedFilename = uploadResult.filename; // Save the filename from backend
                console.log('Upload successful:', uploadResult.message, 'filename:', uploadedFilename);

                // Removed: updateEstimatedTime(uploadedFilename, qualitySelect.value);

            } catch (error) {
                console.error('Error uploading video:', error);
                fileNameSpan.textContent = 'Upload failed.';
                // Removed: estimatedTimeSpan.textContent = 'N/A';
            }
        } else {
            fileNameSpan.textContent = 'No file chosen';
            // Removed: estimatedTimeSpan.textContent = 'N/A';
            uploadedFilename = null;
        }
    });

    // Removed: qualitySelect.addEventListener('change', () => {
    // Removed:     if (uploadedFilename) {
    // Removed:         updateEstimatedTime(uploadedFilename, qualitySelect.value);
    // Removed:     }
    // Removed: });

    processButton.addEventListener('click', async () => {
        if (uploadedFilename) {
            // Reset progress bar and text
            progressBar.style.width = '0%';
            progressText.textContent = '0% Complete';
            modelDisplayDiv.innerHTML = ''; // Clear previous video
            modelDisplayPlaceholder.style.display = 'block'; // Show placeholder

            console.log('Processing video:', uploadedFilename, 'with quality:', qualitySelect.value);
            try {
                const processResponse = await fetch('/process_video', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        filename: uploadedFilename,
                        quality: qualitySelect.value,
                    }),
                });

                if (!processResponse.ok) {
                    throw new Error(`HTTP error! status: ${processResponse.status}`);
                }

                const processResult = await processResponse.json();
                console.log('Processing started:', processResult.message, 'Task ID:', processResult.task_id);
                // Start polling for progress updates
                startProgressPolling(processResult.task_id);
                currentTaskId = processResult.task_id; // Store taskId for export

            } catch (error) {
                console.error('Error starting video processing:', error);
                alert('Failed to start video processing.');
            }
        } else {
            alert('Please upload a video first.');
        }
    });

    // Removed: async function updateEstimatedTime(filename, quality) {
    // Removed:     try {
    // Removed:         const response = await fetch('/estimate_time', {
    // Removed:             method: 'POST',
    // Removed:             headers: {
    // Removed:                 'Content-Type': 'application/json',
    // Removed:             },
    // Removed:             body: JSON.stringify({
    // Removed:                 filename: filename,
    // Removed:                 quality: quality,
    // Removed:             }),
    // Removed:         });
    // Removed: 
    // Removed:         if (!response.ok) {
    // Removed:             throw new Error(`HTTP error! status: ${response.status}`);
    // Removed:         }
    // Removed: 
    // Removed:         const result = await response.json();
    // Removed:         estimatedTimeSpan.textContent = `${result.estimated_minutes} minutes`;
    // Removed:     } catch (error) {
    // Removed:         console.error('Error fetching estimated time:', error);
    // Removed:         estimatedTimeSpan.textContent = 'N/A';
    // Removed:     }
    // Removed: }

    function startProgressPolling(taskId) {
        const eventSource = new EventSource(`/progress/${taskId}`);

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Received progress data:', data);

            progressBar.style.width = `${data.progress}%`;
            progressText.textContent = `${data.progress}% Complete - ${data.line}`;

            if (data.status === 'completed') {
                eventSource.close();
                alert('Video processing completed!');
                modelDisplayPlaceholder.style.display = 'none'; // Hide placeholder
                const videoElement = document.createElement('video');
                videoElement.controls = true;
                videoElement.autoplay = true;
                videoElement.loop = true;
                videoElement.src = `/video_result/${taskId}`;
                videoElement.style.width = '100%';
                videoElement.style.maxWidth = '600px';
                modelDisplayDiv.appendChild(videoElement);
                // Ensure progress bar shows 100% on successful completion
                progressBar.style.width = '100%';
                progressText.textContent = '100% Complete';

                // Show export options
                exportSection.style.display = 'block';
            } else if (data.status === 'failed') {
                eventSource.close();
                alert(`Video processing failed: ${data.line}`);
                progressText.textContent = `Failed: ${data.line}`;
            }
        };

        eventSource.onerror = (error) => {
            console.error('EventSource failed:', error);
            eventSource.close();
            progressText.textContent = 'Error during processing.';
        };
    }

    // Handle export button clicks
    exportIngpButton.addEventListener('click', () => downloadFile('ingp'));
    exportObjButton.addEventListener('click', () => downloadFile('obj'));
    exportPlyButton.addEventListener('click', () => downloadFile('ply'));

    async function downloadFile(format) {
        if (!currentTaskId) {
            alert('No NeRF model has been processed yet.');
            return;
        }

        try {
            const response = await fetch(`/export_model/${currentTaskId}/${format}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const blob = await response.blob();
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = `model.${format}`;

            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1];
                }
            }

            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error(`Error downloading ${format} file:`, error);
            alert(`Failed to download ${format} file.`);
        }
    }
});