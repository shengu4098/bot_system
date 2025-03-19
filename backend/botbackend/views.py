from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from botapp.models import User, Feedback, Message
from botapp.serializers import UserSerializer, FeedbackSerializer
import json
import os
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from django.conf import settings
from langchain.prompts import PromptTemplate
from rag.qa_system import init_qa_system
from django.views.decorators.csrf import csrf_exempt

# 加載環境變量
load_dotenv()

# 獲取 OpenAI API 金鑰
openai_api_key = os.getenv("OPENAI_API_KEY")
vector_store_path = os.path.join(settings.BASE_DIR, "vector_store")

# 初始化 QA 系統
qa_chain = init_qa_system(docs_dir=os.path.join(settings.BASE_DIR, 'documents'))
def init_qa_system():
    global qa_chain
    if qa_chain is not None:
        return qa_chain
        
    try:
        embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        if os.path.exists(vector_store_path):
            print("載入現有的向量資料庫...")
            vector_store = FAISS.load_local(vector_store_path, embeddings, allow_dangerous_deserialization=True)
            
            # 初始化 QA chain，加入長度限制
            llm = ChatOpenAI(
                temperature=0, 
                model_name="gpt-3.5-turbo",
                max_tokens=4000  # 限制輸出長度
            )
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=vector_store.as_retriever(
                    search_kwargs={
                        "k": 2,  # 減少檢索的文檔數量
                        "fetch_k": 4  # 減少檢索的候選文檔數量
                    }
                ),
                return_source_documents=True,
                chain_type_kwargs={
                    "prompt": PromptTemplate(
                        template="""基於以下資訊回答問題。如果無法從資訊中找到答案，請說明無法回答。

資訊:
{context}

問題: {question}

回答:""",
                        input_variables=["context", "question"]
                    )
                }
            )
            print("QA 系統初始化成功")
            return qa_chain
        else:
            print("向量資料庫不存在，需要重新生成。")
            return None
    except Exception as e:
        print(f"初始化 QA 系統時發生錯誤: {str(e)}")
        return None

# 初始化 QA 系統
qa_chain = init_qa_system()

@csrf_exempt
def chat_response(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('question')
            
            if not question:
                return JsonResponse({"status": "error", "message": "請提供問題"}, status=400)
                
            if qa_chain is None:
                return JsonResponse({"status": "error", "message": "QA 系統未正確初始化"}, status=500)
                
            # 使用 QA chain 獲取答案
            try:
                result = qa_chain.invoke({"query": question})
                answer = result.get("result", "")
                source_docs = result.get("source_documents", [])
                
                # Get source string
                from rag.qa_system import get_source_string
                source_string = get_source_string(source_docs)
                
                # Add source to answer
                if source_string:
                    if not answer.endswith('\n'):
                        answer += '\n'
                    answer += f"參考來源：{source_string}"
                
                # 儲存用戶問題
                user_message = Message.objects.create(
                    content=question,
                    is_bot_response=False
                )
                
                # 儲存機器人回答
                bot_message = Message.objects.create(
                    content=answer,
                    is_bot_response=True
                )
                
                return JsonResponse({
                    "status": "success",
                    "data": {
                        "id": bot_message.id,  # 返回機器人回答的ID
                        "question": question,
                        "answer": answer,
                        "created_at": bot_message.created_at.isoformat()
                    }
                })
            except Exception as e:
                print(f"QA chain 錯誤: {str(e)}")  # 添加錯誤日誌
                return JsonResponse({
                    "status": "error",
                    "message": f"處理問題時發生錯誤: {str(e)}"
                }, status=500)
            
        except json.JSONDecodeError:
            return JsonResponse({
                "status": "error",
                "message": "無效的 JSON 格式"
            }, status=400)
        except Exception as e:
            print(f"未預期的錯誤: {str(e)}")  # 添加錯誤日誌
            return JsonResponse({
                "status": "error",
                "message": f"發生未預期的錯誤: {str(e)}"
            }, status=500)
            
    return JsonResponse({
        "status": "error",
        "message": "只支援 POST 方法"
    }, status=405)
@csrf_exempt
def login_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_acc = data.get('user_acc')
            user_psd = data.get('user_psd')
            user = User.objects.filter(user_acc=user_acc, user_psd=user_psd).first()
            if user:
                return JsonResponse({'status': 'success', 'message': 'Login successful'}, status=200)
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid credentials'}, status=401)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


@csrf_exempt
def create_message(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            content = data.get("content")
            message = Message.objects.create(content=content)
            return JsonResponse({
                "status": "success",
                "data": {
                    "id": message.id,
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                }
            }, status=201)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

@csrf_exempt
def feedback(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message_id = data.get('message_id')
            feedback_type = data.get('feedback')
            
            if not message_id or not feedback_type:
                return JsonResponse({"status": "error", "message": "缺少必要欄位"}, status=400)
            
            message = Message.objects.filter(id=message_id).first()
            if not message:
                return JsonResponse({"status": "error", "message": "訊息不存在"}, status=404)
            
            feedback = Feedback.objects.create(
                message=message,
                feedback_type=feedback_type
            )
            
            return JsonResponse({
                "status": "success",
                "data": {
                    "id": feedback.id,
                    "feedback_type": feedback.feedback_type,
                    "created_at": feedback.created_at.isoformat()
                }
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)
@csrf_exempt
def save_message(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message_id = data.get('id')
            content = data.get('content')

            if not message_id or not content:
                return JsonResponse({"status": "error", "message": "缺少必要的字段"}, status=400)

            # 保存到 Message 表
            message = Message.objects.create(id=message_id, content=content)
            return JsonResponse({"status": "success", "message": "消息保存成功"}, status=201)

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "無效的請求方法"}, status=405)


class QuestionResponseViewSet(ViewSet):
    def list(self, request):
        # 獲取歷史對話記錄
        messages = Message.objects.all().order_by('-created_at')
        return Response({
            "messages": [{
                "id": msg.id,
                "content": msg.content,
                "response": msg.response,
                "created_at": msg.created_at.isoformat()
            } for msg in messages]
        })

    def create(self, request):
        try:
            question = request.data.get('question')
            if not question:
                return Response({"error": "請提供問題"}, status=400)
                
            # 使用 QA chain 獲取答案
            result = qa_chain({"query": question})
            answer = result.get("result", "")
            source_docs = result.get("source_documents", [])
            
            # Get source string
            from rag.qa_system import get_source_string
            source_string = get_source_string(source_docs)
            
            # Add source to answer
            if source_string:
                if not answer.endswith('\n'):
                    answer += '\n'
                answer += f"參考來源：{source_string}"
            
            # 儲存對話記錄
            message = Message.objects.create(
                content=question,
                response=answer
            )
            
            return Response({
                "id": message.id,
                "question": question,
                "answer": answer,
                "created_at": message.created_at.isoformat()
            })
            
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class UserFeedbackViewSet(ViewSet):
    def list(self, request):
        feedbacks = Feedback.objects.all()
        serializer = FeedbackSerializer(feedbacks, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "反饋已成功儲存", "data": serializer.data})
        return Response({"message": "反饋儲存失敗", "errors": serializer.errors}, status=400)

@csrf_exempt
def health_check(request):
    return JsonResponse({
        'status': 'ok',
        'qa_system': 'initialized' if qa_chain else 'not initialized'
    })
