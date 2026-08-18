"""Presença deste arquivo faz o pytest pôr `corretor/` no sys.path.

Sem ele, `tests/test_schema.py` não consegue `import schema`, porque o pytest
insere o diretório do próprio teste no path, não o diretório pai.
"""
