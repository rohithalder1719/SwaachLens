import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { buildLeafletHtml, Hotspot } from "./HotspotShared";

// Web: render the same Leaflet map inside a real DOM iframe (react-native-web
// forwards unknown string tags to react-dom). No native module or API key needed.
export default function HotspotMap({ hotspots }: { hotspots: Hotspot[] }) {
  return (
    <View style={styles.card}>
      {React.createElement("iframe", {
        srcDoc: buildLeafletHtml(hotspots, true),
        title: "Live hotspot map",
        style: { border: 0, width: "100%", height: 240, display: "block" },
      })}
      <View style={styles.legend}>
        <View style={styles.legendDot} />
        <Text style={styles.legendText}>{hotspots.length} active hotspot{hotspots.length === 1 ? "" : "s"} · tap a pin for directions</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: "#fff", borderRadius: 19, overflow: "hidden", borderWidth: 1, borderColor: "#bfdbfe" },
  legend: { backgroundColor: "#fff", padding: 12, flexDirection: "row", alignItems: "center", gap: 7, borderTopWidth: 1, borderTopColor: "#f1f5f9" },
  legendDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#dc2626" },
  legendText: { color: "#334155", fontSize: 12, fontWeight: "700", flex: 1 },
});
