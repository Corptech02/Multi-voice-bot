// COI Tool JavaScript Enhancement
// This file provides additional functionality for the COI Tool

// API Configuration
const API_BASE_URL = 'http://localhost:8001';

// Enhanced process email function with better error handling
async function processEmailEnhanced() {
    const emailInput = document.getElementById('email-input').value;
    const processBtn = document.querySelector('.btn-primary');
    const loadingSpinner = document.getElementById('process-loading');
    const messageDiv = document.getElementById('process-message');
    
    if (!emailInput.trim()) {
        showMessage('Please enter an email to process.', 'error');
        return;
    }

    // Show loading state
    processBtn.disabled = true;
    loadingSpinner.style.display = 'inline-block';
    messageDiv.innerHTML = '';

    try {
        // First, get the list of requests to find a valid ID
        const requestsResponse = await fetch(`${API_BASE_URL}/api/v1/requests`);
        if (!requestsResponse.ok) {
            throw new Error('Failed to fetch requests');
        }
        
        const requests = await requestsResponse.json();
        const requestId = requests.length > 0 ? requests[0].id : 'req-001';

        // Process the email
        const response = await fetch(`${API_BASE_URL}/api/v1/requests/${requestId}/process`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email_content: emailInput
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        // Update the UI with the response
        displayExtractedDetailsEnhanced(data);
        displayEmailResponseEnhanced(data.email_response);
        displayCOIPreviewEnhanced(data.preview_url);
        
        // Also handle original_email, extracted_details fields if present
        if (data.original_email) {
            document.getElementById('email-input').value = data.original_email;
        }
        if (data.extracted_details) {
            displayExtractedDetailsEnhanced({ extracted_details: data.extracted_details });
        }
        
        showMessage('Email processed successfully!', 'success');
        
    } catch (error) {
        console.error('Error processing email:', error);
        showMessage('Error processing email: ' + error.message, 'error');
    } finally {
        // Hide loading state
        processBtn.disabled = false;
        loadingSpinner.style.display = 'none';
    }
}

// Enhanced display functions with better formatting
function displayExtractedDetailsEnhanced(data) {
    const detailsList = document.getElementById('extracted-details-list');
    
    if (!data.processed_content && !data.extracted_details) {
        detailsList.innerHTML = '<p style="color: #999;">No details could be extracted.</p>';
        return;
    }

    let extractedData;
    try {
        // Try to parse processed_content first
        if (data.processed_content) {
            extractedData = typeof data.processed_content === 'string' 
                ? JSON.parse(data.processed_content) 
                : data.processed_content;
        } else if (data.extracted_details) {
            extractedData = data.extracted_details;
        }
    } catch (e) {
        extractedData = { message: data.processed_content || 'No details available' };
    }

    let html = '';
    
    // Display extracted fields with better formatting
    const fields = [
        { key: 'project_name', label: 'Project Name', icon: '🏢' },
        { key: 'project_address', label: 'Project Address', icon: '📍' },
        { key: 'certificate_holder', label: 'Certificate Holder', icon: '👤' },
        { key: 'holder_address', label: 'Holder Address', icon: '📮' },
        { key: 'general_liability', label: 'General Liability', icon: '🛡️' },
        { key: 'auto_liability', label: 'Auto Liability', icon: '🚗' },
        { key: 'workers_comp', label: 'Workers Compensation', icon: '👷' },
        { key: 'umbrella_policy', label: 'Umbrella Policy', icon: '☂️' },
        { key: 'additional_insured', label: 'Additional Insured', icon: '➕' },
        { key: 'urgency', label: 'Urgency', icon: '⚡' }
    ];

    fields.forEach(field => {
        const value = extractedData[field.key] || extractedData[field.label];
        if (value) {
            html += `
                <div class="detail-item">
                    <span class="detail-label">${field.icon} ${field.label}:</span> 
                    <span style="color: #2c3e50;">${value}</span>
                </div>
            `;
        }
    });

    // If no specific fields found, display all available data
    if (!html && extractedData) {
        Object.entries(extractedData).forEach(([key, value]) => {
            if (value && key !== 'message') {
                const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                html += `
                    <div class="detail-item">
                        <span class="detail-label">${label}:</span> 
                        <span style="color: #2c3e50;">${value}</span>
                    </div>
                `;
            }
        });
    }

    detailsList.innerHTML = html || '<p style="color: #999;">No specific details extracted.</p>';
}

function displayEmailResponseEnhanced(response) {
    const responseTextarea = document.getElementById('response-preview');
    if (response) {
        responseTextarea.value = response;
        // Auto-resize textarea to fit content
        responseTextarea.style.height = 'auto';
        responseTextarea.style.height = responseTextarea.scrollHeight + 'px';
    } else {
        responseTextarea.value = 'No response generated.';
    }
}

function displayCOIPreviewEnhanced(previewUrl) {
    const previewContainer = document.getElementById('preview-container');
    
    if (!previewUrl) {
        previewContainer.innerHTML = '<p style="color: #999; text-align: center; padding: 20px;">No preview available.</p>';
        return;
    }

    // Convert relative URL to full URL if needed
    const fullUrl = previewUrl.startsWith('http') ? previewUrl : `${API_BASE_URL}${previewUrl}`;
    
    previewContainer.innerHTML = `
        <iframe src="${fullUrl}" class="preview-frame" title="COI Preview"></iframe>
        <div style="margin-top: 10px; text-align: center;">
            <a href="${fullUrl}" target="_blank" class="btn-secondary" style="text-decoration: none; display: inline-block;">
                Open in New Tab
            </a>
            <button onclick="downloadCOI('${fullUrl}')" class="btn-primary" style="margin-left: 10px;">
                Download PDF
            </button>
        </div>
    `;
}

// Download COI function
function downloadCOI(url) {
    const link = document.createElement('a');
    link.href = url;
    link.download = 'COI_' + new Date().toISOString().split('T')[0] + '.pdf';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Auto-save functionality
let autoSaveTimer;
function enableAutoSave() {
    const emailInput = document.getElementById('email-input');
    
    emailInput.addEventListener('input', () => {
        clearTimeout(autoSaveTimer);
        autoSaveTimer = setTimeout(() => {
            localStorage.setItem('coi_draft_email', emailInput.value);
            showMessage('Draft saved', 'success');
        }, 2000);
    });
}

// Load saved draft on page load
function loadSavedDraft() {
    const savedDraft = localStorage.getItem('coi_draft_email');
    if (savedDraft) {
        document.getElementById('email-input').value = savedDraft;
        showMessage('Draft loaded from previous session', 'success');
    }
}

// Enhanced initialization
document.addEventListener('DOMContentLoaded', function() {
    // Replace the original processEmail with enhanced version
    window.processEmail = processEmailEnhanced;
    
    // Enable auto-save
    enableAutoSave();
    
    // Load saved draft
    loadSavedDraft();
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + Enter to process
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            processEmail();
        }
        // Ctrl/Cmd + K to clear
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            clearForm();
        }
    });
    
    // Check backend connectivity
    checkBackendConnection();
});

// Check backend connection
async function checkBackendConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/`);
        const data = await response.json();
        console.log('Backend connected:', data);
    } catch (error) {
        console.error('Backend connection error:', error);
        showMessage('Warning: Backend connection issue. Some features may not work.', 'error');
    }
}

// Export functions for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        processEmailEnhanced,
        displayExtractedDetailsEnhanced,
        displayEmailResponseEnhanced,
        displayCOIPreviewEnhanced
    };
}