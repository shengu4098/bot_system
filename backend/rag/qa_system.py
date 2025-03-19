import os
import re
from langchain_community.document_loaders import TextLoader, UnstructuredPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import docx2txt
import warnings
from PyPDF2 import PdfReader
# from django.conf import settings
# 忽略警告信息
warnings.filterwarnings('ignore')

# 載入環境變量
load_dotenv()

def clean_text(text):
    """文本清理"""
    # 移除多餘空白和特殊字符
    text = re.sub(r'\s+', ' ', text)
    # 統一標點符號（適合中文文檔）
    text = text.replace('，', '。').replace('；', '。').replace('！', '。').replace('？', '。')
    return text.strip()

def load_single_document(file_path):
    """載入單個文檔並處理可能的錯誤"""
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.docx':
            # 處理 Word 文檔
            text = docx2txt.process(file_path)
            text = clean_text(text)
            txt_path = file_path + '.txt'
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text)
            loader = TextLoader(txt_path, encoding='utf-8')
            docs = loader.load()
            os.remove(txt_path)
            return docs
            
        elif file_extension == '.pdf':
            try:
                # 首先嘗試使用 UnstructuredPDFLoader
                loader = UnstructuredPDFLoader(file_path)
                docs = loader.load()
                return docs
            except Exception as e:
                print(f"使用 UnstructuredPDFLoader 失敗，切換到 PdfReader: {str(e)}")
                # 如果 UnstructuredPDFLoader 失敗，使用 PdfReader
                pdf_reader = PdfReader(file_path)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                text = clean_text(text)
                txt_path = file_path + '.txt'
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                loader = TextLoader(txt_path, encoding='utf-8')
                docs = loader.load()
                os.remove(txt_path)
                return docs
                
        else:
            # 其他類型文件
            loader = TextLoader(file_path, encoding='utf-8')
            return loader.load()
            
    except Exception as e:
        print(f"無法載入文件 {file_path}: {str(e)}")
        return []

def format_source(doc):
    """格式化來源文檔內容"""
    # 提取文件名
    metadata = doc.metadata
    filename = metadata.get('source', '未知文件') if metadata else '未知文件'
    filename = os.path.basename(filename)
    filename = filename.replace('.txt', '').replace('.docx', '')
    
    # 從內容中提取章節號
    content = doc.page_content.strip()
    
    # 主要匹配完整的章節號，避免部分匹配
    patterns = [
        r'\b\d+\.\d+\.\d+\b(?!\.\d)',  # 匹配 x.x.x 格式，但不匹配後面還有數字的情況
        r'\b\d+\.\d+\b(?!\.\d)',        # 匹配 x.x 格式，但不匹配後面還有數字的情況
    ]
    
    found_sections = set()  # 使用集合來避免重複
    for pattern in patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            section = match.group()
            pos = match.start()
            # 檢查章節號前後的內容
            before = content[max(0, pos-5):pos].strip()
            after = content[pos+len(section):min(len(content), pos+len(section)+10)].strip()
            
            # 確認這是一個真實的章節號
            if (before == '' or before.endswith(' ') or before.endswith('。') or 
                before.endswith('\n')) and len(after) > 0:
                found_sections.add(section)
    
    # 將找到的章節號排序
    sorted_sections = sorted(list(found_sections))
    
    return {
        'filename': filename,
        'sections': sorted_sections  # 返回所有找到的章節號
    }

def get_source_string(source_documents):
    """從文檔中提取並格式化參考來源字符串"""
    # 收集所有來源的章節號
    all_sections = set()
    filename = None
    
    for doc in source_documents:
        source_info = format_source(doc)
        if source_info:
            filename = source_info['filename']  # 保存文件名
            all_sections.update(source_info['sections'])  # 添加所有章節號
    
    # 生成參考來源字符串
    if filename:
        # 返回檔案名稱，不包含項目符號
        return f'"{filename}"'  # 添加引號
    return '"未知文件"'

