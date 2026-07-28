#!/usr/bin/env python3
"""在 CLiMRS 根目录执行: python scripts/patch_minimax_llm.py
修复 MiniMax-M3: strip <think>、放宽 YES I CAN、按 [skill] 解析动作。
可重复执行（幂等）。
"""
from pathlib import Path
import re

ROOT = Path(".").resolve()
mod_path = ROOT / "LLM/llm_utils/llm_module.py"
fa_path = ROOT / "LLM/dev_revision/llm_agents/feedback_agent.py"

if not mod_path.exists() or not fa_path.exists():
    raise SystemExit(f"请在 CLiMRS 根目录运行。找不到:\n  {mod_path}\n  {fa_path}")

# ========== 1) llm_module.py ==========
LLM_MODULE = r'''import requests
import json
import re
import sys
from .args import *

MODEL_DEFAULT = "gpt-4o-2024-11-20"


def strip_think_tags(text):
    """Remove MiniMax / reasoning <think>...</think> blocks."""
    if not text:
        return text
    text = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE)
    return text.strip()


class Agent:
    '''
        This is a class for querying the LLM model as an agent.
        :param str model: the model name to use.
        :param str api_url: str, the API URL to use for the model.
        :param str api_key: the API key to use for authentication.
    '''
    def __init__(
            self,
            model=None,
            api_url=None,
            api_key=None,

        ):

        self.model_name = model
        self.api_url = api_url
        self.api_key = api_key

        self.headers  = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'User-Agent':'Apifox/1.0.0(https://apifox.com)',
            'Content-Type': 'application/json'
        }

        self.api_url_completions = f"{self.api_url}/v1/chat/completions"
        pass

    def respond_once_raw(
            self,
            messages=None,
            max_tokens=None,
            temperature=None,
        ):

        assert messages is not None, "Messages cannot be None!"

        payload_dict = {
            "model": self.model_name,
            "messages": messages
        }

        if max_tokens is not None:
            payload_dict["max_tokens"] = max_tokens
        if temperature is not None:
            payload_dict["temperature"] = temperature

        url = self.api_url_completions
        payload = json.dumps(payload_dict)
        response = requests.post(url, headers=self.headers, data=payload)
        response = response.json()
        try:
            for ch in response.get("choices", []):
                msg = ch.get("message") or {}
                if "content" in msg and isinstance(msg["content"], str):
                    msg["content"] = strip_think_tags(msg["content"])
        except Exception:
            pass
        return response

    def respond_once_all_args(
            self,
            messages=None,
            *args,
            **kwargs
        ):

        assert messages is not None, "Messages cannot be None!"

        payload_dict = {
            "model": self.model_name,
            "messages": messages
        }

        payload_dict.update(kwargs)

        url = self.api_url_completions
        payload = json.dumps(payload_dict)
        response = requests.post(url, headers=self.headers, data=payload)

        if response.status_code != 200:
            print(f"Request failed with status code {response.status_code}")
            print(response.text)
            response.raise_for_status()


        if response.text.strip():
            try:
                json_data = response.json()
            except json.JSONDecodeError as e:
                print("Failed to parse JSON:", e)
                print("Response text:", response.text)
        else:
            print("Empty response body")

        response = response.json()
        # Strip think tags in-place so oracle_planner / feedback_agent all benefit
        try:
            for ch in response.get("choices", []):
                msg = ch.get("message") or {}
                if "content" in msg and isinstance(msg["content"], str):
                    msg["content"] = strip_think_tags(msg["content"])
        except Exception:
            pass

        return response

    def respond_once(
            self,
            question=None,
        ):
        messages = self.prompt_from_question(question)
        return self.respond_once_raw(messages)

    def prompt_from_question(
            self,
            question
        ):
        messages = [
            {"role": "user", "content": question}
        ]
        return messages


    def usage_from_response(
            self,
            response
        ):
        usage = response.get("usage", {})
        return usage

    def answer_from_response(
            self,
            response
        ):
        answer = response.get("choices", [])[0].get("message", {}).get("content", "")
        return strip_think_tags(answer)


if __name__ == "__main__":
    agent = Agent(
        model=MODEL_DEFAULT,
        api_url=API_URL,
        api_key=API_KEY_CLIMRS,
    )
'''
mod_path.write_text(LLM_MODULE)
print("OK wrote", mod_path)

