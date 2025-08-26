document.addEventListener('DOMContentLoaded', () => {
    const videoUpload = document.getElementById('videoUpload');
    const fileNameSpan = document.getElementById('fileName');
    const processButton = document.getElementById('processVideo');
    const estimatedTimeSpan = document.getElementById('estimatedTime');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const qualitySelect = document.getElementById('quality');
    const modelDisplayDiv = document.querySelector('.model-display');

    let selectedFile = null;
    let uploadedFilename = null; // Store the filename returned by the backend

    videoUpload.addEventListener('change', async (event) => {
        selectedFile = event.target.files[0];
        if (selectedFile) {
            fileNameSpan.textContent = selectedFile.name;
            // Upload the file to the backend and then get estimation
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

                // Now get the estimated time
                updateEstimatedTime(uploadedFilename, qualitySelect.value);

            } catch (error) {
                console.error('Error uploading video:', error);
                fileNameSpan.textContent = 'Upload failed.';
                estimatedTimeSpan.textContent = 'N/A';
            }
        } else {
            fileNameSpan.textContent = 'No file chosen';
            estimatedTimeSpan.textContent = 'N/A';
            uploadedFilename = null;
        }
    });

    qualitySelect.addEventListener('change', () => {
        if (uploadedFilename) { // Use uploadedFilename here for consistency
            updateEstimatedTime(uploadedFilename, qualitySelect.value);
        }
    });

    processButton.addEventListener('click', async () => {
        if (uploadedFilename) {
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

            } catch (error) {
                console.error('Error starting video processing:', error);
                alert('Failed to start video processing.');
            }
        } else {
            alert('Please upload a video first.');
        }
    });

    async function updateEstimatedTime(filename, quality) {
        try {
            const response = await fetch('/estimate_time', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    filename: filename,
                    quality: quality,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            estimatedTimeSpan.textContent = `${result.estimated_minutes} minutes`;
        } catch (error) {
            console.error('Error fetching estimated time:', error);
            estimatedTimeSpan.textContent = 'N/A';
        }
    }

    function startProgressPolling(taskId) {
        const eventSource = new EventSource(`/progress/${taskId}`);

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            progressBar.style.width = `${data.progress}%`;
            progressText.textContent = `${data.progress}% Complete - ${data.line}`;

            if (data.status === 'completed') {
                eventSource.close();
                alert('Video processing completed!');
                // Display the 3D model video here
                modelDisplayDiv.innerHTML = ''; // Clear placeholder
                const videoElement = document.createElement('video');
                videoElement.controls = true;
                videoElement.autoplay = true;
                videoElement.loop = true;
                videoElement.src = `/video_result/${taskId}`;
                videoElement.style.width = '100%';
                videoElement.style.maxWidth = '600px';
                modelDisplayDiv.appendChild(videoElement);
            } else if (data.status === 'failed') {
                eventSource.close();
                alert(`Video processing failed: ${data.line}`);
            }
        };

        eventSource.onerror = (error) => {
            console.error('EventSource failed:', error);
            eventSource.close();
            progressText.textContent = 'Error during processing.';
        };
    }
});