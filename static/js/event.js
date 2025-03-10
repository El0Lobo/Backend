document.addEventListener("DOMContentLoaded", function () {
  console.log("Initializing the application...");
  initializeCalendar();
  initializePerformerFields();
  setupEventFormListeners();
});

function initializeCalendar() {
  console.log("Initializing FullCalendar...");
  const calendarEl = document.getElementById("calendar");
  const calendar = new FullCalendar.Calendar(calendarEl, {
    height: "auto",
    locale: "de",
    firstDay: 1,
    initialView: "dayGridMonth",
    events: async function (fetchInfo, successCallback, failureCallback) {
      try {
        console.log("Fetching events for calendar...");
        const userEventsResponse = await fetch("/api/events");
        if (!userEventsResponse.ok) {
          throw new Error(
            `Failed to fetch user events: ${userEventsResponse.statusText}`
          );
        }
        const userEventsData = await userEventsResponse.json();
        const { DateTime } = luxon;

        // Fetch holiday events for current and next year
        const currentYear = new Date().getFullYear();
        const holidayResponses = await Promise.all([
          fetch(
            `https://feiertage-api.de/api/?jahr=${currentYear}&nur_land=BW`
          ),
          fetch(
            `https://feiertage-api.de/api/?jahr=${currentYear + 1}&nur_land=BW`
          ),
        ]);

        const holidayData = await Promise.all(
          holidayResponses.map((res) => res.json())
        );
        console.log("Holiday data:", holidayData);

        // Map holidays to background events
        const holidayBackgroundEvents = holidayData.flatMap((data) =>
          Object.entries(data).map(([key, holiday]) => ({
            start: holiday.datum,
            end: holiday.datum,
            display: "background",
            title: key,
            className: "holiday-background",
          }))
        );

        console.log("Holiday background events:", holidayBackgroundEvents);

        // Map user events to FullCalendar format
        const userEvents = userEventsData.flatMap((event) => {
          const occurrences = [];
          const startDate = DateTime.fromISO(event.date, {
            zone: "Europe/Berlin",
          });
          const endLimit = DateTime.fromJSDate(fetchInfo.end, {
            zone: "Europe/Berlin",
          });

          if (event.weekly) {
            let nextDate = startDate;
            while (nextDate <= endLimit) {
              occurrences.push({
                id: event.id,
                title: event.name,
                start: nextDate.toISODate(),
                description: event.description,
                className: "weekly-event", // Add CSS class for weekly events
                extendedProps: {
                  proposed: event.proposed || false,
                  intern: event.intern || false,
                  entry_time: event.entry_time || null,
                  end_time: event.end_time || null,
                  price: event.price || 0,
                  location: event.location || null,
                  image_path: event.image_path || null,
                  shifts: {
                    theke: event.theke_shift ? event.num_people_per_shift : 0,
                    tür: event.door_shift ? event.num_people_per_shift : 0,
                    double: event.double_shift,
                  },
                  assignments: event.assignments || [], // Add assignments to extendedProps
                },
              });
              nextDate = nextDate.plus({ weeks: 1 });
            }
          } else if (event.monthly) {
            let nextDate = startDate;
            while (nextDate <= endLimit) {
              occurrences.push({
                id: event.id,
                title: event.name,
                start: nextDate.toISODate(),
                description: event.description,
                className: "monthly-event", // Add CSS class for monthly events
                extendedProps: {
                  proposed: event.proposed || false,
                  intern: event.intern || false,
                  entry_time: event.entry_time || null,
                  end_time: event.end_time || null,
                  price: event.price || 0,
                  location: event.location || null,
                  image_path: event.image_path || null,
                  shifts: {
                    theke: event.theke_shift ? event.num_people_per_shift : 0,
                    tür: event.door_shift ? event.num_people_per_shift : 0,
                    double: event.double_shift,
                  },
                  assignments: event.assignments || [], // Add assignments to extendedProps
                },
              });
              nextDate = nextDate.plus({ months: 1 });
            }
          } else {
            occurrences.push({
              id: event.id,
              title: event.name,
              start: event.date,
              description: event.description,
              className: "", // No additional class for non-recurring events
              extendedProps: {
                proposed: event.proposed || false,
                intern: event.intern || false,
                entry_time: event.entry_time || null,
                end_time: event.end_time || null,
                price: event.price || 0,
                location: event.location || null,
                image_path: event.image_path || null,
                shifts: {
                  theke: event.theke_shift ? event.num_people_per_shift : 0,
                  tür: event.door_shift ? event.num_people_per_shift : 0,
                  double: event.double_shift,
                },
                assignments: event.assignments || [], // Add assignments to extendedProps
              },
            });
          }
          return occurrences;
        });

        console.log("Mapped events with assignments:", userEvents); // Log to confirm

        // Combine user-created events and holiday events
        const allEvents = [...userEvents, ...holidayBackgroundEvents];
        console.log("All combined events:", allEvents);

        successCallback(allEvents);
      } catch (error) {
        console.error("Error fetching events:", error);
        failureCallback(error);
      }
    },

    eventContent: function (info) {
      const { event } = info;

      if (!event) {
        console.error("No event provided for rendering.");
        return { domNodes: [] };
      }

      // Create the container
      const container = createEventContainer(event);

      // Check if the event is a holiday
      const isHoliday =
        event.display === "background" &&
        event.classNames.includes("holiday-background");

      if (!isHoliday) {
        // Add "Assign Shift" button for non-holiday events
        addAssignShiftButton(container, event);

        // Add "?" help button for non-holiday events
        addHelpButton(container, event);
      }

      // Add shift checkboxes if available
      if (event.extendedProps.shifts) {
        addShiftCheckBoxes(container, event);
      }

      return { domNodes: [container] };
    },
  });

  calendar.render();
  console.log("Calendar rendered.");
}
function createEventContainer(event) {
  const container = document.createElement("div");
  container.classList.add("custom-event-container");
  container.style.position = "relative";

  // Add special classes based on event properties
  if (event.extendedProps.proposed) container.classList.add("proposed-event");
  if (event.extendedProps.intern) container.classList.add("intern-event");

  // Check if the event is in the past and apply a 'past-event' class
  const eventDate = new Date(event.start);
  const now = new Date();
  // Truncate time from both eventDate and now for comparison
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const eventDay = new Date(
    eventDate.getFullYear(),
    eventDate.getMonth(),
    eventDate.getDate()
  );

  if (eventDay < today) {
    container.classList.add("past-event"); // Add class if the event is in the past
  }

  // Add event title
  const title = document.createElement("div");
  title.textContent = event.title || "Unbenanntes Event";
  title.classList.add("event-title");
  container.appendChild(title);

  return container;
}

