function logout() {
  fetch("/out", { method: "POST" })
    .then(res => res.text())
    .then(txt => {
      if (txt === "OK") {
        location.href = "/login";  // Redirect to login page after logout
      } else {
        alert(txt);
      }
    })
    .catch(err => {
      console.error(err);
      alert("Error - " + err.message);
    });
  return false;  // Prevent the default behavior of the click
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
