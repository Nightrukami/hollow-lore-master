import os
import hashlib
from tqdm import tqdm
from pathlib import Path
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from lore_master.core.components import build_embeddings
from lore_master.core.config import get_settings


s = get_settings()
DB_NAME = str(Path(__file__).resolve().parents[3] / s.persist_dir)
KNOWLEDE_BASE = str(Path(__file__).resolve().parents[3] / s.knowlede_dir)

def fetch_documents():
    base = Path(KNOWLEDE_BASE)
    documents = []
    # rglob walks every nested sub-category folder the crawler creates,
    # not just the immediate children of the knowledge-base directory.
    for md_path in tqdm(sorted(base.rglob("*.md")), desc="fetching documents"):
        doc_type = md_path.relative_to(base).parts[0]
        loader = TextLoader(str(md_path), encoding="utf-8")
        for doc in loader.load():
            doc.metadata["doc_type"] = doc_type
            documents.append(doc)
    print("finished fetch doc")
    return documents

def create_chunks(documents):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    print("finished chunks doc")
    return chunks

def _stable_id(chunk) -> str:
    """Deterministic chunk ID from its source file + exact text.

    Chroma assigns a random UUID to every chunk when no ``ids`` are given,
    so re-running ingest on unchanged content still produces a brand-new
    set of record IDs each time. Hashing (source, text) instead means the
    same chunk gets the same ID across runs, while content that actually
    changed naturally gets a new ID.
    """
    source = chunk.metadata.get("source", "")
    digest = hashlib.sha256(f"{source}::{chunk.page_content}".encode("utf-8"))
    return digest.hexdigest()

def create_embeddings(chunks):
    ids = [_stable_id(chunk) for chunk in chunks]

    if os.path.exists(DB_NAME):
        Chroma(persist_directory=DB_NAME, embedding_function=build_embeddings()).delete_collection()

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=build_embeddings(),
        persist_directory=DB_NAME,
        collection_name=s.collection_name,
        ids=ids,
    )

    collection = vectorstore._collection
    count = collection.count()

    sample_embedding = collection.get(limit=1, include=["embeddings"])["embeddings"][0]
    dimensions = len(sample_embedding)
    print(f"There are {count:,} vectors with {dimensions:,} dimensions in the vector store")
    return vectorstore