function addAssignShiftButton(container, event) {
  const eventDate = new Date(event.start); // Event date
  const now = new Date(); // Current date

  // Truncate time from both eventDate and now for comparison
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const eventDay = new Date(
    eventDate.getFullYear(),
    eventDate.getMonth(),
    eventDate.getDate()
  );

  // Check if the event is strictly in the past
  if (eventDay < today) {
    return; // Do not add the button if the event is in the past
  }

  // Fetch session role and add the button if the user has the correct role
  (async () => {
    const role = await getSessionRole();
    if (role === "Admin" || role === "Vorstand") {
      const assignButton = document.createElement("button");
      assignButton.textContent = "Assign Shift";
      assignButton.classList.add("assign-button");
      assignButton.onclick = () => openAssignModal(event.id);
      container.appendChild(assignButton);
    }
  })();
}

function addHelpButton(container, event) {
  const helpButton = document.createElement("button");
  helpButton.innerHTML = "&#x3F;";
  helpButton.title = "View event details";

  // Apply inline styles to ensure the button is positioned in the top-right corner
  helpButton.style.position = "absolute";
  helpButton.style.top = "0px";
  helpButton.style.right = "0px";

  // Apply existing CSS class for styling
  helpButton.classList.add("help-button");

  helpButton.onclick = () => {
    const eventDetails = `
      Name: ${event.title || "Kein Titel"}
      Datum: ${new Date(event.start).toLocaleDateString("de-DE")}
      Einlasszeit: ${event.extendedProps.entry_time || "Nicht verfügbar"}
      Ende: ${event.extendedProps.end_time || "Nicht verfügbar"}
      Eintritt: ${
        event.extendedProps.price > 0
          ? `${event.extendedProps.price} €`
          : "Kostenlos"
      }
      Intern: ${event.extendedProps.intern ? "Ja" : "Nein"}
    `.trim();
    alert(eventDetails);
  };

  container.appendChild(helpButton);
}

