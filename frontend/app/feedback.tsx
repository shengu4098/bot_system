import React, { useEffect, useState } from 'react';
import axiosClient from '../api/axiosClient';

function FeedbackScreen() {
  const [feedbacks, setFeedbacks] = useState([]); // 反饋列表
  const [newFeedback, setNewFeedback] = useState({ message_id: '', feedback_type: '' }); // 用於提交新反饋的狀態

  // 獲取所有反饋數據
  useEffect(() => {
    const fetchFeedbacks = async () => {
      try {
        const response = await axiosClient.get('/feedbacks/');
        setFeedbacks(response.data); // 假設後端返回的是反饋數據列表
      } catch (error) {
        console.error('獲取反饋數據時發生錯誤:', error);
      }
    };

    fetchFeedbacks();
  }, []);

  const handleFeedback = async (messageId, feedbackType) => {
    try {
      const response = await fetch("http://172.20.10.4:8000/api/feedback/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message_id: messageId,  // 確保使用 message_id
          feedback: feedbackType, // 確保使用 feedback
        }),
      });
  
      const responseData = await response.json(); // 解析返回的 JSON
      
      if (response.ok) {
        console.log("反饋成功:", responseData);
        Alert.alert("提示", "反饋提交成功");
      } else {
        console.error("反饋失敗:", responseData);
        Alert.alert("錯誤", responseData.message || "反饋提交失敗");
      }
    } catch (error) {
      console.error("發送反饋時發生錯誤:", error);
      Alert.alert("錯誤", "發送反饋時發生網路錯誤");
    }
  };
}
const handleSendMessage = async () => {
  if (!inputText.trim()) {
    Alert.alert("提示", "請輸入訊息");
    return;
  }

  const userMessage = {
    id: Date.now().toString(),
    text: inputText,
    timestamp: new Date().toLocaleTimeString(),
    sender: "user",
  };

  setMessages((prevMessages) => [...prevMessages, userMessage]);
  setInputText("");

  // 模擬機器人回應
  setTimeout(async () => {
    const botMessage = {
      id: Date.now().toString(), // 生成唯一 ID
      text: `這是機器人的回覆：${inputText}`,
      timestamp: new Date().toLocaleTimeString(),
      sender: "bot",
    };

    setMessages((prevMessages) => [...prevMessages, botMessage]);

    // 儲存到後端
    try {
      await axiosClient.post('/messages/', {
        id: botMessage.id, // 傳遞唯一 ID
        content: botMessage.text,
      });
      console.log("機器人回應已保存到後端");
    } catch (error) {
      console.error("保存機器人回應到後端時發生錯誤:", error);
    }

    flatListRef.current?.scrollToEnd({ animated: true });
  }, 1000);
};

export default FeedbackScreen;
