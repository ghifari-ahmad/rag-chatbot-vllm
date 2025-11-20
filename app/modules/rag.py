import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_openai import ChatOpenAI

def setup_rag_pipeline():
    # 1. Setup Embedding Model (BAAI/bge-m3)
    embeddings = HuggingFaceEmbeddings(
        model_name=os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"),
        model_kwargs={'device': 'cpu'}, # Ubah ke 'cuda' jika container App punya akses GPU
        encode_kwargs={'normalize_embeddings': True}
    )

    # 2. Setup Qdrant Client
    client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "qdrant"),
        port=int(os.getenv("QDRANT_PORT", 6333))
    )
    
    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=os.getenv("QDRANT_COLLECTION_NAME", "my_documents"),
        embedding=embeddings,
    )

    # 3. Setup Retriever & Reranker (BAAI/bge-reranker-base)
    base_retriever = vectorstore.as_retriever(search_kwargs={"k": 10}) # Ambil 10 kandidat
    
    model_rerank = HuggingFaceCrossEncoder(
        model_name=os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
    )
    compressor = CrossEncoderReranker(model=model_rerank, top_n=3) # Ambil top 3 setelah rerank
    
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, 
        base_retriever=base_retriever
    )

    # 4. Setup LLM (vLLM via OpenAI Protocol)
    llm = ChatOpenAI(
        model=os.getenv("VLLM_MODEL_NAME"),
        openai_api_key="EMPTY",
        openai_api_base=os.getenv("VLLM_API_BASE"),
        temperature=0.2,
        max_tokens=1024,
        streaming=True 
    )

    return compression_retriever, llm