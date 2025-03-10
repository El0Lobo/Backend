  function openEventModal() {
    document.getElementById('eventModal').style.display = 'block';
  }

  function closeEventModal() {
    document.getElementById('eventModal').style.display = 'none';
  }

  function claimShift(eventDate, shiftNumber) {
    fetch('/assign_shift', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: `event_date=${eventDate}&shift_number=${shiftNumber}&username={{ user['name'] }}`
    }).then(response => {
      if (response.ok) {
        window.location.reload();
      } else {
        response.text().then(text => alert(text));
      }
    });
  }

  function unclaimShift(eventDate) {
    fetch('/unassign_shift', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: `event_date=${eventDate}`
    }).then(response => {
      if (response.ok) {
        window.location.reload();
      } else {
        response.text().then(text => alert(text));
      }
    });
  }

  function toggleFields() {
    const eventType = document.getElementById('event_type').value;
    const concertFields = document.getElementById('concert-fields');
    const pauseFields = document.getElementById('pause-fields');

    // Show/Hide fields based on selected event type
    if (eventType === 'Konzert') {
      concertFields.style.display = 'block';
      pauseFields.style.display = 'none';
    } else if (eventType === 'Pause') {
      pauseFields.style.display = 'block';
      concertFields.style.display = 'none';
    } else {
      concertFields.style.display = 'none';
      pauseFields.style.display = 'none';
    }
  }

  // Call toggleFields on page load to display fields based on the default selection
  document.addEventListener("DOMContentLoaded", toggleFields);