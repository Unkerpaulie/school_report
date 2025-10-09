# Loading Overlay Feature for Report Downloads

## Overview
This feature adds a professional loading overlay with animation to provide user feedback during report download processing. It prevents users from clicking download buttons multiple times and gives clear indication that their request is being processed.

## Features Implemented

### 1. Loading Overlay Component
- **Location**: Added to `core/templates/layout/base.html`
- **Visual Elements**:
  - Semi-transparent dark background overlay
  - Centered white content box with rounded corners
  - Animated spinning loader
  - Customizable message and subtext
  - Fade-in animation

### 2. Download Handler JavaScript Class
- **Location**: `core/static/js/download-handler.js`
- **Features**:
  - Prevents duplicate downloads of the same URL
  - Multiple completion detection methods:
    - Timeout-based fallback
    - Focus change detection
    - Visibility change detection
    - Mouse movement detection
  - Button state management (disables buttons during download)
  - Separate handling for single vs bulk downloads
  - Configurable timeouts and messages

### 3. Integration Points
Updated the following templates to use the loading overlay:

#### Term Class Report List (`reports/templates/reports/term_class_report_list.html`)
- **Button**: "Download All Reports" (bulk download)
- **Behavior**: Shows overlay with message about processing multiple reports
- **Timeout**: 2 minutes (120 seconds)
- **Removed**: Old JavaScript progress feedback system

#### Report Detail (`reports/templates/reports/report_detail.html`)
- **Buttons**: Two "Download Report" buttons (top and bottom navigation)
- **Behavior**: Shows overlay with single report processing message
- **Timeout**: 15 seconds
- **Added**: Test button for superusers to verify overlay functionality

## Technical Implementation

### CSS Styles
```css
.loading-overlay {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background-color: rgba(0, 0, 0, 0.7);
    display: none;
    justify-content: center;
    align-items: center;
    z-index: 9999;
}

.loading-spinner {
    width: 50px; height: 50px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #007bff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

.downloading {
    pointer-events: none;
    opacity: 0.7;
}
```

### JavaScript API
```javascript
// Global instance
window.downloadHandler = new DownloadHandler();

// Main methods
downloadHandler.handleSingleDownload(url)  // For individual reports
downloadHandler.handleBulkDownload(url)    // For bulk downloads
downloadHandler.showLoadingOverlay(message, subtext)
downloadHandler.hideLoadingOverlay()

// Legacy compatibility functions
handleDownloadWithLoading(url)
handleBulkDownloadWithLoading(url)
```

### HTML Integration
```html
<!-- Bulk download button -->
<a href="..." onclick="return window.downloadHandler.handleBulkDownload(this.href);">
    Download All Reports
</a>

<!-- Single download button -->
<a href="..." onclick="return window.downloadHandler.handleSingleDownload(this.href);">
    Download Report
</a>
```

## Download Completion Detection

The system uses multiple methods to detect when downloads complete:

1. **Timeout Fallback**: Always hides overlay after configured timeout
2. **Focus Detection**: Detects when user returns to page after download dialog
3. **Visibility Change**: Monitors page visibility changes
4. **Mouse Movement**: Detects user activity indicating they're back

## Configuration

### Timeouts
- **Single Reports**: 15 seconds
- **Bulk Reports**: 2 minutes (120 seconds)

### Messages
- **Single Reports**: "Generating Report" / "Please wait while your report is being processed..."
- **Bulk Reports**: "Generating Reports" / "Please wait while all reports are being processed. This may take several minutes..."

## Testing

### Manual Testing
1. **Access Report Pages**: Navigate to any report detail page or class report list
2. **Test Single Download**: Click "Download Report" button on report detail page
3. **Test Bulk Download**: Click "Download All Reports" button on class report list
4. **Verify Overlay**: Confirm overlay appears with appropriate message
5. **Verify Completion**: Confirm overlay disappears when download completes

### Superuser Test Button
- **Location**: Report detail pages (only visible to superusers)
- **Button**: "Test Overlay" (blue button with gear icon)
- **Function**: Shows overlay for 5 seconds to verify functionality

### Browser Testing
Test in multiple browsers to ensure compatibility:
- Chrome/Edge (Chromium-based)
- Firefox
- Safari (if available)

## Browser Compatibility

The implementation uses modern JavaScript features but maintains compatibility with:
- ES6+ browsers (2015+)
- All major modern browsers
- Mobile browsers

## Performance Considerations

- **Lightweight**: Minimal CSS and JavaScript overhead
- **Non-blocking**: Doesn't interfere with download process
- **Memory Efficient**: Cleans up resources after completion
- **Prevents Abuse**: Blocks duplicate downloads

## Future Enhancements

Potential improvements for future versions:
1. **Server-side Progress**: Real-time progress updates via WebSocket
2. **Download Queue**: Handle multiple simultaneous downloads
3. **Retry Mechanism**: Automatic retry on failed downloads
4. **Analytics**: Track download success/failure rates
5. **Customization**: User-configurable timeout settings

## Troubleshooting

### Common Issues
1. **Overlay doesn't appear**: Check browser console for JavaScript errors
2. **Overlay doesn't disappear**: Check network tab for download completion
3. **Multiple overlays**: Ensure no duplicate event handlers

### Debug Mode
Add to browser console to enable debug logging:
```javascript
window.downloadHandler.debug = true;
```

## Files Modified

1. `core/templates/layout/base.html` - Added overlay HTML and CSS
2. `core/static/js/download-handler.js` - New JavaScript handler class
3. `reports/templates/reports/term_class_report_list.html` - Updated bulk download button
4. `reports/templates/reports/report_detail.html` - Updated download buttons, added test button

## Dependencies

- **jQuery**: Already included in base template
- **Bootstrap 5**: For styling (already included)
- **Modern Browser**: ES6+ support required
