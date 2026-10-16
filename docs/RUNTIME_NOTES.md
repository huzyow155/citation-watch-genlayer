# Runtime Notes and SDK Investigation

## Network Context
- Network: GenLayer Studionet (Preview)
- Chain ID: 61999
- RPC Endpoint: https://studio.genlayer.com/api
- Pinned SDK Dependency: `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`
- Compiler Version: `v0.2.16`

## Pinned SDK API Signatures & File Locations

All APIs below were verified directly by reading the extracted py-genlayer library source in the local GenVM package cache:

1. `gl.eq_principle.strict_eq(fn)`
   - Location: `genlayer/gl/eq_principle.py`, lines 19-39
   - Signature:
     ```python
     def strict_eq[T: calldata.Decoded](fn: typing.Callable[[], T]) -> Lazy[T]:
     ```
   - Mechanism: Delegates to `vm.run_nondet_unsafe.lazy(fn, validator_fn)`. The validator node spawns a sandbox `my_res = vm.spawn_sandbox(fn)` and strictly evaluates `my_res == leaders_res`.

2. `gl.eq_principle.prompt_comparative(fn, principle)`
   - Location: `genlayer/gl/eq_principle.py`, lines 45-92
   - Signature:
     ```python
     def prompt_comparative[T: calldata.Decoded](fn: typing.Callable[[], T], principle: str) -> Lazy[T]:
     ```
   - Mechanism: Delegates to `vm.run_nondet.lazy(fn, validator_fn)`. The validator node evaluates `my_res = fn()`, checks that `leaders_res` is `vm.Return`, and invokes `ExecPromptTemplate` with `EqComparative` to evaluate equivalence against the principle.

3. `gl.eq_principle.prompt_non_comparative(fn, *, task, criteria)`
   - Location: `genlayer/gl/eq_principle.py`, lines 95-153
   - Signature:
     ```python
     def prompt_non_comparative(fn: typing.Callable[[], str], *, task: str, criteria: str) -> Lazy[str]:
     ```

4. `gl.vm.run_nondet(leader_fn, validator_fn, /, *, compare_user_errors=..., compare_vm_errors=...)`
   - Location: `genlayer/gl/vm.py`, lines 191-240
   - Signature:
     ```python
     def run_nondet[T: calldata.Decoded](
         leader_fn: typing.Callable[[], T],
         validator_fn: typing.Callable[[Result[T]], bool],
         /,
         *,
         compare_user_errors: typing.Callable[[UserError, UserError], bool] = ...,
         compare_vm_errors: typing.Callable[[VMError, VMError], bool] = ...,
     ) -> Lazy[T]:
     ```

5. `gl.vm.run_nondet_unsafe(leader_fn, validator_fn, /)`
   - Location: `genlayer/gl/vm.py`, lines 142-189
   - Signature:
     ```python
     def run_nondet_unsafe[T: calldata.Decoded](
         leader_fn: typing.Callable[[], T],
         validator_fn: typing.Callable[[Result], bool],
         /,
     ) -> Lazy[T]:
     ```

6. `gl.nondet.web.render(url, *, mode='text', wait_after_loaded=...)`
   - Location: `genlayer/gl/nondet/web.py`, lines 126-160
   - Signature:
     ```python
     def render(
         url: str,
         *,
         mode: typing.Literal['html', 'text', 'screenshot'] = 'text',
         wait_after_loaded: str | None = None,
     ) -> Lazy[str | Image]:
     ```
   - Limitation: Does not return the final URL after HTTP/HTML redirects. If a redirect occurs, the contract cannot observe the redirected destination URL.

7. `gl.nondet.web.get(url, *, headers={})`
   - Location: `genlayer/gl/nondet/web.py`, lines 41-48
   - Signature:
     ```python
     def get(url: str, *, headers: dict[str, str | bytes] = {}) -> Lazy[Response]:
     ```
   - Return struct: `Response(status: int, headers: dict[str, bytes], body: bytes | None)`.

