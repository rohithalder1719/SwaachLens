import { Feather } from "@expo/vector-icons";
import Constants from "expo-constants";
import React from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";

import { Hotspot, HotspotFallback, openDirections, severityColor } from "./HotspotShared";

const GREEN = "#15803d";

// Native maps are unavailable in Expo Go (Google/Apple maps disabled) and on web.
const isExpoGo = Constants.executionEnvironment === "storeClient";

let MapView: any = null;
let Marker: any = null;
let Callout: any = null;
if (!isExpoGo && Platform.OS !== "web") {
  try {
    const maps = require("react-native-maps");
    MapView = maps.default;
    Marker = maps.Marker;
    Callout = maps.Callout;
  } catch {
    MapView = null;
  }
}

function regionFor(hotspots: Hotspot[]) {
  if (!hotspots.length) return { latitude: 19.076, longitude: 72.8777, latitudeDelta: 0.08, longitudeDelta: 0.08 };
  const lats = hotspots.map((h) => h.latitude);
  const lngs = hotspots.map((h) => h.longitude);
  const latitude = (Math.min(...lats) + Math.max(...lats)) / 2;
  const longitude = (Math.min(...lngs) + Math.max(...lngs)) / 2;
  const latitudeDelta = Math.max(0.03, (Math.max(...lats) - Math.min(...lats)) * 1.6);
  const longitudeDelta = Math.max(0.03, (Math.max(...lngs) - Math.min(...lngs)) * 1.6);
  return { latitude, longitude, latitudeDelta, longitudeDelta };
}

export default function HotspotMap({ hotspots }: { hotspots: Hotspot[] }) {
  if (!MapView) {
    return <HotspotFallback hotspots={hotspots} note="Live map opens in the installed app build" />;
  }
  return (
    <View testID="hotspot-map" style={styles.card}>
      <MapView style={styles.map} initialRegion={regionFor(hotspots)} showsUserLocation showsMyLocationButton={false}>
        {hotspots.map((h, i) => (
          <Marker key={`${h.label}-${i}`} coordinate={{ latitude: h.latitude, longitude: h.longitude }} testID={`map-marker-${i}`}>
            <View style={[styles.cluster, { backgroundColor: severityColor(h.severity) }]}>
              <Text style={styles.clusterText}>{h.count}</Text>
            </View>
            <Callout tooltip onPress={() => openDirections(h.latitude, h.longitude, h.label)}>
              <View style={styles.callout}>
                <Text style={styles.calloutTitle} numberOfLines={1}>{h.label}</Text>
                <Text style={styles.calloutMeta}>{h.count} open · max severity {h.severity ?? "-"}</Text>
                <View style={styles.calloutButton}>
                  <Feather name="navigation" size={13} color="#fff" />
                  <Text style={styles.calloutButtonText}>Get directions</Text>
                </View>
              </View>
            </Callout>
          </Marker>
        ))}
      </MapView>
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
  map: { height: 220, width: "100%" },
  cluster: { minWidth: 34, height: 34, borderRadius: 17, paddingHorizontal: 6, borderWidth: 3, borderColor: "#fff", alignItems: "center", justifyContent: "center" },
  clusterText: { color: "#fff", fontWeight: "900", fontSize: 13 },
  callout: { backgroundColor: "#fff", borderRadius: 12, padding: 12, width: 200, shadowColor: "#0f172a", shadowOpacity: 0.15, shadowRadius: 8, elevation: 4 },
  calloutTitle: { color: "#0f172a", fontWeight: "800", fontSize: 14 },
  calloutMeta: { color: "#64748b", fontSize: 12, marginTop: 3 },
  calloutButton: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, backgroundColor: GREEN, borderRadius: 9, paddingVertical: 8, marginTop: 10 },
  calloutButtonText: { color: "#fff", fontWeight: "800", fontSize: 12 },
  legend: { backgroundColor: "#fff", padding: 12, flexDirection: "row", alignItems: "center", gap: 7, borderTopWidth: 1, borderTopColor: "#f1f5f9" },
  legendDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#dc2626" },
  legendText: { color: "#334155", fontSize: 12, fontWeight: "700", flex: 1 },
  topBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 7, minHeight: 46, borderTopWidth: 1, borderTopColor: "#f1f5f9", backgroundColor: "#f0fdf4" },
  topBtnText: { color: GREEN, fontWeight: "800", fontSize: 13 },
});
