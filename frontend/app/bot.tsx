import React, { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  KeyboardAvoidingView,
  Alert,
  ActivityIndicator,
} from "react-native";
import axiosClient from "../api/axiosClient";
import { useRouter } from "expo-router";

interface Message {
  id: number | null;
  text: string;
  timestamp: string;
  sender: "user" | "bot";
}

export default function BotScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    const initialMessage: Message = {
      id: null,
      text: "您好！我是光田醫院的智慧問答助手。我可以協助您查詢醫院的相關規定和政策。例如您可以詢問：\n1. 「請問休假規定是什麼？」\n2. 「告訴我出勤的相關規定」\n3. 「加班費怎麼計算？」",
      timestamp: new Date().toLocaleTimeString(),
      sender: "bot",
    };

    saveMessageToBackend(initialMessage);
  }, []);

  const saveMessageToBackend = async (message: Message) => {
    try {
      const response = await axiosClient.post("/create_message/", {
        content: message.text,
      });

      if (response.data.status === "success") {
        message.id = response.data.data.id;
        setMessages(prev => [...prev, message]);
      }
    } catch (error) {
      console.error("儲存消息失敗:", error);
      Alert.alert("錯誤", "儲存消息失敗，請稍後再試");
    }
  };

  const handleSendMessage = async () => {
    if (!inputText.trim()) {
      Alert.alert("提示", "請輸入訊息");
      return;
    }

    const userMessage: Message = {
      id: null,
      text: inputText,
      timestamp: new Date().toLocaleTimeString(),
      sender: "user",
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText("");
    setIsLoading(true);

    try {
      // Send message to chat endpoint
      const response = await axiosClient.post("/chat/", {
        question: inputText,
      });

      if (response.data.status === "success") {
        const botMessage: Message = {
          id: response.data.data.id,
          text: response.data.data.answer,
          timestamp: new Date().toLocaleTimeString(),
          sender: "bot",
        };

        setMessages(prev => [...prev, botMessage]);
        flatListRef.current?.scrollToEnd({ animated: true });
      }
    } catch (error) {
      console.error("發送消息失敗:", error);
      Alert.alert("錯誤", "發送消息失敗，請稍後再試");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFeedback = async (messageId: number, feedbackType: string) => {
    try {
      const response = await axiosClient.post("/feedback/", {
        message_id: messageId,
        feedback: feedbackType,
      });

      if (response.data.status === "success") {
        Alert.alert("成功", "反饋已提交");
      } else {
        throw new Error(response.data.message || "反饋提交失敗");
      }
    } catch (error) {
      console.error("反饋錯誤:", error);
      Alert.alert("錯誤", error instanceof Error ? error.message : "反饋提交失敗");
    }
  };

  const renderMessage = ({ item }: { item: Message }) => {
    const isUser = item.sender === "user";
    return (
      <View
        style={[
          styles.messageContainer,
          isUser ? styles.userMessage : styles.botMessage,
        ]}
      >
        <Text style={styles.messageText}>{item.text}</Text>
        <Text style={styles.timestamp}>{item.timestamp}</Text>
        {!isUser && item.id && (
          <View style={styles.feedbackContainer}>
            <TouchableOpacity
              onPress={() => item.id && handleFeedback(item.id, "like")}
              style={styles.feedbackButton}
            >
              <Text>👍</Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={() => item.id && handleFeedback(item.id, "dislike")}
              style={styles.feedbackButton}
            >
              <Text>👎</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    );
  };

  return (
    <KeyboardAvoidingView style={styles.container} behavior="padding">
      <FlatList
        data={messages}
        keyExtractor={(item, index) => item.id?.toString() || `temp-${index}-${Date.now()}`}
        renderItem={renderMessage}
        ref={flatListRef}
        contentContainerStyle={{ paddingBottom: 20 }}
      />
      {isLoading && (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007aff" />
        </View>
      )}
      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          placeholder="請輸入您的訊息..."
          placeholderTextColor="#aaa"
          value={inputText}
          onChangeText={setInputText}
        />
        <TouchableOpacity style={styles.sendButton} onPress={handleSendMessage}>
          <Text style={styles.sendButtonText}>發送</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f5f5f5",
  },
  messageContainer: {
    margin: 10,
    padding: 10,
    borderRadius: 10,
    maxWidth: "80%",
  },
  userMessage: {
    alignSelf: "flex-end",
    backgroundColor: "#007aff",
  },
  botMessage: {
    alignSelf: "flex-start",
    backgroundColor: "#e5e5e5",
  },
  messageText: {
    color: "#000",
  },
  timestamp: {
    fontSize: 10,
    color: "#aaa",
    marginTop: 5,
    alignSelf: "flex-end",
  },
  feedbackContainer: {
    flexDirection: "row",
    justifyContent: "flex-end",
    marginTop: 5,
  },
  feedbackButton: {
    marginHorizontal: 5,
  },
  inputContainer: {
    flexDirection: "row",
    alignItems: "center",
    padding: 10,
    backgroundColor: "#fff",
    borderTopWidth: 1,
    borderColor: "#ccc",
  },
  input: {
    flex: 1,
    height: 40,
    borderColor: "#ccc",
    borderWidth: 1,
    borderRadius: 5,
    paddingHorizontal: 10,
    marginRight: 10,
  },
  sendButton: {
    backgroundColor: "#007aff",
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 5,
  },
  sendButtonText: {
    color: "#fff",
    fontWeight: "bold",
  },
  loadingContainer: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(255, 255, 255, 0.7)",
  },
});
