#!/bin/bash
# RoadAware on your phone (prepared by Claude). Double-click in Finder.
# Needs "Start API National" (and, for the Gemini voice, "Start Voice") running too. Phone and Mac on the same Wi-Fi.
cd "$(dirname "$0")/frontend" || exit 1
[ -d node_modules/@vitejs/plugin-basic-ssl ] || npm install || { echo "npm install failed"; read -r; exit 1; }
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
echo ""
echo "=============================================================="
echo "  เปิดในมือถือ (Wi-Fi เดียวกับ Mac):   https://${IP:-<IP ของ Mac>}:5174/"
echo "  ถ้าขึ้นว่า 'ไม่ปลอดภัย / Not private' ให้กด ขั้นสูง → ดำเนินการต่อ"
echo "  (ใบรับรองทำขึ้นในเครื่องนี้เอง ใช้ทดสอบเท่านั้น)"
echo "  ถ้า Mac ถามว่าให้ node รับการเชื่อมต่อไหม ให้กด อนุญาต (Allow)"
echo "  ปิด: กด Ctrl+C หรือปิดหน้าต่างนี้"
echo "=============================================================="
echo ""
npm run dev:phone
