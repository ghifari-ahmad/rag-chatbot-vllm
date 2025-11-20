import chainlit as cl
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.runnable.config import RunnableConfig

# Import modules
from modules import setup_rag_pipeline, get_rag_cache

# Setup resources saat startup
retriever, llm = setup_rag_pipeline()
cache = get_rag_cache()

@cl.on_chat_start
async def start():
    # Setup Prompt
    template = """
    Anda adalah asisten AI yang membantu menjawab pertanyaan seputar kebijakan perusahaan.
    Gunakan konteks berikut untuk menjawab pertanyaan pengguna secara akurat dalam bahasa Indonesia.
    Jika konteks tidak memuat jawaban, katakan bahwa Anda tidak tahu.
    Utamakan menjawab dengan spesifik, kemudian ringkas.
    Konteks:
    {context}

    Pertanyaan: {question}
    """
    prompt = ChatPromptTemplate.from_template(template)

    # Buat Chain
    def format_docs(docs):
        return "\n\n".join([d.page_content for d in docs])

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    cl.user_session.set("rag_chain", rag_chain)

@cl.on_message
async def main(message: cl.Message):
    rag_chain = cl.user_session.get("rag_chain")
    user_query = message.content

    # 1. Cek Caching (GPTCache Logic Simple)
    # Kita gunakan cache put/get manual untuk kontrol penuh
    cached_res = cache.get(user_query)
    if cached_res:
        await cl.Message(content=f"(Cached) {cached_res}").send()
        return

    # 2. Jika tidak ada di cache, jalankan RAG
    msg = cl.Message(content="")
    
    full_response = ""
    async for chunk in rag_chain.astream(user_query, config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()])):
        await msg.stream_token(chunk)
        full_response += chunk

    await msg.send()

    # 3. Simpan ke Cache
    cache.put(user_query, full_response)