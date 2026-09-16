# RoadAware Frontend

หน้าเริ่มต้น RoadAware พัฒนาด้วย React และ JavaScript (.jsx / .js) บน Vite

## เริ่มใช้งาน

```bash
npm install
npm run dev
```

## ตรวจสอบโปรเจกต์

```bash
npm run lint
npm run build
```

## โครงสร้าง

```text
src/
├── components/
│   ├── common/        # Button, Icon, Brand ใช้ร่วมกัน
│   └── layout/        # Header, Footer และสไตล์โครงหน้า
├── features/
│   └── home/
│       ├── components/ # Hero, แผนที่จำลอง, การ์ดบริการ, ขั้นตอนใช้งาน
│       ├── data/       # ข้อความและตำแหน่งหมุดตัวอย่าง
│       └── styles/     # สไตล์แยกตามส่วนของหน้าแรก
├── pages/             # ประกอบแต่ละหน้าเข้าด้วยกัน
├── styles/            # ค่าสีกลางและสไตล์พื้นฐาน
├── App.jsx
├── index.css
└── main.jsx
```

## ขอบเขตปัจจุบัน

- หน้าแรกแบบแสดงผลเท่านั้น ปุ่มยังไม่มีการนำทางหรือเชื่อมต่อระบบ
- แผนที่ SVG เป็นภาพจำลอง ไม่ใช่ภูมิศาสตร์จริงหรือข้อมูลอุบัติเหตุจริง
- รองรับมือถือ แท็บเล็ต และเดสก์ท็อปด้วย CSS responsive
- ฟอนต์ Noto Sans Thai และ Plus Jakarta Sans โหลดจาก Google Fonts โดยมีฟอนต์ระบบสำรอง
- ยังไม่เชื่อม backend, บริการแผนที่ หรือ Machine Learning
