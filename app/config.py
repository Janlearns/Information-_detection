"""Server-side model settings; .env is loaded by app.__init__."""
import os


MODEL_ID = os.getenv('MODEL_ID', '').strip() or 'MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli'
# False disables implicit use of a cached login for the default public model.
# Never include this value in API responses, logs, or frontend configuration.
MODEL_TOKEN = os.getenv('HF_TOKEN', '').strip() or False
