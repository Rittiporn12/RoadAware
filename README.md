<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:020617,45:0f172a,75:0b6e69,100:334155&height=180&section=header&text=RoadAware&fontSize=46&fontColor=f8fafc&fontAlignY=38&desc=%E0%B8%A3%E0%B8%B9%E0%B9%89%E0%B8%81%E0%B9%88%E0%B8%AD%E0%B8%99%E0%B8%A7%E0%B9%88%E0%B8%B2%E0%B8%84%E0%B8%A7%E0%B8%A3%E0%B8%A3%E0%B8%B0%E0%B8%A7%E0%B8%B1%E0%B8%87%E0%B8%95%E0%B8%A3%E0%B8%87%E0%B9%84%E0%B8%AB%E0%B8%99%20%E0%B8%81%E0%B9%88%E0%B8%AD%E0%B8%99%E0%B8%AD%E0%B8%AD%E0%B8%81%E0%B9%80%E0%B8%94%E0%B8%B4%E0%B8%99%E0%B8%97%E0%B8%B2%E0%B8%87&descSize=16&descAlignY=58" alt="RoadAware" />

<br />

<img src="./docs/logo.svg" width="110" alt="โลโก้ RoadAware" />

<br />
<br />

<a href="https://github.com/Rittiporn12/RoadAware">
  <img src="https://img.shields.io/badge/GITHUB-Repository-334155?style=for-the-badge&labelColor=020617&color=475569" alt="GitHub" />
</a>

<img src="https://img.shields.io/badge/MODEL-HistGradientBoosting-0b6e69?style=for-the-badge&labelColor=020617" alt="โมเดล" />

<img src="https://img.shields.io/badge/COVERAGE-Thailand%20Highways-1e3a8a?style=for-the-badge&labelColor=020617" alt="พื้นที่ครอบคลุม" />

<br />
<br />

<p>
  <b>RoadAware</b>
</p>

<p>
  เว็บแอปช่วยวางแผนการเดินทาง ที่บอกจุดที่ควรระวังบนเส้นทางทั่วประเทศไทย
</p>

<p>
  เลือกต้นทาง ปลายทาง และเวลาออกเดินทาง ระบบจะชี้ช่วงทางหลวง<br />
  ที่คาดว่าจะเกิดอุบัติเหตุมากที่สุด ในช่วงเวลาที่คุณจะขับผ่าน
</p>

</div>

<hr />

<h2 align="center">เกี่ยวกับโครงงาน</h2>

<p align="center">
  <b>RoadAware</b> เป็นโครงงานระดับมหาวิทยาลัย ที่นำข้อมูลอุบัติเหตุทางถนนแบบเปิดของประเทศไทย มาสรุปเป็นข้อมูลก่อนเดินทางที่อ่านเข้าใจง่าย
</p>

<p align="center">
  ใช้แบบจำลอง Machine Learning (HistGradientBoosting แบบ Poisson) คาดจำนวนอุบัติเหตุที่จะถูกบันทึก<br />
  ของทางหลวงแต่ละช่วง (ช่วงละราว 2 กม.) ตามวันและช่วงเวลา 6 ชั่วโมงที่คุณเดินทาง
</p>

<p align="center">
  หน้าเว็บจะเรียงลำดับช่วงถนนบนเส้นทาง ใส่หมายเลขจุดที่เด่นที่สุด และพูดเตือนล่วงหน้าระหว่างขับได้
</p>

<p align="center">
  <i>ใช้เพื่อการศึกษาและเตรียมตัวก่อนเดินทาง ไม่ใช่ระบบเตือนภัยแบบเรียลไทม์ ระดับที่แสดงเป็นการเปรียบเทียบระหว่างช่วงถนน ไม่ใช่โอกาสเกิดอุบัติเหตุของแต่ละบุคคล</i>
</p>

<hr />

<h2 align="center">ความสามารถ</h2>