function toggleModal() {
  console.log("Toggling modal...");
  const modal = document.getElementById("eventModal");
  const overlay = document.getElementById("overlay");
  const isModalOpen = modal.style.display === "block";

  modal.style.display = isModalOpen ? "none" : "block";
  overlay.style.display = isModalOpen ? "none" : "block";

  if (isModalOpen) {
    console.log("Modal closed. Resetting form...");
    resetEventForm();
  }
}
function resetEventForm() {
  console.log("Resetting event form...");
  document.getElementById("eventForm").reset();
  toggleEventFields();
  const performerFields = document.getElementById("performerFields");
  performerFields.innerHTML = "";
  initializePerformerFields();
}
function setupEventFormListeners() {
  console.log("Setting up event form listeners...");
  document
    .getElementById("eventForm")
    .addEventListener("submit", function (event) {
      event.preventDefault();
      console.log("Form data before submission:");
      const formData = new FormData(this);
      for (const [key, value] of formData.entries()) {
        console.log(key, value);
      }
      this.submit(); // Uncomment only when verified.
    });

  document
    .getElementById("eventForm")
    .addEventListener("submit", function (event) {
      event.preventDefault(); // Prevent default for debugging

      // Verify form fields
      const name = document.getElementById("event_name").value;
      const date = document.getElementById("event_date").value;

      if (!name || !date) {
        alert("Event name and date are required!");
        return;
      }

      console.log("Submitting form...");
      this.submit();
    });
  document
    .getElementById("schema_type")
    .addEventListener("change", toggleEventFields);
  toggleEventFields();
}
function toggleEventFields() {
  console.log("Toggling event fields...");
  const schemaType = document.getElementById("schema_type").value;
  const holidayBreakFields = document.getElementById("holiday_break_fields");
  const musicDjFields = document.getElementById("music_dj_fields");
  const standardEventFields = document.getElementById("standard_event_fields");

  holidayBreakFields.style.display =
    schemaType === "HolidayBreak" ? "block" : "none";
  musicDjFields.style.display =
    schemaType === "MusicEvent" || schemaType === "DJEvent" ? "block" : "none";
  standardEventFields.style.display =
    schemaType !== "HolidayBreak" ? "block" : "none";

  // Set required attribute based on visibility
  document.getElementById("closed_from").required =
    schemaType === "HolidayBreak";
  document.getElementById("closed_to").required = schemaType === "HolidayBreak";
}
function initializePerformerFields() {
  console.log("Initializing performer fields...");
  const performerFieldsContainer = document.getElementById("performerFields");
  addPerformerField(performerFieldsContainer);
}
function addPerformerField(container) {
  console.log("Adding performer field...");
  const inputWrapper = document.createElement("div");
  inputWrapper.classList.add("performer-input-wrapper");

  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = "Band/DJ Name (Genre)";
  input.className = "performer-input";
  input.autocomplete = "off";

  const suggestions = document.createElement("div");
  suggestions.className = "autocomplete-suggestions";

  input.addEventListener("input", function () {
    fetchAutocompleteSuggestions(input, suggestions);

    const isLastInput = container.lastElementChild === inputWrapper;
    if (input.value.trim() !== "" && isLastInput) {
      addPerformerField(container);
    }
  });

  inputWrapper.appendChild(input);
  inputWrapper.appendChild(suggestions);
  container.appendChild(inputWrapper);
}
function fetchAutocompleteSuggestions(input, suggestionsContainer) {
  console.log(`Fetching autocomplete suggestions for query: "${input.value}"`);
  const query = input.value.trim();
  if (query.length < 2) {
    suggestionsContainer.innerHTML = "";
    return;
  }

  fetch(`/autocomplete_band?q=${encodeURIComponent(query)}`)
    .then((response) => response.json())
    .then((data) => {
      console.log("Autocomplete suggestions:", data);
      suggestionsContainer.innerHTML = "";

      data.forEach((band) => {
        const suggestion = document.createElement("div");
        suggestion.className = "suggestion-item";
        suggestion.textContent = `${band.name} (${band.genre || "Unbekannt"})`;
        suggestion.addEventListener("click", () => {
          input.value = `${band.name} (${band.genre || "Unbekannt"})`;
          suggestionsContainer.innerHTML = "";
        });
        suggestionsContainer.appendChild(suggestion);
      });
    })
    .catch((error) =>
      console.error("Error fetching autocomplete suggestions:", error)
    );
}

function createEventObject(event, date) {
  return {
    id: event.id,
    title: event.name,
    start: date,
    description: event.description,
    extendedProps: {
      proposed: event.proposed || false,
      intern: event.intern || false,
      entry_time: event.entry_time || null,
      end_time: event.end_time || null,
      price: event.price || 0,
      location: event.location || null,
      image_path: event.image_path || null,
      shifts: {
        theke: event.theke_shift ? event.num_people_per_shift : 0,
        tür: event.door_shift ? event.num_people_per_shift : 0,
        double: event.double_shift,
      },
    },
  };
}

