#!/bin/zsh
cd -- "${0:A:h}" || exit 1
print "RoadAware: Sign in to Claude using your own account."
claude auth login
login_result=$?
if (( login_result == 0 )); then
  python3 tools/ai_team.py note "Claude: เข้าสู่ระบบแล้ว; เริ่มทดสอบการเชื่อมต่อ"
  python3 tools/ai_team.py run workflow/tasks/000-connection-check.md
  check_result=$?
  if (( check_result == 0 )); then
    print "Connection test finished. Codex still needs to review the report."
  else
    print "Connection test failed. Ask Codex to inspect the latest run."
  fi
else
  python3 tools/ai_team.py note "Claude: การเข้าสู่ระบบยังไม่สำเร็จ"
fi
print "Press Enter to close this window."
read