<table align="center">
  <tr>
    <th>ความสามารถ</th>
    <th>รายละเอียด</th>
  </tr>
  <tr>
    <td>ครอบคลุมทั่วประเทศ</td>
    <td>ทางหลวงของกรมทางหลวง 26,740 ช่วง ยาวรวมราว 51,900 กม.</td>
  </tr>
  <tr>
    <td>จุดที่ควรระวัง</td>
    <td>หมายเลขเรียงตามลำดับที่จะผ่าน พร้อมเวลาที่คาดว่าจะผ่านแต่ละจุด</td>
  </tr>
  <tr>
    <td>คาดตามเวลาที่เดินทาง</td>
    <td>วันในสัปดาห์ ช่วงเวลา 6 ชั่วโมง ฤดูกาล เทศกาลสงกรานต์และปีใหม่ สภาพอากาศ และปริมาณจราจร</td>
  </tr>
  <tr>
    <td>รายละเอียดแต่ละจุด</td>
    <td>ที่ผ่านมาเกิดเหตุแบบไหนบ่อย สัดส่วนที่เกิดตอนฝนตก และช่วงเวลาที่เกิดบ่อย พร้อมคำแนะนำ</td>
  </tr>
  <tr>
    <td>คำแนะนำอัตโนมัติ</td>
    <td>เส้นทางอื่นที่ใช้เวลาใกล้กันแต่ผ่านช่วงเสี่ยงน้อยกว่า หรือเวลาออกเดินทางที่ดีกว่า</td>
  </tr>
  <tr>
    <td>เทียบทั้งประเทศ</td>
    <td>ดูว่าแต่ละช่วงถนนอยู่ระดับไหนเมื่อเทียบกับทางหลวงทั้งประเทศ (สูงมาก / สูง / ปานกลาง / ต่ำกว่าครึ่งประเทศ)</td>
  </tr>
  <tr>
    <td>โหมดขับ</td>
    <td>ติดตามตำแหน่งด้วย GPS หรือจำลองการขับ พร้อมเสียงเตือนภาษาไทยที่ 2 กม. / 500 ม. / เมื่อเข้าสู่จุด</td>
  </tr>
  <tr>
    <td>รองรับทุกหน้าจอ</td>
    <td>ใช้ได้ทั้งคอมพิวเตอร์และมือถือ</td>
  </tr>
</table>

<hr />

<h2 align="center">ข้อมูลและแบบจำลอง</h2>

<table align="center">
  <tr>
    <th>หัวข้อ</th>
    <th>รายละเอียด</th>
  </tr>
  <tr>
    <td>ข้อมูลอุบัติเหตุ</td>
    <td>ข้อมูลเปิดของกระทรวงคมนาคม ปี 2564–2568 จับคู่กับช่วงถนนได้ 98,207 รายการ</td>
  </tr>
  <tr>
    <td>ข้อมูลถนน</td>
    <td>ข้อมูลเปิดของกรมทางหลวง</td>
  </tr>
  <tr>
    <td>ปัจจัยประกอบ</td>
    <td>ปฏิทินและเทศกาล สภาพอากาศ (Open-Meteo) ปริมาณจราจรเฉลี่ยรายปี (AADT)</td>
  </tr>
  <tr>
    <td>ข้อมูลที่ใช้ฝึก</td>
    <td>ปี 2564–2566 (ตัดข้อมูลที่ 1 ธ.ค. 2566)</td>
  </tr>
  <tr>
    <td>การเลือกแบบจำลอง</td>
    <td>ทดสอบย้อนหลัง 4 รอบในปี 2565–2566 เทียบกับค่าพื้นฐานที่ดีที่สุด ตามเกณฑ์ที่ล็อกไว้ก่อนทดลอง</td>
  </tr>
  <tr>
    <td>การตรวจและทดสอบ</td>
    <td>ตรวจกับปี 2567–2568 และทดสอบกับปี 2569 (ม.ค.–ก.ย. 15,425 รายการ) ที่แบบจำลองไม่เคยเห็น</td>
  </tr>
</table>

<h3 align="center">ผลการประเมิน</h3>

