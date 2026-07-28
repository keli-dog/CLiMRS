'''
    This is a module for storing the API configuration.
    Usually it is written with the URL and the API key in pairs.
'''

# NOTE: Agent 会再拼 /v1/chat/completions，这里不要带 /v1
# API key: set locally or via LLM/llm_utils/args.local.py (gitignored)
API_URL = "https://api.minimaxi.com"
API_KEY_CLIMRS = ""

# oracle_planner / LLM.py 会从 llm_module 再导出这些名字，必须存在
API_URL_R17B = API_URL
API_KEY_R17B = API_KEY_CLIMRS

MODEL_SELECTION = "MiniMax-M3"
