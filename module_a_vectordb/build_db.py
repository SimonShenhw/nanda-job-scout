from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)
from langchain_community.vectorstores import Chroma

print("1. 正在读取 resume_tips.txt...")
loader = TextLoader("resume_tips.txt")
documents = loader.load()

print("2. 正在切割文本...")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=350,  # 刚好能完整包住最长的一条Tip
    chunk_overlap=50,  # 留一点点重叠，防止极端情况切断单词
)
docs = text_splitter.split_documents(documents)

print("3. 正在转换向量并存入数据库 (首次运行会自动下载模型权重，存放在外置硬盘中)...")
embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

# 数据将保存在当前目录下的 chroma_data 文件夹中
db = Chroma.from_documents(docs, embedding_function, persist_directory="./chroma_data")

print("✅ 成功！数据库已建立。")
