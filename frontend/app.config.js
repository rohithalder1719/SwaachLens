// The hotspot map now uses Leaflet + OpenStreetMap inside a WebView, which needs
// no native map module and no API key. This config simply passes app.json through.
const appJson = require("./app.json");

module.exports = ({ config }) => ({ ...appJson.expo, ...config });
