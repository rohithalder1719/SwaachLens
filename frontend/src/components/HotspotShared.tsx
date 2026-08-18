import { Feather } from "@expo/vector-icons";
import React from "react";
import { Linking, Platform, Pressable, StyleSheet, Text, View } from "react-native";

export type Hotspot = { label: string; count: number; latitude: number; longitude: number; severity?: number };

const GREEN = "#15803d";

export function openDirections(lat: number, lng: number, label: string) {
  const q = encodeURIComponent(label || "Hotspot");
  const url = Platform.select({
    ios: `http://maps.apple.com/?daddr=${lat},${lng}&q=${q}`,
    android: `geo:${lat},${lng}?q=${lat},${lng}(${q})`,
    default: `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`,
  }) as string;
  Linking.openURL(url).catch(() => Linking.openURL(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`));
}

export function severityColor(sev?: number) {
  if ((sev ?? 0) >= 8) return "#dc2626";
  if ((sev ?? 0) >= 6) return "#f59e0b";
  return "#0284c7";
}

// Real interactive Leaflet + OpenStreetMap map (no API key, works in Expo Go and web).
// `web=true` opens directions in a new browser tab; native posts a message back to RN.
export function buildLeafletHtml(hotspots: Hotspot[], web: boolean) {
  const data = JSON.stringify(hotspots || []);
  const dirAction = web
    ? "window.open('https://www.google.com/maps/dir/?api=1&destination='+h.latitude+','+h.longitude, '_blank');"
    : "if(window.ReactNativeWebView){window.ReactNativeWebView.postMessage(JSON.stringify(h));}";
  return `<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>html,body,#map{height:100%;margin:0;padding:0;background:#e2e8f0}
.leaflet-popup-content{margin:10px 12px;font-family:-apple-system,Roboto,sans-serif;font-size:13px}
.dir-btn{display:block;margin-top:8px;background:#15803d;color:#fff;text-align:center;padding:8px;border-radius:8px;font-weight:700;text-decoration:none}</style>
</head><body><div id="map"></div><script>
function esc(s){return String(s||'').replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c];});}
var hs = ${data};
var map = L.map('map', {zoomControl:true, attributionControl:false});
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom:19}).addTo(map);
var bounds = [];
hs.forEach(function(h, i){
  var color = h.severity>=8 ? '#dc2626' : (h.severity>=6 ? '#f59e0b' : '#0284c7');
  var icon = L.divIcon({className:'', iconSize:[32,32], iconAnchor:[16,16], html:
    '<div style="background:'+color+';color:#fff;border:3px solid #fff;border-radius:18px;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font:700 13px sans-serif;box-shadow:0 2px 6px rgba(0,0,0,.4)">'+h.count+'</div>'});
  var m = L.marker([h.latitude, h.longitude], {icon:icon}).addTo(map);
  m.bindPopup('<b>'+esc(h.label)+'</b><br/>'+h.count+' open \u00b7 severity '+(h.severity||'-')+
    '<a class="dir-btn" href="#" onclick="dir('+i+');return false;">Get directions \u203a</a>');
  bounds.push([h.latitude, h.longitude]);
});
if (bounds.length > 1) { map.fitBounds(bounds, {padding:[45,45], maxZoom:14}); }
else if (bounds.length === 1) { map.setView(bounds[0], 14); }
else { map.setView([19.076, 72.8777], 12); }
function dir(i){ var h = hs[i]; ${dirAction} }
</script></body></html>`;
}

// Static fallback (used if a map ever fails to load).
export function HotspotFallback({ hotspots, note }: { hotspots: Hotspot[]; note?: string }) {
  return (
    <View testID="hotspot-map" style={styles.card}>
      <View style={styles.list}>
        {hotspots.length === 0 ? (
          <Text style={styles.emptyText}>No active hotspots right now.</Text>
        ) : hotspots.map((h, i) => (
          <View key={`row-${h.label}-${i}`} style={styles.row}>
            <View style={[styles.dot, { backgroundColor: severityColor(h.severity) }]} />
            <View style={{ flex: 1 }}>
              <Text style={styles.rowLabel} numberOfLines={1}>{h.label}</Text>
              <Text style={styles.rowMeta}>{h.count} open · max severity {h.severity ?? "-"}</Text>
            </View>
            <Pressable testID={`directions-${i}`} onPress={() => openDirections(h.latitude, h.longitude, h.label)} style={({ pressed }) => [styles.dirButton, pressed && { opacity: 0.7 }]}>
              <Feather name="navigation" size={14} color={GREEN} />
              <Text style={styles.dirText}>Directions</Text>
            </Pressable>
          </View>
        ))}
        {note ? <Text style={styles.note}>{note}</Text> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: "#fff", borderRadius: 19, overflow: "hidden", borderWidth: 1, borderColor: "#bfdbfe" },
  list: { backgroundColor: "#fff", padding: 8 },
  emptyText: { color: "#94a3b8", fontSize: 13, padding: 12, textAlign: "center" },
  note: { color: "#94a3b8", fontSize: 11, padding: 10, textAlign: "center" },
  row: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 10, paddingHorizontal: 8, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: "#f1f5f9" },
  dot: { width: 10, height: 10, borderRadius: 5 },
  rowLabel: { color: "#0f172a", fontWeight: "800", fontSize: 13 },
  rowMeta: { color: "#64748b", fontSize: 11, marginTop: 2 },
  dirButton: { flexDirection: "row", alignItems: "center", gap: 6, borderWidth: 1, borderColor: "#bbf7d0", borderRadius: 10, paddingHorizontal: 11, minHeight: 38, backgroundColor: "#f0fdf4" },
  dirText: { color: GREEN, fontWeight: "800", fontSize: 12 },
});
