// Get modal elements
const formModal = document.getElementById("formModal");
const openFormButton = document.getElementById("openFormButton");
const closeButton = document.querySelector(".close-button");

// Helper function to check if today is the user's birthday
const isBirthdayToday = (birthDate) => {
  if (!birthDate) return false;

  const today = new Date();
  const [day, month] = [
    today.getDate().toString().padStart(2, "0"),
    (today.getMonth() + 1).toString().padStart(2, "0"),
  ];

  const [birthDay, birthMonth] = birthDate.split(".").slice(0, 2); // Use correct split method based on date format
  return day === birthDay && month === birthMonth;
};

// Open modal for creating a new user
if (openFormButton) {
  openFormButton.onclick = () => {
    console.log("Create User button clicked");
    resetForm(); // Reset the form for new user creation
    formModal.style.display = "block"; // Show the modal

    // Ensure password is required for new user creation
    const passwordInput = document.getElementById("password");
    if (passwordInput) {
      passwordInput.required = true;
    }
  };
}

// Open modal for editing a user
window.openEditForm = function (member) {
  try {
    console.log("Edit User button clicked", member);

    // Update form title
    const formTitle = document.getElementById("formTitle");
    if (formTitle) {
      formTitle.innerText = "Edit User";
    }

    // Helper function to convert DD.MM.YYYY or Date objects to YYYY-MM-DD for input fields
    const convertToInputDate = (dateStr) => {
      if (!dateStr) return ""; // Return an empty string for null or undefined
      if (typeof dateStr === "string" && dateStr.includes(".")) {
        const [day, month, year] = dateStr.split(".");
        return `${year}-${month}-${day}`;
      }
      if (typeof dateStr === "string" && dateStr.includes("-")) {
        return dateStr; // Already in YYYY-MM-DD format
      }
      console.error("Invalid date format:", dateStr);
      return ""; // Return empty string for invalid formats
    };

    // Map member data to form fields
    const fieldMap = {
      user_id: member[0],
      name: member[1],
      nickname: member[2],
      phone: member[3],
      email: member[4],
      role: member[6],
      street: member[11] || "",
      number: member[12] || "",
      city: member[13] || "",
      postcode: member[14] || "",
      "birth-date": convertToInputDate(member[15]), // Convert birth-date
      patron: member[16] === 1,
      "patron-amount": member[17] || "",
      show_email: member[7] === 1,
      show_phone: member[8] === 1,
      has_key: member[9] === 1,
      paid: member[10] === 1,
      "paid-until": convertToInputDate(member[18]), // Convert paid_until
      "member-since": convertToInputDate(member[21]), // Populate member_since field
      is_birthday: isBirthdayToday(member[15]), // Check if today is their birthday
      description: member[23] || ""
    };

    for (const [id, value] of Object.entries(fieldMap)) {
      const element = document.getElementById(id);
      if (element) {
        if (element.type === "checkbox") {
          element.checked = value;
        } else {
          element.value = value;
        }
      } else {
        console.error(`Element with ID '${id}' not found`);
      }
    }

    // Handle the password field (set placeholder)
    const passwordField = document.getElementById("password");
    if (passwordField) {
        passwordField.value = ""; // Leave blank for security
        passwordField.placeholder = "********"; // Indicate a password exists
    }

    // Show the modal
    formModal.style.display = "block";
  } catch (error) {
    console.error("Error in openEditForm function:", error);
  }
};

// Reset form for creating a new user
function resetForm() {
  const formTitle = document.getElementById("formTitle");
  if (formTitle) {
    formTitle.innerText = "Create User";
  }

  const userForm = document.getElementById("userForm");
  if (userForm) {
    userForm.reset(); // Clear all inputs
  }

  // Explicitly clear specific fields
  const fieldsToClear = [
    "user_id",
    "paid-until",
    "paid-duration",
    "birth-date",
    "member-since",
  ];
  fieldsToClear.forEach((id) => {
    const element = document.getElementById(id);
    if (element) {
      element.value = "";
    }
  });

  // Clear checkboxes
  const checkboxesToClear = [
    "paid",
    "show_email",
    "show_phone",
    "has_key",
    "patron",
    "show_birthday",
  ];
  checkboxesToClear.forEach((id) => {
    const checkbox = document.getElementById(id);
    if (checkbox) {
      checkbox.checked = false;
    }
  });

  // Reset the days-left display
  const daysLeftSpan = document.getElementById("days-left");
  if (daysLeftSpan) {
    daysLeftSpan.innerText = "";
  }
}

// Confirm delete action
function confirmDelete(userId) {
  if (confirm("Are you sure you want to delete this user?")) {
    window.location.href = `/delete_user/${userId}`;
  }
}

// Close modal when clicking outside of it
window.onclick = (event) => {
  if (event.target === formModal) {
    formModal.style.display = "none";
  }
};

// Add event listener to the close button
if (closeButton) {
  closeButton.addEventListener("click", () => {
    formModal.style.display = "none"; // Hide the modal
  });
};

// Autocomplete functionality
const streetInput = document.getElementById("street");
const cityInput = document.getElementById("city");
const postcodeInput = document.getElementById("postcode");
const autocompleteContainer = document.createElement("div");
autocompleteContainer.className = "autocomplete-container";

if (streetInput) {
  streetInput.parentNode.style.position = "relative";
  streetInput.parentNode.appendChild(autocompleteContainer);

  streetInput.addEventListener("input", async (event) => {
    const query = event.target.value;

    if (query.length > 2) {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(
          query
        )}&format=json&addressdetails=1&accept-language=de&limit=5&bounded=1&viewbox=5,55,15,47`
      );

      if (response.ok) {
        const suggestions = await response.json();
        updateAutocomplete(suggestions);
      }
    } else {
      autocompleteContainer.innerHTML = "";
    }
  });
}

function updateAutocomplete(suggestions) {
  autocompleteContainer.innerHTML = "";

  if (suggestions.length === 0) {
    const noResult = document.createElement("div");
    noResult.className = "autocomplete-item";
    noResult.innerText = "Keine Ergebnisse gefunden";
    autocompleteContainer.appendChild(noResult);
    return;
  }

  suggestions.forEach((suggestion) => {
    const suggestionItem = document.createElement("div");
    suggestionItem.className = "autocomplete-item";

    const street =
      suggestion.address.road || suggestion.address.pedestrian || "";
    const city =
      suggestion.address.city ||
      suggestion.address.town ||
      suggestion.address.village ||
      "";
    const postcode = suggestion.address.postcode || "";

    suggestionItem.innerHTML = `<strong>${street}</strong>, ${postcode} ${city}`;
    suggestionItem.onclick = () => {
      streetInput.value = street;
      cityInput.value = city;
      postcodeInput.value = postcode;

      autocompleteContainer.innerHTML = "";
    };

    autocompleteContainer.appendChild(suggestionItem);
  });
}

// Hide suggestions when clicking outside
document.addEventListener("click", (event) => {
  if (
    !streetInput.contains(event.target) &&
    !autocompleteContainer.contains(event.target)
  ) {
    autocompleteContainer.innerHTML = "";
  }
});


const passwordField = document.getElementById("password");
passwordField.addEventListener("input", () => {
    if (passwordField.value) {
        passwordField.style.border = "2px solid green";
    } else {
        passwordField.style.border = "";
    }
});
