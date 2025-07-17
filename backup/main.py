from pentago import Pentago
from pentago.lang import AUTO, JAPANESE

# Initialize translator
translator = Pentago(AUTO, JAPANESE)

# Translate Japanese → English
result = translator.translate_sync("これはテストです。")
print(result.get("translatedText", "[Translation failed]"))


