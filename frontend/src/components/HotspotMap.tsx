import { Feather } from "@expo/vector-icons";
import React from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";
import { WebView } from "react-native-webview";

import { buildLeafletHtml, Hotspot, openDirections } from "./HotspotShared";

const GREEN = "#15803d";

export default function HotspotMap({ hotspots }: { hotspots: Hotspot[] }) {
  const onMessage = (e: any) => {
    try {
      const h = JSON.parse(e.nativeEvent.data);
      openDirections(h.latitude, h.longitude, h.label);
    } catch { /* ignore malformed message */ }
  };
  return (
    <View style={styles.card}>
      <WebView
        testID="hotspot-map"
        originWhitelist={["*"]}
        source={{ html: buildLeafletHtml(hotspots, false) }}
        style={styles.map}
        onMessage={onMessage}
        javaScriptEnabled
        domStorageEnabled
        scrollEnabled={false}
        nestedScrollEnabled
        androidLayerType={Platform.OS === "android" ? "hardware" : undefined}
      />
      <View style={styles.legend}>
        <View style={styles.legendDot} />
        <Text style={styles.legendText}>{hotspots.length} active hotspot{hotspots.length === 1 ? "" : "s"} · tap a pin for directions</Text>
      </View>
      {hotspots.length > 0 && (
        <Pressable testID="directions-top" onPress={() => openDirections(hotspots[0].latitude, hotspots[0].longitude, hotspots[0].label)} style={styles.topBtn}>
          <Feather name="navigation" size={14} color={GREEN} />
          <Text style={styles.topBtnText}>Route to busiest hotspot</Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: "#fff", borderRadius: 19, overflow: "hidden", borderWidth: 1, borderColor: "#bfdbfe" },
  map: { height: 240, width: "100%", backgroundColor: "#e2e8f0" },
  legend: { backgroundColor: "#fff", padding: 12, flexDirection: "row", alignItems: "center", gap: 7, borderTopWidth: 1, borderTopColor: "#f1f5f9" },
  legendDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#dc2626" },
  legendText: { color: "#334155", fontSize: 12, fontWeight: "700", flex: 1 },
  topBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 7, minHeight: 46, borderTopWidth: 1, borderTopColor: "#f1f5f9", backgroundColor: "#f0fdf4" },
  topBtnText: { color: GREEN, fontWeight: "800", fontSize: 13 },
});
