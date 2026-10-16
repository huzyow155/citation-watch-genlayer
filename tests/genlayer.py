import json
import collections.abc


class GlVM:
    class UserError(Exception):
        def __init__(self, message=""):
            super().__init__(message)
            self.message = str(message)

        def __str__(self):
            return self.message

        def __repr__(self):
            return f"UserError({self.message!r})"

    class VMError(Exception):
        def __init__(self, message=""):
            super().__init__(message)
            self.message = str(message)

        def __str__(self):
            return self.message

    class Return:
        def __init__(self, calldata):
            self.calldata = calldata

    Result = object

    def spawn_sandbox(self, fn, **kwargs):
        try:
            res = fn()
            return self.Return(calldata=res)
        except self.UserError as e:
            return e
        except Exception as e:
            return self.VMError(str(e))

    def run_nondet_unsafe(self, leader_fn, validator_fn):
        leader_res = leader_fn()
        wrapped = self.Return(calldata=leader_res)
        valid = validator_fn(wrapped)
        if not valid:
            raise self.VMError("validator disagreed")
        return leader_res

    def run_nondet(self, leader_fn, validator_fn, **kwargs):
        return self.run_nondet_unsafe(leader_fn, validator_fn)


class GlPublic:
    @staticmethod
    def view(fn):
        return fn

    @staticmethod
    def write(fn):
        return fn


class GlEqPrinciple:
    @staticmethod
    def strict_eq(fn):
        return fn()

    @staticmethod
    def prompt_comparative(fn, principle=""):
        return fn()

    @staticmethod
    def prompt_non_comparative(fn, *, task="", criteria=""):
        return fn()


class GlWebResponse:
    def __init__(self, status=200, body=b"", headers=None):
        self.status = status
        self.body = body
        self.headers = headers or {}


class GlWeb:
    def __init__(self):
        self.pages = {}
        self.render_handler = None
        self.get_handler = None

    def render(self, url, mode="text", wait_after_loaded=None):
        if self.render_handler:
            return self.render_handler(url, mode)
        if url in self.pages:
            return self.pages[url]
        return ""

    def get(self, url, headers=None):
        if self.get_handler:
            return self.get_handler(url, headers)
        if url in self.pages:
            body = self.pages[url]
            if isinstance(body, str):
                body = body.encode("utf-8")
            return GlWebResponse(status=200, body=body)
        return GlWebResponse(status=404, body=b"Not found")


class GlNondet:
    def __init__(self):
        self.prompt_handler = None
        self.web = GlWeb()

    def exec_prompt(self, p, response_format="text"):
        if self.prompt_handler:
            return self.prompt_handler(p, response_format)
        return "{}"


class GlMessage:
    class SenderAddress:
        as_hex = "0x1111111111111111111111111111111111111111"

        def __str__(self):
            return self.as_hex

    sender_address = SenderAddress()


class Address:
    SIZE = 20

    def __init__(self, val):
        if isinstance(val, str):
            if val.startswith("0x") and len(val) == 42:
                self._as_hex = val
                self._as_bytes = bytes.fromhex(val[2:])
            else:
                self._as_hex = val
                self._as_bytes = val.encode("utf-8")[:20]
        else:
            self._as_bytes = bytes(val)
            self._as_hex = "0x" + self._as_bytes.hex()

    @property
    def as_hex(self):
        return self._as_hex

    @property
    def as_bytes(self):
        return self._as_bytes

    def __str__(self):
        return self._as_hex

    def __repr__(self):
        return f"Address('{self._as_hex}')"


class ContractProxy:
    def __init__(self, target_contract):
        self._target = target_contract

    def view(self):
        return self._target

    def emit(self, **kwargs):
        return self._target


class GlContract:
    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        for base in cls.__mro__:
            for attr_name, attr_type in getattr(base, "__annotations__", {}).items():
                origin = getattr(attr_type, "__origin__", attr_type)
                if origin is dict or "TreeMap" in str(attr_type) or attr_type is dict:
                    setattr(instance, attr_name, {})
        return instance


class GlMock:
    Contract = GlContract
    vm = GlVM()
    public = GlPublic()
    eq_principle = GlEqPrinciple()
    nondet = GlNondet()
    message = GlMessage()
    message_raw = {"datetime": "2026-10-16T12:00:00Z"}
    contracts_registry = {}

    @classmethod
    def get_contract_at(cls, address):
        addr_str = address.as_hex if isinstance(address, Address) else str(address)
        if addr_str in cls.contracts_registry:
            return ContractProxy(cls.contracts_registry[addr_str])
        raise GlVM.UserError(f"contract not found at {addr_str}")


gl = GlMock()
TreeMap = dict
u256 = int
Lazy = object
