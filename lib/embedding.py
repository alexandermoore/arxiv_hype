from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F
import os
from lib import util


class SentenceTransformer:
    def __init__(self, model="sentence-transformers/all-MiniLM-L6-v2"):
        cache_dir = util.get_env_var("TORCH_HOME", must_exist=True)
        print(f"Using pytorch cache directory: {cache_dir}")
        self._tokenizer = AutoTokenizer.from_pretrained(model, cache_dir=cache_dir)
        self._model = AutoModel.from_pretrained(model, cache_dir=cache_dir)

    @staticmethod
    def _mean_pooling(model_output, attention_mask):
        token_embeddings = model_output[
            0
        ]  # First element of model_output contains all token embeddings
        input_mask_expanded = (
            attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        )
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
            input_mask_expanded.sum(1), min=1e-9
        )

    def embed(self, sentences):
        if not len(sentences):
            return []
        encoded_input = self._tokenizer(
            sentences, padding=True, truncation=True, return_tensors="pt"
        )
        with torch.no_grad():
            model_output = self._model(**encoded_input)
        sentence_embeddings = self._mean_pooling(
            model_output, encoded_input["attention_mask"]
        )
        sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)
        return [x.tolist() for x in sentence_embeddings]

    # def embed_batch(self, sentences, batch_size=16):
    #     results = []
    #     for i in range(0, len(sentences), batch_size):
    #         print(f"{i}/{len(sentences)}")
    #         embeddings = self.embed(sentences[i:i+batch_size])
    #         results.extend(embeddings)
    #     return results
