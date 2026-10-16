# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
from genlayer import *


class Probe2(gl.Contract):
    res: str

    def __init__(self):
        self.res = ""

    @gl.public.view
    def get_res(self) -> str:
        return self.res

    @gl.public.write
    def test_spawn_in_validator(self, url: str) -> None:
        def leader() -> str:
            r = gl.nondet.web.render(url, mode="text")
            return "LEN:" + str(len(str(r)))

        def validator(leaders_res: gl.vm.Result) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False

            def val_fetch() -> int:
                r = gl.nondet.web.render(url, mode="text")
                return len(str(r))

            sand_res = gl.vm.spawn_sandbox(val_fetch)
            if not isinstance(sand_res, gl.vm.Return):
                return False

            val_len = sand_res.calldata
            # agree if lengths are within 10%
            leader_len = int(str(leaders_res.calldata).split(":")[1])
            return abs(val_len - leader_len) < 500

        res = gl.vm.run_nondet_unsafe(leader, validator)
        self.res = str(res)

    @gl.public.write
    def test_validator_prompt(self, test_msg: str) -> None:
        def leader() -> str:
            r = gl.nondet.exec_prompt("Echo strictly JSON {\"echo\": \"" + str(test_msg) + "\"}", response_format="json")
            return "LEADER:" + str(r)

        def validator(leaders_res: gl.vm.Result) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False

            def val_call() -> str:
                return gl.nondet.exec_prompt("Echo strictly JSON {\"echo\": \"" + str(test_msg) + "\"}", response_format="json")

            sand_res = gl.vm.spawn_sandbox(val_call)
            if not isinstance(sand_res, gl.vm.Return):
                return False

            val_res = str(sand_res.calldata)
            return len(val_res) > 0

        res = gl.vm.run_nondet_unsafe(leader, validator)
        self.res = str(res)