<table align="center">
  <tr>
    <th>การประเมิน</th>
    <th>รายวัน</th>
    <th>ราย 6 ชั่วโมง</th>
  </tr>
  <tr>
    <td>ทดสอบย้อนหลังปี 2565–2566 (ค่าความคลาดเคลื่อนลดลงเทียบค่าพื้นฐาน)</td>
    <td>ลดลง 2.7% · ชนะ 3 จาก 4 รอบ</td>
    <td>ลดลง 10.6% · ชนะ 4 จาก 4 รอบ</td>
  </tr>
  <tr>
    <td>ข้อมูลปี 2569 ที่ไม่เคยเห็น</td>
    <td>ดีกว่า 6.5% · ทุกเดือน</td>
    <td>ดีกว่า 13.5% · ทุกเดือน</td>
  </tr>
  <tr>
    <td>ช่วงสงกรานต์ / ปีใหม่ 2569</td>
    <td>ดีกว่า 24% / 28%</td>
    <td>ดีกว่า 29% / 32%</td>
  </tr>
</table>

<p align="center">
  รายละเอียดและข้อจำกัด: <a href="backend/reports/v4/evaluation_2026_national_summary_th.md">สรุปผลทดสอบปี 2569</a>
</p>

<hr />

<h2 align="center">เทคโนโลยีที่ใช้</h2>

<div align="center">

<table>
  <tr>
    <td align="center">Python</td>
    <td align="center">scikit-learn</td>
    <td align="center">pandas</td>
    <td align="center">Jupyter</td>
    <td align="center">FastAPI</td>
    <td align="center">React</td>
    <td align="center">Vite</td>
    <td align="center">Leaflet</td>
  </tr>
</table>

</div>

<hr />

<h2 align="center">การติดตั้ง</h2>

<p align="center">
  ข้อมูลดิบและไฟล์แบบจำลองมีขนาดใหญ่ จึงไม่ได้เก็บไว้ใน repository นี้<br />
  ขั้นตอนด้านล่างต้องมีข้อมูลอยู่ใน <code>backend/data/</code> และ <code>backend/rerun-*</code> แล้ว
</p>

<h3>1. ดาวน์โหลดโปรเจค</h3>

```bash
git clone https://github.com/Rittiporn12/RoadAware.git
cd RoadAware
```

<h3>2. เปิด API</h3>

```bash
python3.9 -m venv .venv
.venv/bin/pip install -r backend/requirements-api.txt -c backend/constraints-runtime.txt
.venv/bin/python backend/scripts/run_api_server.py --national
```

<p>API จะทำงานที่ <code>http://127.0.0.1:8000</code></p>

<h3>3. เปิดหน้าเว็บ</h3>

```bash
cd frontend
npm install
npm run dev
```

<p>เปิดที่อยู่ที่แสดงใน Terminal</p>

```bash
http://127.0.0.1:5173/
```

<p>
  บน macOS ดับเบิลคลิก <code>Start API National.command</code> และ <code>Start Website.command</code> แทนได้
</p>

<hr />

<h2 align="center">โครงสร้างโปรเจค</h2>

```txt
RoadAware/
├── backend/
│   ├── notebooks/     # ขั้นตอนข้อมูลและ ML (01–25, *_national = ทั่วประเทศ)
│   ├── config/        # ค่าตั้งของแต่ละขั้น
│   ├── api/           # FastAPI ที่หน้าเว็บเรียกใช้
│   ├── scripts/       # ตัวรัน notebook, เปิด API, สร้างเสียงเตือน
│   ├── reports/       # รายงานสรุปและผลประเมิน
│   └── tests/         # ชุดทดสอบ pytest
├── frontend/
│   ├── public/
│   └── src/           # หน้าเว็บ React (แผนที่, สรุปทริป, โหมดขับ)
├── workflow/          # ไฟล์ล็อก hash ที่ API ตรวจก่อนโหลดแบบจำลอง
├── docs/
└── README.md
```

<hr />

<h2 align="center">คำสั่งที่ใช้บ่อย</h2>

