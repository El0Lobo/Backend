function logout() {
  fetch("/out", { method: "POST" })
    .then(response => {
      if (response.ok) {
        alert("Logged out successfully!");
        location.href = "/login";  // Redirect to login page after logout
      } else {
        alert("Failed to log out.");
      }
    })
    .catch(err => {
      console.error(err);
      alert("Error - " + err.message);
    });
}

function login() {
  var data = new FormData(document.getElementById("login"));

  fetch("/in", { method: "POST", body: data })
    .then(res => {
      if (res.ok) {
        return res.text();
      } else {
        throw new Error("Invalid login attempt");
      }
    })
    .then(txt => {
      if (txt === "OK") {
        // Redirect to the news page after successful login
        window.location.href = "/news";
      } else {
        alert(txt); // Show an alert if there was an issue
      }
    })
    .catch(err => {
      console.error(err);
      alert("Error - " + err.message);
    });
  return false;  // Prevent form submission from refreshing the page
}
