from transformers import MarianMTModel, MarianTokenizer

# Model name for Japanese → English
model_name = "Helsinki-NLP/opus-mt-ja-en"

# Load tokenizer and model
tokenizer = MarianTokenizer.from_pretrained(model_name)
model = MarianMTModel.from_pretrained(model_name)

# Input sentence(s)
text = ["異世界黙示録マイノグーラ～破滅の文明で始める世界征服～ 第一話"]

# Tokenize and translate
inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
translated = model.generate(**inputs)

# Decode output
result = tokenizer.batch_decode(translated, skip_special_tokens=True)
print(result)