function renderEventContent(info) {
  const { event } = info;

  if (!event) {
    console.error("No event provided for rendering.");
    return { domNodes: [] };
  }

  const container = document.createElement("div");
  container.classList.add("custom-event-container");

  // Add special classes based on event properties
  if (event.extendedProps.proposed) {
    container.classList.add("proposed-event");
  }
  if (event.extendedProps.intern) {
    container.classList.add("intern-event");
  }
  if (event.extendedProps && event.extendedProps.shifts) {
    addShiftCheckBoxes(container, event);
  } else {
    console.warn(`No shifts defined for event ${event.id}`);
  }
  // Add event title
  const title = document.createElement("div");
  title.textContent = event.title || "Unbenanntes Event";
  title.classList.add("event-title");
  container.appendChild(title);

  // Check if the event is a holiday (has the "holiday-background" class)
  const isHoliday = event.classNames.includes("holiday-background");

  if (!isHoliday) {
    // Add "Assign Shift" button only for non-holiday events
    (async () => {
      const role = await getSessionRole();
      if (role === "Admin" || role === "Vorstand") {
        const assignButton = document.createElement("button");
        assignButton.textContent = "Assign Shift";
        assignButton.classList.add("assign-button");
        assignButton.onclick = () => openAssignModal(event.id);
        container.appendChild(assignButton);
      }
    })();

    // Add "?" help button only for non-holiday events
    const helpButton = document.createElement("button");
    helpButton.innerHTML = "&#x3F;";
    helpButton.classList.add("help-button");
    helpButton.title = "View event details";

    helpButton.onclick = () => {
      let eventDetails = `Name: ${event.title || "Kein Titel"}\n`;
      if (event.start) {
        const formattedDate = new Date(event.start).toLocaleDateString("de-DE");
        eventDetails += `Datum: ${formattedDate}\n`;
      }
      if (event.extendedProps.entry_time) {
        eventDetails += `Einlasszeit: ${event.extendedProps.entry_time}\n`;
      }
      if (event.extendedProps.end_time) {
        eventDetails += `Ende: ${event.extendedProps.end_time}\n`;
      }
      if (event.extendedProps.price !== undefined) {
        eventDetails += `Eintritt: ${
          event.extendedProps.price > 0
            ? `${event.extendedProps.price} €`
            : "Kostenlos"
        }\n`;
      }
      alert(eventDetails.trim());
    };
    container.appendChild(helpButton);
  }

  return { domNodes: [container] };
}

function formatEventDetails(event) {
  return `
    Name: ${event.title || "Kein Titel"}
    Datum: ${new Date(event.start).toLocaleDateString("de-DE")}
    Einlasszeit: ${event.extendedProps.entry_time || "Nicht verfügbar"}
    Ende: ${event.extendedProps.end_time || "Nicht verfügbar"}
    Eintritt: ${
      event.extendedProps.price > 0
        ? `${event.extendedProps.price} €`
        : "Kostenlos"
    }
    Ort: ${event.extendedProps.location || "Nicht verfügbar"}
  `.trim();
}

function renderEvents(events) {
  const container = document.getElementById("tile-list");
  if (!container) {
    console.error("Events container not found!");
    return;
  }

  container.innerHTML = ""; // Clear existing content

  events.forEach((event) => {
    if (!event) return;
    const tile = createEventTile(event);
    if (tile) container.appendChild(tile);
  });
}

function createEventTile(event) {
  if (!event || !event.name) {
    console.warn("Skipping invalid event:", event);
    return null;
  }

  const tile = document.createElement("div");
  tile.className = "tile";
  if (event.in_past) tile.classList.add("past");
  if (event.suggested) tile.classList.add("suggested");

  tile.innerHTML = `
    <h3>${event.name}</h3>
    <p>${event.description || "Keine Beschreibung"}</p>
    <p><strong>Datum:</strong> ${new Date(event.date).toLocaleDateString(
      "de-DE"
    )}</p>
    <p><strong>Einlasszeit:</strong> ${
      event.entry_time || "Nicht verfügbar"
    }</p>
    <p><strong>Ende:</strong> ${event.end_time || "Nicht verfügbar"}</p>
    <p><strong>Eintritt:</strong> ${
      event.price > 0 ? `${event.price} €` : "Kostenlos"
    }</p>
    <p><strong>Ort:</strong> ${event.location || "Nicht verfügbar"}</p>
  `;

  return tile;
}

