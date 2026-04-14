# Bedingte Imports: qa_generator und dataset_builder benötigen httpx/tiktoken,
# die im Docker-Web-Container nicht installiert sind.
try:
    from .qa_generator import QAGenerator, QAPair
    from .dataset_builder import DatasetBuilder
    __all__ = ["QAGenerator", "QAPair", "DatasetBuilder"]
except ImportError:
    __all__ = []
