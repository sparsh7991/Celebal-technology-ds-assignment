
import os


from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding



Settings.llm = Ollama(
    model="qwen2.5:3b",
    request_timeout=120
)

Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5"
)

print("Config Loaded Successfully!")