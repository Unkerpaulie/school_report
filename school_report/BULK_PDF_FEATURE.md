# Bulk PDF Report Generation Feature

## Overview
This feature allows teachers, principals, and administrators to generate PDF files for all student reports in a class for a specific term, and download them as a single ZIP file.

## Features
- **Bulk PDF Generation**: Generate PDF reports for all students in a class with one click
- **Organized File Structure**: PDFs are organized in `media/<school-slug>/<year>/<term>/<class-name>/` directories
- **ZIP Download**: All PDFs are packaged into a single ZIP file for easy download
- **Progress Feedback**: User-friendly loading indicators and success/error messages
- **Automatic Cleanup**: Old PDF files are automatically cleaned up to save disk space
- **Permission Control**: Role-based access (teachers can only generate for their assigned class)
- **Graceful Degradation**: System works even if PDF generation library is not installed

## Technical Implementation

### Dependencies
- **WeasyPrint**: HTML-to-PDF conversion library
- **Python zipfile**: For creating ZIP archives
- **Django**: Web framework integration

### Files Modified/Created
1. **requirements-new.txt**: Added WeasyPrint dependency
2. **reports/views.py**: Added bulk PDF generation view and imports
3. **reports/urls.py**: Added URL pattern for bulk PDF generation
4. **reports/templates/reports/term_class_report_list.html**: Added bulk print button and JavaScript
5. **reports/templates/reports/report_detail.html**: Modified for PDF-friendly rendering
6. **core/utils.py**: Added file cleanup utility function
7. **test_bulk_pdf.py**: Test script for functionality verification

### URL Pattern
```
reports/term/<int:term_id>/class/<int:class_id>/bulk-pdf/
```

### View Function
`bulk_generate_class_reports_pdf(request, school_slug, term_id, class_id)`

## Installation Requirements

### For Development (Windows)
1. Install WeasyPrint dependencies:
   ```bash
   # Install MSYS2 from https://www.msys2.org/
   # In MSYS2 shell:
   pacman -S mingw-w64-x86_64-pango
   
   # Set environment variable (in cmd.exe):
   set WEASYPRINT_DLL_DIRECTORIES=C:\msys64\mingw64\bin
   ```

2. Install Python package:
   ```bash
   pip install weasyprint>=62.0
   ```

### For Production (Linux)
```bash
# Ubuntu/Debian
apt install python3-pip libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0

# Install WeasyPrint
pip install weasyprint>=62.0
```

## Usage

### For Teachers
1. Navigate to your class reports list
2. Click the "Print All Reports" button
3. Wait for PDF generation to complete
4. Download the ZIP file containing all student reports

### For Principals/Administrators
1. Navigate to any class reports list
2. Click the "Print All Reports" button
3. System generates PDFs for all students in that class
4. Download the ZIP file

## File Organization
Generated files are organized as follows:
```
media/
└── <school-slug>/
    └── <year>/
        └── <term>/
            └── <class-name>/
                ├── Student_Name_1_Report.pdf
                ├── Student_Name_2_Report.pdf
                └── Class_Term_Year_Reports.zip
```

## Error Handling
- **Missing WeasyPrint**: Graceful error message with installation instructions
- **No Reports**: User-friendly message when no reports exist
- **Permission Denied**: Role-based access control with appropriate redirects
- **File System Errors**: Proper error handling and user feedback
- **PDF Generation Failures**: Individual student failures don't stop the entire process

## Security Considerations
- **Role-based Access**: Teachers can only generate PDFs for their assigned class
- **File Cleanup**: Automatic cleanup of old files to prevent disk space issues
- **Path Validation**: Secure file path handling to prevent directory traversal
- **Error Logging**: Proper error handling without exposing system details

## Performance Considerations
- **Automatic Cleanup**: Files older than 7 days are automatically removed
- **Individual PDF Cleanup**: Individual PDFs are removed after ZIP creation
- **Progress Feedback**: JavaScript provides user feedback during generation
- **Timeout Handling**: 10-second timeout for user feedback

## Testing
Run the test script to verify functionality:
```bash
python test_bulk_pdf.py
```

## Future Enhancements
- **Progress Bar**: Real-time progress tracking for large classes
- **Email Delivery**: Option to email ZIP file to teachers
- **Custom Templates**: Different PDF templates for different report types
- **Batch Processing**: Queue system for handling multiple simultaneous requests
- **Report Customization**: Options to include/exclude certain sections

## Troubleshooting

### WeasyPrint Installation Issues
- **Windows**: Ensure MSYS2 and Pango are properly installed
- **Linux**: Install system dependencies before pip install
- **macOS**: Use Homebrew for easiest installation

### PDF Generation Failures
- Check Django logs for detailed error messages
- Verify media directory permissions
- Ensure sufficient disk space
- Check WeasyPrint system dependencies

### Performance Issues
- Monitor disk space usage
- Adjust cleanup frequency if needed
- Consider implementing queue system for large schools
