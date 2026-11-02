// Show article times as "25 min ago", falling back to the server-formatted date for older ones
function showRelativeTimes() {
  var now = Date.now();

  document.querySelectorAll('time[data-relative]').forEach(function (el) {
    var published = Date.parse(el.getAttribute('datetime'));
    if (isNaN(published)) {
      return;
    }

    var minutes = Math.round((now - published) / 60000);
    if (minutes < 0 || minutes >= 48 * 60) {
      return;
    }

    el.title = el.textContent.trim();
    if (minutes < 1) {
      el.textContent = 'Just now';
    } else if (minutes < 60) {
      el.textContent = minutes + ' min ago';
    } else {
      var hours = Math.round(minutes / 60);
      el.textContent = hours + (hours === 1 ? ' hour ago' : ' hours ago');
    }
  });
}

// Show the date in the reader's own time zone
function showToday() {
  var el = document.getElementById('today');
  if (el) {
    el.textContent = new Date().toLocaleDateString(undefined, {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
    });
  }
}

// Keep only one dropdown open, and close it when clicking elsewhere or pressing Escape
function setUpMenus() {
  var menus = document.querySelectorAll('.menu');

  menus.forEach(function (menu) {
    menu.addEventListener('toggle', function () {
      if (menu.open) {
        menus.forEach(function (other) {
          if (other !== menu) {
            other.open = false;
          }
        });
      }
    });
  });

  document.addEventListener('click', function (event) {
    menus.forEach(function (menu) {
      if (!menu.contains(event.target)) {
        menu.open = false;
      }
    });
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      menus.forEach(function (menu) {
        if (menu.open) {
          menu.open = false;
          menu.querySelector('summary').focus();
        }
      });
    }
  });
}

showToday();
showRelativeTimes();
setUpMenus();
