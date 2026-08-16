// Extends the static app.json config and injects the react-native-maps plugin
// with the Android Google Maps API key from the environment. iOS uses Apple Maps
// (no key required). The map only renders in a native dev/production build —
// Expo Go and web fall back to a hotspot list (see src/components/HotspotMap).
const appJson = require("./app.json");

module.exports = ({ config }) => {
  const base = { ...appJson.expo, ...config };
  const plugins = [...(base.plugins || [])];

  const mapsKey = process.env.GOOGLE_MAPS_API_KEY;
  const androidGoogleMapsApiKey =
    mapsKey && !mapsKey.startsWith("REPLACE_WITH_") ? mapsKey : undefined;

  plugins.push([
    "react-native-maps",
    {
      androidGoogleMapsApiKey,
    },
  ]);

  return { ...base, plugins };
};