# ========== 2) feedback_agent.py ==========
t = fa_path.read_text()

HELPERS = '''from llm_utils.llm_module import Agent, API_KEY_R17B, API_KEY_CLIMRS, API_URL, API_URL_R17B, MODEL_SELECTION, strip_think_tags


def _normalize_agent_cot(output):
\t"""Strip <think> and ensure MiniMax answers can pass the YES I CAN gate."""
\toutput = strip_think_tags(output or "")
\tupper = output.upper().strip()
\tif upper.startswith("YES I CAN") or upper.startswith("SORRY I CANNOT"):
\t\treturn output
\tskill_hints = ("[MOVE]", "[PUSH]", "[WAIT]", "[WALK]", "[CARRY]", "[CHECK]", "[PICK]", "[OBSERVE]", "OPTION ")
\tif any(s in upper for s in skill_hints) or not upper:
\t\treturn ("YES I CAN. " + output).strip()
\treturn output


def _decision_prefix(output):
\toutput = _normalize_agent_cot(output)
\tupper = output.upper().lstrip()
\tif upper.startswith("YES I CAN"):
\t\treturn "YES I CAN", output
\tif upper.startswith("SORRY I CANNOT"):
\t\treturn "SORRY I CANNOT", output
\tfirst = upper.split(".")[0].strip() if upper else ""
\treturn first, output


def _parse_available_action(available_actions, text):
\t"""Match LLM text to an available action; tolerant of MiniMax / underscore issues."""
\ttext = strip_think_tags(text or "")
\ttext_space = text.replace("_", " ")
\tfor action in available_actions:
\t\tif action in text or action.replace("_", " ") in text_space:
\t\t\treturn action
\ttext_l = text.lower()
\tskill_hits = []
\tfor action in available_actions:
\t\tm = re.match(r'(\\[[^\\]]+\\])', action.strip(), re.I)
\t\tif m and m.group(1).lower() in text_l:
\t\t\tskill_hits.append(action)
\tif len(skill_hits) == 1:
\t\treturn skill_hits[0]
\tif len(skill_hits) > 1:
\t\tfor action in skill_hits:
\t\t\tids = re.findall(r'\\((\\d+)\\)', action)
\t\t\tif ids and ids[0] in text:
\t\t\t\treturn action
\t\treturn skill_hits[0]
\tfor i, action in enumerate(available_actions):
\t\toption = chr(ord('A') + i)
\t\ttokens = text_space.split(' ')
\t\tif any(opt in text for opt in [f"option {option}", f"Option {option}", f"({option})"]) or f"{option}." in tokens or f"{option}," in tokens:
\t\t\treturn action
\treturn None


'''

# normalize import line then inject helpers once
t = re.sub(
    r"from llm_utils\.llm_module import[^\n]+\n",
    "from llm_utils.llm_module import Agent, API_KEY_R17B, API_KEY_CLIMRS, API_URL, API_URL_R17B, MODEL_SELECTION, strip_think_tags\n",
    t,
    count=1,
)
if "def _decision_prefix" not in t:
    t = t.replace(
        "from llm_utils.llm_module import Agent, API_KEY_R17B, API_KEY_CLIMRS, API_URL, API_URL_R17B, MODEL_SELECTION, strip_think_tags\n",
        HELPERS,
        1,
    )
    print("OK injected helpers")
else:
    print("OK helpers already present")

# tab-indented first_sentence block
old_tab = '''\t\tsentences = output.split(".")
\t\tfirst_sentence = sentences[0].upper()
\t\tprint("#" *20)
\t\tprint("the first sentence is", first_sentence)
\t\tprint("#" *20)'''
new_tab = '''\t\tfirst_sentence, output = _decision_prefix(output)
\t\tprint("#" *20)
\t\tprint("the first sentence is", first_sentence)
\t\tprint("#" *20)
\t\tmessage = ""'''
if old_tab in t:
    t = t.replace(old_tab, new_tab)
    print("OK patched tab first_sentence")