<table align="center">
  <tr>
    <th>คำสั่ง</th>
    <th>ใช้ทำอะไร</th>
  </tr>
  <tr>
    <td><code>run_api_server.py --national</code></td>
    <td>เปิด API ด้วยแบบจำลองทั่วประเทศ</td>
  </tr>
  <tr>
    <td><code>npm run dev</code></td>
    <td>เปิดหน้าเว็บสำหรับพัฒนา</td>
  </tr>
  <tr>
    <td><code>npm run dev:phone</code></td>
    <td>เปิดเว็บแบบ HTTPS ใน Wi-Fi เดียวกัน เพื่อทดสอบ GPS บนมือถือ</td>
  </tr>
  <tr>
    <td><code>npm run build</code></td>
    <td>สร้างหน้าเว็บสำหรับใช้งานจริง</td>
  </tr>
  <tr>
    <td><code>pytest backend/tests</code></td>
    <td>รันชุดทดสอบของ backend</td>
  </tr>
  <tr>
    <td><code>tts_proxy.py</code></td>
    <td>เสียงเตือนภาษาไทยจากเครื่อง Mac สำหรับโหมดขับ (ไม่บังคับ)</td>
  </tr>
</table>

<hr />

<h2 align="center">วิธีใช้งาน</h2>

<table align="center">
  <tr>
    <th>ขั้นตอน</th>
    <th>รายละเอียด</th>
  </tr>
  <tr>
    <td>1</td>
    <td>ใส่ต้นทางและปลายทาง หรือเลือกบนแผนที่</td>
  </tr>
  <tr>
    <td>2</td>
    <td>เลือกวันและเวลาออกเดินทาง</td>
  </tr>
  <tr>
    <td>3</td>
    <td>กด <b>ตรวจเส้นทางนี้</b></td>
  </tr>
  <tr>
    <td>4</td>
    <td>ดูจำนวนจุดที่ควรระวัง และแตะแต่ละจุดเพื่อดูรายละเอียด</td>
  </tr>
  <tr>
    <td>5</td>
    <td>ถ้ามีคำแนะนำขึ้นมา เลือกใช้เส้นทางหรือเวลาออกเดินทางที่แนะนำได้</td>
  </tr>
  <tr>
    <td>6</td>
    <td>กด <b>เริ่มเดินทาง</b> เพื่อให้ระบบพูดเตือนระหว่างขับ</td>
  </tr>
</table>

<hr />

<h2 align="center">ข้อมูลและบริการที่นำมาใช้</h2>

<p align="center">
  แผนที่ © OpenStreetMap contributors (ODbL) · ค้นหาสถานที่ Photon (komoot) · คำนวณเส้นทาง OSRM<br />
  ขอบเขตประเทศ geoBoundaries (CC BY 4.0) และ Natural Earth · สภาพอากาศ Open-Meteo<br />
  ข้อมูลอุบัติเหตุ กระทรวงคมนาคม · ข้อมูลทางหลวง กรมทางหลวง
</p>

<hr />

<h2 align="center">ผู้พัฒนา</h2>

<div align="center">

<p>
  <b>ฤทธิพร ผึ่งผาย</b>
</p>

<p>
  นักศึกษาวิทยาการคอมพิวเตอร์<br />
  การพัฒนาซอฟต์แวร์ | การพัฒนาแบบ Full-Stack | AI และระบบอัตโนมัติ | คุณภาพซอฟต์แวร์
</p>

<p>
  <a href="https://github.com/Rittiporn12">
    GitHub
  </a>
  &nbsp;|&nbsp;
  <a href="https://rittiporn12.github.io/portfolio/">
    Portfolio
  </a>
</p>

</div>

<hr />

<div align="center">

<p>
  <b>ขอบคุณที่แวะมาดู RoadAware</b>
</p>

<p>
  ขับขี่ปลอดภัย และระวังเป็นพิเศษที่จุดหมายเลขบนเส้นทาง
</p>

</div>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:334155,45:0b6e69,75:0f172a,100:020617&height=100&section=footer" alt="" />
