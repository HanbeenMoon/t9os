# ADR-024: WSL Ubuntu as Single CLI Environment

- Date: 2026-03-10
- Status: Accepted
- Decision: All CLI work (cc, cx, gm, git, scripts) runs in WSL Ubuntu. PowerShell is excluded from all CLI operations.
- Rationale: Dual-environment operation creates path confusion, encoding issues, and toolchain fragmentation. Single environment eliminates an entire class of bugs.
- Outcome: All SSH keys, env vars, aliases configured in WSL

## Simondon Mapping
Concretization — reducing environmental heterogeneity increases internal coherence of the technical system.
