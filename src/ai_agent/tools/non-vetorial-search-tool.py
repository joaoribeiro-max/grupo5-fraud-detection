from rank_bm25 import BM25Okapi

Base = [
    "o gato pulou na cerca e ela quebrou",
    "o mundo via acabar por causa de um papaguaio",
    "zaaaaaaaaawuaaaardooooooooooooooo"
]

def non_vetorial_search_tool(pergunta:str):

    token_document = [doc.lower().split(" ") for doc in Base]
    bm25 = BM25Okapi(token_document)

    token_query = pergunta.lower().split(" ") 

    top_base = bm25.get_top_n(token_query,Base,n = 1)
    print(top_base)