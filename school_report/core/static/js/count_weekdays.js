function calc_weekdays(term) {
    // Get the start and end date elements
    const startDateField = document.getElementById(`${term}_start_date`);
    const endDateField = document.getElementById(`${term}_end_date`);
    
    // Get the values from the fields
    const startDateStr = startDateField.value;
    const endDateStr = endDateField.value;
    
    // If either date is missing, return 0
    if (!startDateStr || !endDateStr) {
        updateWeekdaysField(term, 0);
        return 0;
    }
    
    // Parse the dates
    const startDate = new Date(startDateStr);
    const endDate = new Date(endDateStr);
    
    // Validate dates
    if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
        console.error('Invalid date format');
        updateWeekdaysField(term, 0);
        return 0;
    }
    
    // If start date is after end date, return 0
    if (startDate > endDate) {
        updateWeekdaysField(term, 0);
        return 0;
    }
    
    // Calculate weekdays
    let weekdays = 0;
    const currentDate = new Date(startDate);
    
    while (currentDate <= endDate) {
        const dayOfWeek = currentDate.getDay();
        // Sunday is 0, Saturday is 6
        if (dayOfWeek !== 0 && dayOfWeek !== 6) {
            weekdays++;
        }
        currentDate.setDate(currentDate.getDate() + 1);
    }
    
    // Update the result field
    updateWeekdaysField(term, weekdays);
    return weekdays;
}

// Helper function to update the weekdays field
function updateWeekdaysField(term, value) {
    const resultField = document.getElementById(`${term}_weekdays`);
    if (resultField) {
        resultField.value = value;
    }
}