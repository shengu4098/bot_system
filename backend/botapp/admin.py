from django.contrib import admin
from .models import Feedback

class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_message_content', 'feedback_type', 'created_at')

    def get_message_content(self, obj):
        # 確保引用的是正確的字段或關聯
        return obj.message.content if obj.message else "無"
    get_message_content.short_description = '機器人回覆的句子'

admin.site.register(Feedback, FeedbackAdmin)
