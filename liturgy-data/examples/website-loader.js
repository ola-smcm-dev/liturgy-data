/* Website (church-web): read today's data from this repo instead of the Google Sheet.
   Not wired into main.js yet - switch over only after comparing it with the Sheet for a few weeks.
   ES5 style, like the rest of main.js.  ALWAYS insert the text with textContent / escapeHtml(), never raw innerHTML. */
var LITURGY_BASE = "https://ola-smcm-dev.github.io/liturgy-data/";
var LITURGY_CACHE = "ola_liturgy_v1_";

function liturgyGetJson_(path, cb) {
  var key = LITURGY_CACHE + path, cached = null;
  try { cached = JSON.parse(localStorage.getItem(key) || "null"); } catch (e) {}
  if (cached) cb(cached, true);                                    // instant, from this browser's last visit
  fetch(LITURGY_BASE + path)
    .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
    .then(function (data) {
      try { localStorage.setItem(key, JSON.stringify(data)); } catch (e) {}
      cb(data, false);
    })
    .catch(function () { if (!cached) cb(null, false); });
}

/* cb(dayRecordOrNull, index).  dayRecord = {weekday, season, celebrations:[{label, notes, readings:[{ref,title}]}], feasts, obligation, check} */
function liturgyDay(isoDate, cb) {
  liturgyGetJson_("index.json", function (index) {
    if (!index || !index.years[isoDate.slice(0, 4)]) return cb(null, index);
    liturgyGetJson_(index.years[isoDate.slice(0, 4)].file, function (yr) {
      cb(yr && yr.days ? (yr.days[isoDate] || null) : null, index);
    });
  });
}
