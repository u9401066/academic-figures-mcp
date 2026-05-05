# Skills Audit (Cline)

Validate that all project skills are discoverable and correctly formatted for Cline.

Note: Skills are an experimental feature. Enable it in Cline Settings → Features → Enable Skills.

<execute_command>
<command>python -c "from pathlib import Path; missing=[p for p in Path('.cline/skills').iterdir() if p.is_dir() and not (p/'SKILL.md').is_file()]; assert not missing, missing; print('Cline skills ok')"</command>
</execute_command>

If it fails, stop and report the issues.
