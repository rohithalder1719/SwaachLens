import { Feather, MaterialCommunityIcons } from "@expo/vector-icons";
import React, { useState } from "react";
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, SafeAreaView,
  ScrollView, StyleSheet, Text, TextInput, View,
} from "react-native";

import { Role, useAuth } from "@/src/auth/AuthContext";

const GREEN = "#15803d";

export default function AuthScreen() {
  const { signup, login, loginWithGoogle } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [role, setRole] = useState<Role>("citizen");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError("");
    if (!email.trim() || !password) { setError("Enter your email and password."); return; }
    if (mode === "signup" && !name.trim()) { setError("Enter your name."); return; }
    setBusy(true);
    try {
      if (mode === "signup") {
        await signup({ email: email.trim(), password, name: name.trim(), role, invite_code: inviteCode.trim() });
      } else {
        await login(email.trim(), password);
      }
    } catch (e: any) {
      setError(e?.message || "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const googleLogin = async () => {
    setError(""); setBusy(true);
    try { await loginWithGoogle(); }
    catch { setError("Google sign-in was cancelled."); }
    finally { setBusy(false); }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
          <View style={styles.logo}><MaterialCommunityIcons name="leaf-circle" size={34} color="#fff" /></View>
          <Text style={styles.kicker}>SWACHHLENS</Text>
          <Text style={styles.title}>{mode === "login" ? "Welcome back." : "Create your account."}</Text>
          <Text style={styles.body}>
            {mode === "login" ? "Sign in to report issues or manage cleanup response." : "Join citizens and municipal crews keeping streets clean."}
          </Text>

          {mode === "signup" && (
            <View style={styles.roleRow}>
              {(["citizen", "staff"] as Role[]).map((r) => (
                <Pressable key={r} testID={`role-toggle-${r}`} onPress={() => setRole(r)}
                  style={[styles.roleChip, role === r && styles.roleChipActive]}>
                  <Feather name={r === "citizen" ? "camera" : "briefcase"} size={15} color={role === r ? "#fff" : GREEN} />
                  <Text style={[styles.roleChipText, role === r && styles.roleChipTextActive]}>
                    {r === "citizen" ? "Citizen" : "Municipal staff"}
                  </Text>
                </Pressable>
              ))}
            </View>
          )}

          {mode === "signup" && (
            <>
              <Text style={styles.label}>Full name</Text>
              <TextInput testID="name-input" value={name} onChangeText={setName} placeholder="Your name"
                placeholderTextColor="#94a3b8" style={styles.input} autoCapitalize="words" />
            </>
          )}

          <Text style={styles.label}>Email</Text>
          <TextInput testID="email-input" value={email} onChangeText={setEmail} placeholder="you@example.com"
            placeholderTextColor="#94a3b8" style={styles.input} autoCapitalize="none" keyboardType="email-address" autoComplete="email" />

          <Text style={styles.label}>Password</Text>
          <TextInput testID="password-input" value={password} onChangeText={setPassword} placeholder="••••••••"
            placeholderTextColor="#94a3b8" style={styles.input} secureTextEntry />

          {mode === "signup" && role === "staff" && (
            <>
              <Text style={styles.label}>Municipal invite code</Text>
              <TextInput testID="invite-code-input" value={inviteCode} onChangeText={setInviteCode} placeholder="Enter staff invite code"
                placeholderTextColor="#94a3b8" style={styles.input} autoCapitalize="characters" />
              <Text style={styles.hint}>Ask your municipal admin for the shared code.</Text>
            </>
          )}

          {error ? <Text testID="auth-error" style={styles.error}>{error}</Text> : null}

          <Pressable testID="auth-submit" onPress={submit} disabled={busy}
            style={({ pressed }) => [styles.primary, (pressed || busy) && { opacity: 0.7 }]}>
            {busy ? <ActivityIndicator color="#fff" /> : (
              <>
                <Text style={styles.primaryText}>{mode === "login" ? "Sign in" : "Create account"}</Text>
                <Feather name="arrow-right" size={19} color="#fff" />
              </>
            )}
          </Pressable>

          <View style={styles.dividerRow}><View style={styles.divider} /><Text style={styles.dividerText}>or</Text><View style={styles.divider} /></View>

          <Pressable testID="google-login" onPress={googleLogin} disabled={busy} style={({ pressed }) => [styles.google, pressed && { opacity: 0.7 }]}>
            <MaterialCommunityIcons name="google" size={19} color="#0f172a" />
            <Text style={styles.googleText}>Continue with Google</Text>
          </Pressable>

          <Pressable testID="toggle-mode" onPress={() => { setMode(mode === "login" ? "signup" : "login"); setError(""); }} style={styles.toggle}>
            <Text style={styles.toggleText}>
              {mode === "login" ? "New here? " : "Already have an account? "}
              <Text style={styles.toggleLink}>{mode === "login" ? "Create an account" : "Sign in"}</Text>
            </Text>
          </Pressable>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f8fafc" },
  scroll: { padding: 26, paddingTop: 40, paddingBottom: 40 },
  logo: { backgroundColor: GREEN, width: 60, height: 60, borderRadius: 19, alignItems: "center", justifyContent: "center" },
  kicker: { color: GREEN, fontWeight: "800", letterSpacing: 2, marginTop: 20, fontSize: 12 },
  title: { color: "#0f172a", fontWeight: "900", fontSize: 32, lineHeight: 36, marginTop: 8, letterSpacing: -0.5 },
  body: { color: "#64748b", fontSize: 15, lineHeight: 22, marginTop: 10, maxWidth: 320 },
  roleRow: { flexDirection: "row", gap: 10, marginTop: 24 },
  roleChip: { flex: 1, minHeight: 46, borderRadius: 13, borderWidth: 1, borderColor: "#bbf7d0", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 7 },
  roleChipActive: { backgroundColor: GREEN, borderColor: GREEN },
  roleChipText: { color: "#166534", fontWeight: "800", fontSize: 13 },
  roleChipTextActive: { color: "#fff" },
  label: { color: "#334155", fontWeight: "800", marginTop: 18, marginBottom: 8, fontSize: 13 },
  input: { borderWidth: 1, borderColor: "#e2e8f0", borderRadius: 13, minHeight: 50, paddingHorizontal: 14, color: "#0f172a", fontSize: 15, backgroundColor: "#fff" },
  hint: { color: "#94a3b8", fontSize: 12, marginTop: 6 },
  error: { color: "#dc2626", fontSize: 13, fontWeight: "700", marginTop: 16 },
  primary: { backgroundColor: GREEN, borderRadius: 14, minHeight: 54, marginTop: 22, flexDirection: "row", gap: 10, alignItems: "center", justifyContent: "center" },
  primaryText: { color: "#fff", fontSize: 16, fontWeight: "800" },
  dividerRow: { flexDirection: "row", alignItems: "center", gap: 12, marginTop: 22 },
  divider: { flex: 1, height: 1, backgroundColor: "#e2e8f0" },
  dividerText: { color: "#94a3b8", fontSize: 12, fontWeight: "700" },
  google: { backgroundColor: "#fff", borderWidth: 1, borderColor: "#e2e8f0", borderRadius: 14, minHeight: 54, marginTop: 18, flexDirection: "row", gap: 10, alignItems: "center", justifyContent: "center" },
  googleText: { color: "#0f172a", fontSize: 15, fontWeight: "800" },
  toggle: { alignItems: "center", marginTop: 24 },
  toggleText: { color: "#64748b", fontSize: 14 },
  toggleLink: { color: GREEN, fontWeight: "800" },
});
