サーバー立ち上げ
`uvicorn main:app --reload`

- uvicorn サーバー
- main:app main.py で作成された app オブジェクト
- --reload 立ち上げ後一旦リロードする

alembic revision --autogenerate -m "create todo table"