def init_qa_system(docs_dir='documents'):
   """初始化QA系統"""
   # 1. 載入文檔
   base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
   docs_dir = os.path.join(base_dir, docs_dir)
   vector_store_path = os.path.join(base_dir, "vector_store")
   os.makedirs(docs_dir, exist_ok=True)
   os.makedirs(vector_store_path, exist_ok=True)
   documents = []
   for filename in os.listdir(docs_dir):
       file_path = os.path.join(docs_dir, filename)
       if os.path.isfile(file_path):
           docs = load_single_document(file_path)
           documents.extend(docs)
   
   if not documents:
       raise Exception("沒有成功載入任何文檔")
   
   # 2. 分割文檔
   text_splitter = RecursiveCharacterTextSplitter(
       chunk_size=250,
       chunk_overlap=125,
       separators=["\n\n", "\n", "。", "，", " ", ""] # 增加中文分隔符
   )
   texts = text_splitter.split_documents(documents)
   
   # 3. 創建向量數據庫
   embeddings = OpenAIEmbeddings()
   vectorstore = Chroma.from_documents(
       documents=texts,
       embedding=embeddings,
       collection_metadata={"hnsw:space": "cosine"},
       persist_directory=vector_store_path
   )
   
   # 4. 創建自定義提示模板
   prompt_template = """你是一個專業的人資助理，專門回答員工關於請假制度的問題。請提供準確且容易理解的答案。

基於以下文件內容回答問題。請注意:
                1. 只使用文件中的資訊回答
                2. 如果文件中找不到相關資訊，請直接說明
                3. 回答需要包含關鍵規定（如天數、條件、薪資等）
                4. 使用條列方式讓回答更清晰

回答格式要求：
1. 每個規定後面標註對應的主要條款編號（如7.5.1，不要使用7.5.1.1這樣的子條款）
2. 最後需要列出引用的主要條款編號，格式為：
   參考條款：[條款編號]

問題: {question}
    
參考文件:
{context}
"""

   PROMPT = PromptTemplate(
       template=prompt_template,
       input_variables=["context", "question"]
   )
   
   # 5. 創建問答鏈
   llm = ChatOpenAI(
       model_name="gpt-3.5-turbo",
       temperature=0
   )
   qa_chain = RetrievalQA.from_chain_type(
       llm=llm,
       chain_type="stuff",
       retriever=vectorstore.as_retriever(
           search_type="mmr",
           search_kwargs={
               "k": 8,
               "fetch_k": 15,
               "lambda_mult": 0.8,
               "score_threshold": 0.6
           }
       ),
       return_source_documents=True,
       chain_type_kwargs={
           "prompt": PROMPT
       }
   )
   
   return qa_chain

def main():
       # 檢查是否設置了 OpenAI API Key
   if not os.getenv("OPENAI_API_KEY"):
       print("請先設置 OPENAI_API_KEY 環境變量")
       return
   
   # 檢查documents目錄是否存在
   if not os.path.exists("backend\documents"):
       print("請創建documents目錄並放入要分析的文檔")
       return
   
   # 初始化 QA 系統
   print("正在初始化 QA 系統...")
   try:
       qa_chain = init_qa_system()
       print("初始化完成！")
   except Exception as e:
       print(f"初始化失敗: {str(e)}")
       return
   
   # 開始問答循環
   print("\n開始問答 (輸入 'q' 退出)")
   while True:
       question = input("\n請輸入您的問題: ")
       
       if question.lower() == 'q':
           print("謝謝使用！")
           break
           
       try:
            # Get the answer and source documents
            result = qa_chain({"query": question})
            answer = result["result"]
            source_docs = result.get("source_documents", [])
            
            # Get source information
            source_string = get_source_string(source_docs)
            
            # Add source information at the end
            if source_string:
                # Add a newline if the answer doesn't end with one
                if not answer.endswith('\n'):
                    answer += '\n'
                answer += f"參考來源：{source_string}"
            
            print("\n回答:", answer)
                    
       except Exception as e:
            print(f"發生錯誤: {str(e)}")

if __name__ == "__main__":
   main()