async function getSessionRole() {
  try {
    const response = await fetch("/api/session/role");
    if (response.ok) {
      const data = await response.json();
      return data.role; // Example roles: 'Admin', 'Vorstand', etc.
    } else {
      console.error("Failed to fetch session role:", response.status);
      return null;
    }
  } catch (error) {
    console.error("Error fetching session role:", error);
    return null;
  }
}

async function openAssignModal(eventId) {
  try {
    // Fetch users
    const usersResponse = await fetch("/api/users");
    const users = await usersResponse.json();

    // Fetch event details (shifts and assignments)
    const eventResponse = await fetch(`/api/events/${eventId}`); // Add API to fetch event shifts
    const eventData = await eventResponse.json();

    // Populate users dropdown
    const userSelect = document.getElementById("user-select");
    userSelect.innerHTML = ""; // Clear existing options

    const defaultOption = document.createElement("option");
    defaultOption.textContent = "Select a user";
    defaultOption.disabled = true;
    defaultOption.selected = true;
    userSelect.appendChild(defaultOption);

    users.forEach((user) => {
      const option = document.createElement("option");
      option.value = user.nickname;
      option.textContent = `${user.nickname} (${user.role})`;
      userSelect.appendChild(option);
    });

    // Populate shifts
    const shiftSelect = document.getElementById("shift-select");
    shiftSelect.innerHTML = ""; // Clear existing options

    eventData.shifts.forEach((shift) => {
      const option = document.createElement("option");
      option.value = shift.id;
      option.textContent = `Shift: ${shift.type} (${
        shift.assignedTo || "Unassigned"
      })`;
      shiftSelect.appendChild(option);
    });

    // Display modal
    const assignModal = document.getElementById("assignModal");
    assignModal.dataset.eventId = eventId;
    assignModal.style.display = "block";
  } catch (error) {
    console.error("Error opening assign modal:", error);
  }
}

async function fetchShiftAssignment(eventId, shiftType, schicht, index) {
  try {
    const response = await fetch(
      `/api/shifts/${eventId}/${shiftType}/${schicht}/${index}`
    );
    if (response.ok) {
      return await response.json();
    }
    console.error(
      `Shift assignment fetch failed for ${eventId}-${shiftType}-${schicht}-${index}`
    );
  } catch (error) {
    console.error("Error fetching shift assignment:", error);
  }
  return null;
}

function addShiftCheckBoxes(container, event) {
  const shifts = event.extendedProps.shifts;

  console.log(`Event assignments: ${JSON.stringify(event.assignments)}`); // Add this log

  if (!shifts.theke && !shifts.tür) return;

  const shiftsContainer = document.createElement("div");

  // Add Theke section
  if (shifts.theke > 0) {
    const thekeContainer = document.createElement("div");
    addShiftSection(
      thekeContainer,
      event,
      "Theke",
      shifts.theke,
      shifts.double
    );
    shiftsContainer.appendChild(thekeContainer);
  }

  // Add Tür section
  if (shifts.tür > 0) {
    const tuerContainer = document.createElement("div");
    addShiftSection(tuerContainer, event, "Tür", shifts.tür, shifts.double);
    shiftsContainer.appendChild(tuerContainer);
  }

  container.appendChild(shiftsContainer);
}

async function createShiftCheckbox(event, type, schicht, index) {
  console.log(
    `Creating checkbox for ${type} Schicht ${schicht}, Index ${index}`
  );

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.id = `${type}-${event.id}-${schicht}-${index}`;

  const label = document.createElement("span");
  label.textContent = " benötigt";

  const fragment = document.createDocumentFragment();
  fragment.appendChild(checkbox);
  fragment.appendChild(label);

  console.log(
    `Checkbox for ${type} Schicht ${schicht}, Index ${index} created.`
  );
  return fragment;
}

console.log("User events data:", userEventsData);

// Assign a shift
async function assignShift(eventId, shiftType, schicht, shiftIndex, userNick) {
  try {
    const response = await fetch("/api/shifts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_id: eventId,
        shift_type: shiftType,
        schicht: schicht,
        shift_index: shiftIndex,
        user_nick: userNick,
        date: new Date().toISOString().split("T")[0],
      }),
    });
    if (!response.ok) {
      console.error("Error assigning shift:", await response.text());
    }
  } catch (error) {
    console.error("Error assigning shift:", error);
  }
}

