import { Stack } from "expo-router";

export default function Layout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: "#007aff" },
        headerTintColor: "#fff",
        headerTitleStyle: { fontWeight: "bold" },
      }}
    >
      <Stack.Screen
        name="index"
        options={{
          title: "光田醫院智慧問答系統"
        }}
      />
      <Stack.Screen
        name="bot"
        options={{
          title: "光田醫院智慧問答系統"
        }}
      />
    </Stack>
  );
}