8. `gl.nondet.exec_prompt(prompt, **config)`
   - Location: `genlayer/gl/nondet/__init__.py`, lines 74-106
   - Signature:
     ```python
     def exec_prompt(prompt: str, **config: typing.Unpack[ExecPromptKwArgs]) -> Lazy[str | dict]:
     ```

9. Cross-contract call API:
   - `gl.get_contract_at(address: Address)`
   - Location: `genlayer/gl/genvm_contracts.py`, lines 202-220
   - Usage: `gl.get_contract_at(Address(addr_str)).view().get_status(citation_id)`

## Studionet Probe Benchmark Findings

On-chain Probe deployment and write calls executed on GenLayer Studionet (Preview):
- Probe contract address: `0x2eeF70885ff485D248A682443b4399A8A093F346`
- Deploy transaction: `0x493cb3f124f947f8ee32801082c2d2fe7f318af3dea4a063a0a69d637f386b3f` (duration: 6.6s, status: `ACCEPTED`, consensus: `MAJORITY_AGREE`, votes: 3 agree / 5 nodes).

Empirical execution results:
1. `test_strict_eq`:
   - Tx hash: `0x94c7123ae698a80294bedc991f2fa8db0a40e2d07d41fac02ad394d73e2cfadc`
   - Consensus outcome: `ACCEPTED`, `MAJORITY_AGREE` (3 agree / 5 total validators: 3 voted agree, 2 idle).
   - Execution duration: 8.7s.
   - Result: `MATERIAL|e1:SAME|e2:CHANGED`.

2. `test_comparative`:
   - Tx hash: `0x78d3dec0fd5ac7693d17b06f05c3180c2655405905562301050b9867c6b3249c`
   - Consensus outcome: `ACCEPTED`, `MAJORITY_AGREE` (3 agree / 5 total validators: 3 voted agree, 2 idle).
   - Execution duration: 8.5s.
   - Result: `MATERIAL|e1:SAME|e2:CHANGED`.

3. Wikipedia Revision Permalink Fetch (`oldid=1380390650`):
   - Tx hash: `0x3dd0f7c030d98ac3a1548c429609353c96caf6ef2dc17a5911dd8827979254c2`
   - Consensus outcome: `ACCEPTED`, `MAJORITY_AGREE` (3 agree / 5 total validators).
   - Execution duration: 35.2s.
   - `render_len`: 119,843 text characters.
   - `get_status`: 200, `get_len`: 1,326,194 raw HTML bytes.

4. Wikipedia Live Page Fetch (`https://en.wikipedia.org/wiki/Alan_Turing`):
   - Tx hash: `0x35eaf10f4a755b32d35a002448a0edf8f2c8e31e5a89fe632f8a19bc81fed050`
   - Consensus outcome: `ACCEPTED`, `MAJORITY_AGREE` (3 agree / 5 total validators).
   - Execution duration: 18.4s.
   - `render_len`: 119,544 text characters.
   - `get_status`: 200, `get_len`: 1,322,812 raw HTML bytes.

### Consensus Architecture Decision
- For **registration**: Deterministic fetch and normalization produces an exact fingerprint. Consensus value is `"OK|" + baseline_text_sha256`. Since revision permalinks are immutable, validators reproduce the identical sha256 fingerprint. We use `strict_eq` (or deterministic comparative) on this canonical string.
- For **auditing**: All validators independently fetch the target page, run the deterministic verbatim check layer, extract relevant passage windows by lexical overlap, invoke model classification only for non-verbatim elements, and construct a compact canonical consensus string:
  `"{CLASS}|{target_text_sha256_or_NONE}|e1:{STATUS}:{PASSAGE_ID}|..."`
- Comparing canonical strings via `strict_eq` provides pure deterministic agreement when all validators fetch identical page contents (revisions). When comparative principle is used as a fallback or for prompt comparison, the benchmark proves both execute reliably with 3 of 5 validator agreement on Studionet.
