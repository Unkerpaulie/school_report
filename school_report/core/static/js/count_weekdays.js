/**
 * Calculate the number of weekdays between two dates (inclusive), excluding Sunday and Saturday
 */
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

    // Calculate weekdays
    let weekdays = 1;
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

/**
 * Set minimum dates for term inputs to ensure they don't overlap
 */
function setupDateConstraints() {
    const term_date_elements = ['term1_start_date', 'term1_end_date', 'term2_start_date', 'term2_end_date', 'term3_start_date', 'term3_end_date'];
    let date_elements = [];
    term_date_elements.forEach(element => {
        date_elements.push(document.getElementById(element));
    });
    for (let i = 0; i < date_elements.length; i++) {
        const element = date_elements[i];
        element.addEventListener('change', function() {
            if (element.value) {
                // get element date
                const nextDay = new Date(element.value);
                const nextDayStr = nextDay.toISOString().split('T')[0];
    
                // Set minimum date and default date for all following dates
                for (let j = i + 1; j < date_elements.length; j++) {
                    date_elements[j].min = nextDayStr;
                    date_elements[j].value = nextDayStr;
                }
            }
        });
    }
}


// Initialize date constraints when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupDateConstraints();
});