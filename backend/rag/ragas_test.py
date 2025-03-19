from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings 
from langchain.text_splitter import RecursiveCharacterTextSplitter
import numpy as np
from ragas import evaluate
from ragas.metrics import LLMContextRecall, Faithfulness,LLMContextPrecisionWithoutReference,ResponseRelevancy
from ragas.llms import LangchainLLMWrapper
from ragas import EvaluationDataset
import os
import docx2txt

class RAG:
    def __init__(self, model="gpt-3.5-turbo"):
        self.llm = ChatOpenAI(model=model,temperature=0)
        self.embeddings = OpenAIEmbeddings()
        self.doc_embeddings = None
        self.docs = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=250,
            chunk_overlap=125,
            separators=["\n\n", "\n", "。", "，", " ", ""] # 增加中文分隔符
        )

    def load_documents(self, directory_path):
        """Load documents from a directory and split them into chunks."""
        all_docs = []
        
        # 直接使用docx2txt讀取文件
        for filename in os.listdir(directory_path):
            if filename.endswith('.docx'):
                file_path = os.path.join(directory_path, filename)
                try:
                    # 使用docx2txt讀取文件內容
                    content = docx2txt.process(file_path)
                    all_docs.append(content)
                    print(f"Successfully loaded: {filename}")
                except Exception as e:
                    print(f"Error loading {filename}: {str(e)}")
        
        if not all_docs:
            raise ValueError("No documents were successfully loaded.")
            
        # 將文件分割成chunks
        texts = []
        for doc in all_docs:
            chunks = self.text_splitter.split_text(doc)
            texts.extend(chunks)
        
        # 儲存文件內容
        self.docs = texts
        
        # 計算embeddings
        print("Computing embeddings...")
        self.doc_embeddings = self.embeddings.embed_documents(self.docs)
        print(f"Loaded {len(self.docs)} document chunks.")

    def get_most_relevant_docs(self, query, top_k=5):
        """Find the top k most relevant documents for a given query."""
        if not self.docs or not self.doc_embeddings:
            raise ValueError("Documents and their embeddings are not loaded.")

        query_embedding = self.embeddings.embed_query(query)
        similarities = [
            np.dot(query_embedding, doc_emb)
            / (np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb))
            for doc_emb in self.doc_embeddings
        ]
        
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        return [self.docs[i] for i in top_indices]

    def generate_answer(self, query, relevant_docs):
        """Generate an answer based on the relevant documents."""
        context = "\n\n".join(relevant_docs)
        
        prompt = f"""基於以下文件內容回答問題。請注意:
                1. 只使用文件中的資訊回答
                2. 如果文件中找不到相關資訊,請直接說明
                3. 回答需要包含關鍵規定(如天數、條件、薪資等)
                4. 使用條列方式讓回答更清晰

        問題: {query}
    
        參考文件:
        {context}
        """
    
        messages = [
            ("system", "你是一個專業的人資助理,專門回答員工關於請假制度的問題。請提供準確且容易理解的答案。"),
            ("human", prompt)
            ]
        
        ai_msg = self.llm.invoke(messages)
        return ai_msg.content

def evaluate_rag():
    try:
        # 初始化RAG
        print("Initializing RAG system...")
        rag = RAG()
        
        # 載入文件
        print("Loading documents...")
        rag.load_documents("./documents")
        
        # 定義測試問題和期望答案
        sample_queries = [
            "請詳細說明產假的申請條件、天數和薪資規定",
            "懷孕幾個月以上流產，可以請幾天假？薪水怎麼算？", 
            "到職滿一年的特休假規定（包含天數、期限和薪資）",
            "父母過世的喪假規定（天數和薪資）",
            "產檢假的申請規定（次數、時數和薪資）",
            "生理假對考績和全勤的影響",
            "育嬰留停的申請資格和期限規定",   
            "哺乳時間的申請條件和時數規定",
            "家庭照顧假的申請條件和限制",
            "請說明事假對考績和全勤的影響"
        ]

        expected_responses = [
            "分娩前後可請產假八週。任職六個月以上給全薪,未滿六個月給半薪。",
            "流產假根據懷孕週數給假:懷孕三個月以上給四週,二到三個月給一週,未滿二個月給五天。",
            "到職滿一年特休七天。特休假薪資照給,需在年度內休完或可延到次年。",
            "父親過世可以請喪假八個工作天,且薪資照給。",
            "懷孕期間可以請產檢假七天(五十六小時),薪資照給。",
            "生理假一年未超過三天不列入考績,不影響全勤獎金。",
            "任職滿六個月可申請育嬰留職停薪,期間至子女滿三歲止,但不得超過二年。",
            "子女未滿二歲須親自哺乳者,每日可另給哺乳時間六十分鐘。",
            "家庭照顧假併入事假計算,一年以七天為限。",
            "除進修事假與家庭照顧假外,事假當月達八小時會影響全勤獎金。"
            ]

        print("\nGenerating answers and evaluating...")
        
        # 建立評估資料集
        dataset = []
        for i, (query, reference) in enumerate(zip(sample_queries, expected_responses)):
            print(f"\nProcessing question {i+1}/{len(sample_queries)}")
            relevant_docs = rag.get_most_relevant_docs(query)
            response = rag.generate_answer(query, relevant_docs)
            dataset.append({
                "user_input": query,
                "retrieved_contexts": relevant_docs,
                "response": response,
                "reference": reference
            })

        # 建立評估資料集物件
        evaluation_dataset = EvaluationDataset.from_list(dataset)

        # 進行評估
        print("\nRunning evaluation metrics...")
        evaluator_llm = LangchainLLMWrapper(rag.llm)

        result = evaluate(
            dataset=evaluation_dataset,
            metrics=[
                LLMContextRecall(),  
                Faithfulness(),      
                LLMContextPrecisionWithoutReference(),
                ResponseRelevancy()
            ],
            llm=evaluator_llm
        )

        print("\nEvaluation Results:")
        print(result)
        
        print("\nDetailed Results:")
        for i, data in enumerate(dataset):
            print(f"\nQuestion {i+1}: {data['user_input']}")
            print(f"Generated Answer: {data['response']}")
            print(f"Expected Answer: {data['reference']}")
            print("-" * 100)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    evaluate_rag()