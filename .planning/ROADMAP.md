# Roadmap — LegacyGraph-MCP

Milestone-based plan for the evolution of LegacyGraph-MCP.

## Milestone 1: Project Baseline (v0.3.0) — COMPLETED
- [x] Accurate AST parsing (tree-sitter).
- [x] NetworkX graph model.
- [x] Dual-mode (Local/Cloud).
- [x] JSON caching.


## Milestone 2: Portability & Cloud Shift (v0.4.0) — TARGET
Shift from Render to Hugging Face Spaces and implement full Docker support.

- [x] **Phase 1: Foundation for Containerization**
    - [x] Create a multi-stage `Dockerfile`.
    - [x] Add `.dockerignore`.
    - [x] Verification: Handed over to USER for local terminal validation.
- [ ] **Phase 2: Hugging Face Spaces Integration**
    - [ ] Update `README.md` with Space metadata (YAML header).
    - [ ] Configure port mappings and environment variable defaults.
    - [ ] Verification: Deployment to a test HF Space.
- [ ] **Phase 3: Persistent Storage & Cleanup**
    - Address `.legacygraph.json` persistence in containers.
    - Clean up Render-specific legacy code if necessary.
- [ ] **Phase 4: Final Verification & Documentation**
    - Refresh `PROJECT_MANUAL.md` with Docker instructions.
    - Run E2E verifier in container.

## Milestone 3: Advanced Analysis (v0.5.0) — FUTURE
- [ ] Support for C++20 modules and concepts.
- [ ] Real-time incremental graph updates.
- [ ] IDE Visualizer improvements.
