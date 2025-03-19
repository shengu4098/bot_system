import os
from django.core.management.base import BaseCommand
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()

class Command(BaseCommand):
    help = 'Process documents in the specified folder and add them to the vector store'

    def handle(self, *args, **kwargs):
        # 使用 settings.BASE_DIR 作為基準
        documents_dir = os.path.join(settings.BASE_DIR, "documents")  # 確保這個路徑存在
        print(f"檢查文件目錄：{documents_dir}")

        if not os.path.exists(documents_dir):
            print(f"目錄 {documents_dir} 不存在，請確認")
            return

        # 初始化 OpenAI API 金鑰
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            print("請設置 OPENAI_API_KEY 環境變量或 .env 文件")
            return

        # 初始化向量化器
        embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)

        # 加載所有文檔
        all_documents = []
        for file_name in os.listdir(documents_dir):
            file_path = os.path.join(documents_dir, file_name)
            if file_name.endswith(".pdf"):
                loader = PyPDFLoader(file_path)
            elif file_name.endswith(".docx"):
                loader = UnstructuredWordDocumentLoader(file_path)
            else:
                print(f"跳過不支持的文件類型: {file_name}")
                continue

            try:
                docs = loader.load()
                if docs:
                    print(f"成功加載 {len(docs)} 條文檔來自文件: {file_name}")
                    for doc in docs:
                        print(f"文檔摘要: {doc.page_content[:100]}...")  # 打印文檔的部分內容
                    all_documents.extend(docs)
                else:
                    print(f"文件 {file_name} 中無有效內容")
            except Exception as e:
                print(f"處理文件 {file_name} 時發生錯誤: {e}")

        # 如果沒有任何有效文檔，則退出程序
        if not all_documents:
            print("未找到任何有效文檔，請檢查文件格式與內容。")
            return

        # 向量資料庫存儲路徑
        vector_store_path = os.path.join(settings.BASE_DIR, "vector_store")
        try:
            print("正在初始化向量資料庫...")
            vector_store = FAISS.from_documents(all_documents, embeddings)

            # 保存向量資料庫
            vector_store.save_local(vector_store_path)
            print(f"所有文件已成功處理並保存到向量資料庫：{vector_store_path}")
        except Exception as e:
            print(f"向量資料庫操作失敗: {e}")
