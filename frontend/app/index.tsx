import React, { useState } from "react";
import { View, TextInput, Button, StyleSheet, Alert } from "react-native";
import { useRouter } from "expo-router";
import axios from "axios";

const LoginScreen = () => {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleLogin = async () => {
    if (!username || !password) {
      Alert.alert("提示", "請輸入帳號和密碼");
      return;
    }

    try {
      const response = await axios.post("http://172.20.10.4:8000/api/login/", {
        user_acc: username,
        user_psd: password,
      },
      { 
        headers: {
          "Content-Type": "application/json", // 明确设置请求头
        },
      });

      if (response.status === 200 && response.data.status === "success") {
        router.push("/bot");
      } else {
        Alert.alert("提示", "登入失敗，請檢查帳號和密碼");
      }
    } catch (error) {
      console.error("登入過程中發生錯誤:", error);
      Alert.alert("提示", "無法連接到伺服器");
    }
  };

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.input}
        placeholder="請輸入帳號"
        onChangeText={setUsername}
        value={username}
      />
      <TextInput
        style={styles.input}
        placeholder="請輸入密碼"
        onChangeText={setPassword}
        value={password}
        secureTextEntry
      />
      <Button title="登入" onPress={handleLogin} />
    </View>
  );
};

export default LoginScreen;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    padding: 16,
    backgroundColor: "#fff",
  },
  input: {
    height: 40,
    borderColor: "#ccc",
    borderWidth: 1,
    marginBottom: 12,
    paddingHorizontal: 8,
  },
});
