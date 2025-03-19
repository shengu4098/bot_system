from botapp.models import Message, Feedback
Message.objects.all().delete()
Feedback.objects.all().delete()