old_sp = '''        sentences = output.split(".")
        first_sentence = sentences[0].upper()
        print("#" * 20)
        print("the first sentence is", first_sentence)
        print("#" * 20)'''
new_sp = '''        first_sentence, output = _decision_prefix(output)
        print("#" * 20)
        print("the first sentence is", first_sentence)
        print("#" * 20)'''
if old_sp in t:
    t = t.replace(old_sp, new_sp)
    print("OK patched space first_sentence")

# second-round sentence check (tab)
t = t.replace(
    '''\t\t\tsentences = output.split(".")
\t\t\tfirst_sentence = sentences[0].upper()
\t\t\tif first_sentence != "SORRY I CANNOT":''',
    '''\t\t\tfirst_sentence2, output = _decision_prefix(output)
\t\t\tif first_sentence2 != "SORRY I CANNOT":''',
)
t = t.replace(
    '''            sentences = output.split(".")
            first_sentence = sentences[0].upper()
            if first_sentence != "SORRY I CANNOT":''',
    '''            first_sentence2, output = _decision_prefix(output)
            if first_sentence2 != "SORRY I CANNOT":''',
)

# parse_answer -> use helper (tab version)
t = re.sub(
    r"\tdef parse_answer\(self, available_actions, text\):\n"
    r"\t\t\n"
    r"\t\ttext = text\.replace\([\s\S]*?"
    r"\t\treturn None\n",
    "\tdef parse_answer(self, available_actions, text):\n"
    "\t\t\n"
    "\t\tplan = _parse_available_action(available_actions, text)\n"
    "\t\tif plan is not None:\n"
    "\t\t\treturn plan\n"
    "\t\tself.write_log_to_file('\\nThe first/second action parsing failed!!!')\n"
    "\t\tprint(\"WARNING! No available action parsed!!! Output plan NONE!\\n\")\n"
    "\t\treturn None\n",
    t,
    count=1,
)

# space parse_answer
t = re.sub(
    r'    def parse_answer\(self, available_actions, text\):\n'
    r'        """Parse the LLM\'s answer to get the chosen action"""\n'
    r'        text = text\.replace\([\s\S]*?'
    r'        return None\n',
    '    def parse_answer(self, available_actions, text):\n'
    '        """Parse the LLM\'s answer to get the chosen action"""\n'
    '        plan = _parse_available_action(available_actions, text)\n'
    '        if plan is not None:\n'
    '            return plan\n'
    '        self.write_log_to_file(\'\\nThe first/second action parsing failed!!!\')\n'
    '        print("WARNING! No available action parsed!!! Output plan NONE!\\n")\n'
    '        return None\n',
    t,
    count=1,
)

# fallback: parse from instruction
if "chat_agent_info.get('instruction'" not in t:
    t = t.replace(
        "\t\t\t\tplan = self.parse_answer(available_plans_list, output)\n\t\t\t\tif plan is None:\n\t\t\t\t\tplan_str = 'no plan'",
        "\t\t\t\tplan = self.parse_answer(available_plans_list, output)\n"
        "\t\t\t\tif plan is None:\n"
        "\t\t\t\t\tplan = self.parse_answer(available_plans_list, chat_agent_info.get('instruction', ''))\n"
        "\t\t\t\tif plan is None:\n"
        "\t\t\t\t\tplan_str = 'no plan'",
    )
    t = t.replace(
        "                plan = self.parse_answer(available_plans_list, output)\n"
        "                plan_str = plan if plan is not None else 'no plan'",
        "                plan = self.parse_answer(available_plans_list, output)\n"
        "                if plan is None:\n"
        "                    plan = self.parse_answer(available_plans_list, chat_agent_info.get('instruction', ''))\n"
        "                plan_str = plan if plan is not None else 'no plan'",
    )
    print("OK instruction fallback")

fa_path.write_text(t)
print("OK wrote", fa_path)
print("DONE")
