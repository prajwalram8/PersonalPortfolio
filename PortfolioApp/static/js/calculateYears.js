// Get today's date
let today = new Date();

// Date for October 2016
let start = new Date(2016, 9, 1); // Note: month is 0-indexed, so 9 is October

// Calculate the difference in years
let diffInMs = today - start;
let diffInDays = diffInMs / (1000 * 60 * 60 * 24);
let diffInYears = Math.floor(diffInDays / 365.25); // Taking into account leap years

// Display the result
document.getElementById("years").innerText = diffInYears;

// ... (existing code)

// Birthdate (change this to your actual birthdate)
let birthdate = new Date(1993, 11, 8);  // Example: January 1, 1990

// Function to calculate age
function calculateAge(birthdate, currentDate) {
    let age = currentDate.getFullYear() - birthdate.getFullYear();
    let m = currentDate.getMonth() - birthdate.getMonth();
    if (m < 0 || (m === 0 && currentDate.getDate() < birthdate.getDate())) {
        age--;
    }
    return age;
}

// Calculate and display age
let age = calculateAge(birthdate, today);
document.getElementById("age").innerText = age;

// ... (rest of the existing code)


