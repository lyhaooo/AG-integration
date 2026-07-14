# -*- coding: utf-8 -*-
"""统一 LLM 接口：根据配置选择远程 API 或本地部署。"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from .api_general import InterfaceAPI
from .api_local_llm import InterfaceLocalLLM
import time


def make_llm_generate_fn(interface_llm, max_workers: int = None):
    """
    根据任意具备 get_response(prompt) 的 LLM 实例，生成 llm_generate_fn(prompt, n)。
    并行对同一 prompt 调用 n 次 get_response，返回 n 条回复（顺序与请求一致）。
    """
    def llm_generate_fn(prompt: str, n: int):
        workers = max_workers if max_workers is not None else min(32, n + 4)
        out = [None] * n
        # print("time:", time.time())
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futs = {executor.submit(interface_llm.get_response, prompt): i for i in range(n)}
            for fut in as_completed(futs):
                idx = futs[fut]
                try:
                    res = fut.result()
                    out[idx] = res if res is not None and res.strip() else ""
                except Exception:
                    out[idx] = ""
        # print("time:", time.time())
        return out
    return llm_generate_fn


class InterfaceLLM:
    def __init__(
        self,
        api_endpoint,
        api_key,
        model_LLM,
        llm_use_local,
        llm_local_url,
        debug_mode=False,
        max_workers=4,
    ):
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.model_LLM = model_LLM
        self.debug_mode = debug_mode
        self.llm_use_local = llm_use_local
        self.llm_local_url = llm_local_url
        self._max_workers = max_workers

        print("- check LLM API")

        if self.llm_use_local:
            print("local llm deployment is used ...")
            if self.llm_local_url is None or self.llm_local_url == "xxx":
                print(">> Stop with empty url for local llm !")
                exit(1)
            self.interface_llm = InterfaceLocalLLM(self.llm_local_url)
        else:
            print("remote llm api is used ...")
            if (
                self.api_key is None
                or self.api_endpoint is None
                or self.api_key == "xxx"
                or self.api_endpoint == "xxx"
            ):
                print(
                    ">> Stop with wrong API setting: Set api_endpoint (e.g., api.chat...) and api_key (e.g., kx-...) !"
                )
                exit(1)
            self.interface_llm = InterfaceAPI(
                self.api_endpoint,
                self.api_key,
                self.model_LLM,
                self.debug_mode,
            )

        res = self.interface_llm.get_response("1+1=?")
        if res is None:
            print(
                ">> Error in LLM API, wrong endpoint, key, model or local deployment!"
            )
            exit(1)
        # 尝试输出服务端 API 的限流/配额（若服务端在响应头中提供）
        try:
            hdrs = getattr(self.interface_llm, "last_response_headers", None)
            if isinstance(hdrs, dict) and hdrs:
                keys = sorted(hdrs.keys(), key=lambda x: x.lower())
                rate_keys = [
                    k for k in keys
                    if "ratelimit" in k.lower()
                    or "rate-limit" in k.lower()
                    or k.lower() in ("retry-after", "x-request-id")
                ]
                # if rate_keys:
                #     print("[LLM] 服务端返回的限流/配额相关响应头：")
                #     for k in rate_keys:
                #         print(f"  - {k}: {hdrs.get(k)}")
                # else:
                #     print("[LLM] 服务端未返回可识别的限流/配额响应头（x-ratelimit-*/retry-after 等）。")
            else:
                print("[LLM] 当前接口未暴露响应头，无法读取服务端限流/配额上限。")
        except Exception:
            print("[LLM] 读取服务端限流/配额信息失败（响应头不可用）。")

    def get_response(self, prompt_content: str):
        return self.interface_llm.get_response(prompt_content)

    def get_responses(self, prompt: str, n: int):
        """并行请求 n 次 get_response(prompt)，返回 n 条回复列表。"""
        return make_llm_generate_fn(self, self._max_workers)(prompt, n)
