# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
import hashlib
from genlayer import *


class Probe(gl.Contract):
    last_probe_result: str

    def __init__(self):
        self.last_probe_result = "{}"

    @gl.public.view
    def get_result(self) -> str:
        return self.last_probe_result

    @gl.public.write
    def test_strict_eq(self, canonical_str: str) -> None:
        def compute() -> str:
            return str(canonical_str)

        res = gl.eq_principle.strict_eq(compute)
        self.last_probe_result = str(res)

    @gl.public.write
    def test_comparative(self, canonical_str: str) -> None:
        def compute() -> str:
            return str(canonical_str)

        res = gl.eq_principle.prompt_comparative(
            compute,
            "Both answers agree on the canonical string."
        )
        self.last_probe_result = str(res)

    @gl.public.write
    def test_run_nondet_unsafe(self, val: str) -> None:
        def leader() -> str:
            return "LEADER|" + str(val)

        def validator(leaders_res: gl.vm.Result) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            data = str(leaders_res.calldata)
            return data.startswith("LEADER|")

        res = gl.vm.run_nondet_unsafe(leader, validator)
        self.last_probe_result = str(res)

    @gl.public.write
    def probe_fetch(self, url: str) -> None:
        def fetch_eval() -> str:
            render_text = ""
            render_err = ""
            try:
                r = gl.nondet.web.render(url, mode="text")
                render_text = str(r) if r is not None else ""
            except Exception as e:
                render_err = str(e)

            get_text = ""
            get_err = ""
            get_status = -1
            try:
                resp = gl.nondet.web.get(url)
                get_status = int(resp.status)
                b = resp.body
                if b is not None:
                    get_text = b.decode("utf-8", errors="replace") if isinstance(b, (bytes, bytearray)) else str(b)
            except Exception as e:
                get_err = str(e)

            res = {
                "url": url,
                "render_len": len(render_text),
                "render_sha256": hashlib.sha256(render_text.encode("utf-8")).hexdigest() if render_text else "",
                "render_err": render_err,
                "get_status": get_status,
                "get_len": len(get_text),
                "get_sha256": hashlib.sha256(get_text.encode("utf-8")).hexdigest() if get_text else "",
                "get_err": get_err,
            }
            return json.dumps(res)

        res = gl.eq_principle.prompt_comparative(
            fetch_eval,
            "Both answers report valid fetch statistics for the requested URL."
        )
        self.last_probe_result = str(res)