// Unassign a shift
async function unassignShift(eventId, shiftType, schicht, shiftIndex) {
  try {
    const response = await fetch("/api/shifts", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_id: eventId,
        shift_type: shiftType,
        schicht: schicht,
        shift_index: shiftIndex,
        date: new Date().toISOString().split("T")[0],
      }),
    });
    if (!response.ok) {
      console.error("Error unassigning shift:", await response.text());
    }
  } catch (error) {
    console.error("Error unassigning shift:", error);
  }
}

async function addShiftSection(container, event, type, count, isDouble) {
  const typeLabel = document.createElement("div");
  typeLabel.textContent = `${type}:`;
  container.appendChild(typeLabel);

  const totalSchichten = isDouble ? 2 : 1;
  const currentUserNick = await fetchNickname(); // Get the current logged-in user's nickname

  for (let schicht = 1; schicht <= totalSchichten; schicht++) {
    const schichtLabel = document.createElement("div");
    schichtLabel.textContent = `Schicht ${schicht}:`;
    container.appendChild(schichtLabel);

    for (let shiftIndex = 1; shiftIndex <= count; shiftIndex++) {
      const wrapper = document.createElement("div");
      wrapper.classList.add("checkbox-wrapper");

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.id = `${type}-${event.id}-${schicht}-${shiftIndex}`;

      const label = document.createElement("span");
      label.textContent = " benötigt";

      wrapper.appendChild(checkbox);
      wrapper.appendChild(label);

      // Check if this shift is already assigned
      const assignedShift = event.extendedProps.assignments?.find(
        (a) =>
          a.shift_type === type &&
          a.schicht === schicht &&
          a.shift_index === shiftIndex
      );

      console.log(`Shift assignment: ${JSON.stringify(assignedShift)}`);

      if (assignedShift) {
        checkbox.checked = true;
        label.textContent = assignedShift.user_nick; // Show the assigned user's name
        if (assignedShift.user_nick === currentUserNick) {
          // If the logged-in user assigned this shift, allow deselecting
          addDeselectButton(wrapper, event.id, type, schicht, shiftIndex, label, checkbox, container);
        } else {
          checkbox.disabled = true; // Disable for other users
        }
      }

      // Add event listener for new selection
      checkbox.addEventListener("change", async () => {
        if (checkbox.checked) {
          label.textContent = currentUserNick;

          // Disable other checkboxes
          disableOtherCheckboxes(checkbox, container);

          // Send selection to the server
          await assignShift(event.id, type, schicht, shiftIndex, currentUserNick);

          // Add Deselect button
          addDeselectButton(wrapper, event.id, type, schicht, shiftIndex, label, checkbox, container);
        }
      });

      container.appendChild(wrapper);
    }
  }
}

// Helper: Add a Deselect button for the shift
function addDeselectButton(wrapper, eventId, type, schicht, shiftIndex, label, checkbox, container) {
  const deselectButton = document.createElement("button");
  deselectButton.textContent = "Deselect";
  deselectButton.classList.add("deselect-button");

  deselectButton.addEventListener("click", async () => {
    checkbox.checked = false;
    label.textContent = " benötigt";
    enableAllCheckboxes(container);

    // Remove assignment from the server
    await unassignShift(eventId, type, schicht, shiftIndex);
    wrapper.removeChild(deselectButton);
  });

  // Ensure only one Deselect button exists
  const existingButton = wrapper.querySelector(".deselect-button");
  if (existingButton) wrapper.removeChild(existingButton);

  wrapper.appendChild(deselectButton);
}

// Helper: Fetch the current user's nickname
async function fetchNickname() {
  try {
    const response = await fetch("/api/session/nickname");
    if (response.ok) {
      const data = await response.json();
      console.log(`Fetched nickname: ${data.nickname}`);
      return data.nickname;
    }
  } catch (error) {
    console.error("Error fetching nickname:", error);
  }
  return "Unbekannt";
}

// Helper: Disable other checkboxes in the same container
function disableOtherCheckboxes(selectedCheckbox, container) {
  const checkboxes = container.querySelectorAll("input[type='checkbox']");
  checkboxes.forEach((checkbox) => {
    if (checkbox !== selectedCheckbox) {
      checkbox.disabled = true;
    }
  });
}

// Helper: Enable all checkboxes in the same container
function enableAllCheckboxes(container) {
  const checkboxes = container.querySelectorAll("input[type='checkbox']");
  checkboxes.forEach((checkbox) => {
    checkbox.disabled = false;
  });
}
