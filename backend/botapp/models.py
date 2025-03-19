from django.db import models


class User(models.Model):
    user_acc = models.CharField(max_length=255, unique=True)
    user_psd = models.CharField(max_length=255)

    def __str__(self):
        return self.user_acc

class Message(models.Model):
    content = models.TextField()  # 訊息內容
    response = models.TextField(null=True, blank=True)  # 保留此欄位以維護向後兼容性
    created_at = models.DateTimeField(auto_now_add=True)
    source_documents = models.JSONField(null=True, blank=True)
    is_bot_response = models.BooleanField(default=False)  # 用於區分是否為機器人回答

    def __str__(self):
        prefix = "Bot: " if self.is_bot_response else "User: "
        return f"{prefix}{self.content[:50]}..."

class Feedback(models.Model):
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='feedbacks',
        null=True,  # 允許為空
        blank=True  # 在表單中允許為空
    )
    feedback_type = models.CharField(
        max_length=10,
        choices=[('like', 'Like'), ('dislike', 'Dislike')]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.message:
            response = self.message.response or "No response"
            return f"{self.feedback_type} - {response[:30]}"
        return f"{self.feedback_type} - No message"
