import os
import glob
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain.docstore.document import Document

# --- KONFIGURASI ---
DATA_PATH = "/app/data"
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "my_documents")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

def load_and_split_markdowns():
    md_files = glob.glob(f"{DATA_PATH}/*.md")
    all_splits = []

    # 1. Tentukan Header yang ingin dijadikan pemisah
    # Ini akan membuat metadata baru. Contoh: {'Header 1': 'Judul Bab', 'Header 2': 'Sub Bab'}
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    
    # 2. Splitter Cadangan (Jika satu sub-bab masih terlalu panjang > 1024 char)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1024,
        chunk_overlap=100
    )

    print(f"Ditemukan {len(md_files)} file Markdown.")

    for file_path in md_files:
        print(f"Processing: {os.path.basename(file_path)}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Tahap A: Split berdasarkan Header Markdown
            md_header_splits = markdown_splitter.split_text(file_content)

            # Tahap B: Tambahkan metadata asal file (PENTING untuk citasi)
            for doc in md_header_splits:
                doc.metadata["source"] = os.path.basename(file_path)

            # Tahap C: Split lagi jika chunk masih terlalu besar
            final_splits = text_splitter.split_documents(md_header_splits)
            all_splits.extend(final_splits)
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    return all_splits

def ingest():
    print("--- MEMULAI PROSES INGESTION MARKDOWN ---")
    
    # 1. Load & Split
    chunks = load_and_split_markdowns()
    
    if not chunks:
        print("Tidak ada chunks yang dihasilkan. Cek folder data/.")
        return

    print(f"Total chunks (potongan) yang akan disimpan: {len(chunks)}")
    
    # Debug: Print contoh chunk pertama untuk memastikan metadata header masuk
    if len(chunks) > 0:
        print(f"\n[Contoh Chunk Pertama]:\nContent: {chunks[0].page_content[:100]}...")
        print(f"Metadata: {chunks[0].metadata}\n")

    # 2. Inisialisasi Embedding (BAAI/bge-m3)
    print(f"Loading Embedding Model: {EMBEDDING_MODEL}...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'}, 
        encode_kwargs={'normalize_embeddings': True}
    )

    # 3. Upload ke Qdrant
    print(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")
    
    # Menggunakan 'force_recreate=True' HANYA jika Anda ingin menghapus data lama dan menimpa total
    # Jika ingin menambah (append), hapus parameter mode='recreate' (tergantung implementasi library terbaru biasanya default append)
    
    QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        url=f"http://{QDRANT_HOST}:{QDRANT_PORT}",
        collection_name=COLLECTION_NAME,
        force_recreate=True # PERINGATAN: Ini menghapus koleksi lama. Ubah ke False jika ingin append.
    )

    print("--- INGESTION SELESAI ---")
    print(f"Data Markdown tersimpan di Collection: {COLLECTION_NAME}")

if __name__ == "__main__":
    ingest()