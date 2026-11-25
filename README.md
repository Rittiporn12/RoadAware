<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:020617,45:0f172a,75:0b6e69,100:334155&height=180&section=header&text=RoadAware&fontSize=46&fontColor=f8fafc&fontAlignY=38&desc=Know%20where%20to%20take%20care%20before%20you%20drive&descSize=16&descAlignY=58" alt="RoadAware Header" />

<br />

<img src="./docs/logo.svg" width="110" alt="RoadAware Logo" />

<br />
<br />

<a href="https://github.com/Rittiporn12/RoadAware">
  <img src="https://img.shields.io/badge/GITHUB-Repository-334155?style=for-the-badge&labelColor=020617&color=475569" alt="GitHub Repository" />
</a>

<img src="https://img.shields.io/badge/MODEL-HistGradientBoosting-0b6e69?style=for-the-badge&labelColor=020617" alt="Model" />

<img src="https://img.shields.io/badge/COVERAGE-Thailand%20highways-1e3a8a?style=for-the-badge&labelColor=020617" alt="Coverage" />

<br />
<br />

<p>
  <b>RoadAware</b>
</p>

<p>
  A trip-planning web app that shows the points to take care on your route in Thailand.
</p>

<p>
  Pick an origin, a destination and a departure time — RoadAware marks the stretches of highway<br />
  where recorded accidents are expected to be highest at the time you will pass them.
</p>

</div>

<hr />

<h2 align="center">About This Project</h2>

<p align="center">
  <b>RoadAware</b> is a university project that turns Thailand's open road-accident records into a simple route briefing.
</p>

<p align="center">
  A machine-learning model (HistGradientBoosting, Poisson loss) predicts the expected number of recorded accidents<br />
  for every ~2 km stretch of national highway, for the day and the 6-hour block you travel in.
</p>

<p align="center">
  The website ranks the stretches of your route, numbers the ones that stand out, and can warn you by voice while you drive.
</p>

<p align="center">
  <i>For education and trip preparation only — not a real-time warning system. Levels compare road stretches; they are not your personal chance of an accident.</i>
</p>

<hr />

<h2 align="center">Features</h2>

<table align="center">
  <tr>
    <th>Feature</th>
    <th>Description</th>
  </tr>
  <tr>
    <td>Nationwide Coverage</td>
    <td>26,740 Department of Highways road stretches (about 51,900 km) across Thailand.</td>
  </tr>
  <tr>
    <td>Points to Take Care</td>
    <td>Numbered points in the order you reach them, with the time you are expected to pass.</td>
  </tr>
  <tr>
    <td>Time-aware Prediction</td>
    <td>Day of week, 6-hour time block, season, Songkran and New Year festivals, weather and traffic volume.</td>
  </tr>
  <tr>
    <td>Point Details</td>
    <td>What usually happened there before: main accident type, share in rain, the most common time of day.</td>
  </tr>
  <tr>
    <td>Smart Suggestions</td>
    <td>A route of similar time with fewer high-risk stretches, or a better departure time — shown only when it helps.</td>
  </tr>
  <tr>
    <td>National Comparison</td>
    <td>How each stretch ranks against all highways in Thailand (very high / high / medium / lower half).</td>
  </tr>
  <tr>
    <td>Drive Mode</td>
    <td>GPS tracking or a driving simulation, with spoken Thai warnings at 2 km, 500 m and on entering a point.</td>
  </tr>
  <tr>
    <td>Responsive Design</td>
    <td>Works on desktop and mobile (bottom-sheet layout on phones).</td>
  </tr>
</table>

<hr />

<h2 align="center">Data and Model</h2>

<table align="center">
  <tr>
    <th>Item</th>
    <th>Details</th>
  </tr>
  <tr>
    <td>Accident records</td>
    <td>Ministry of Transport open data, 2021–2025 (B.E. 2564–2568) — 98,207 records matched to road stretches</td>
  </tr>
  <tr>
    <td>Roads</td>
    <td>Department of Highways open data</td>
  </tr>
  <tr>
    <td>Other factors</td>
    <td>Calendar and festivals, weather (Open-Meteo), annual average daily traffic (AADT)</td>
  </tr>
  <tr>
    <td>Training</td>
    <td>2021–2023 (cut-off 1 Dec 2023)</td>
  </tr>
  <tr>
    <td>Model selection</td>
    <td>4-fold time-based backtest over 2022–2023 against the strongest baseline, with rules locked before the experiment</td>
  </tr>
  <tr>
    <td>Checking / Testing</td>
    <td>Checked on 2024–2025 · tested on unseen 2026 records (Jan–Sep, 15,425 records)</td>
  </tr>
</table>

<h3 align="center">Results</h3>

<table align="center">
  <tr>
    <th>Evaluation</th>
    <th>Daily</th>
    <th>6-hour</th>
  </tr>
  <tr>
    <td>Backtest 2022–2023 (Poisson deviance vs. baseline)</td>
    <td>−2.7% · wins 3/4 folds</td>
    <td>−10.6% · wins 4/4 folds</td>
  </tr>
  <tr>
    <td>Unseen 2026 records</td>
    <td>−6.5% · better every month</td>
    <td>−13.5% · better every month</td>
  </tr>
  <tr>
    <td>Songkran / New Year 2026</td>
    <td>−24% / −28%</td>
    <td>−29% / −32%</td>
  </tr>
</table>

<p align="center">
  Details and limitations: <a href="backend/reports/v4/evaluation_2026_national_summary_th.md">evaluation_2026_national_summary_th.md</a>
</p>

<hr />

<h2 align="center">Built With</h2>

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

<h2 align="center">Installation</h2>

<p align="center">
  Raw data and trained model files are large and are not stored in this repository.<br />
  The steps below assume they are present in <code>backend/data/</code> and <code>backend/rerun-*</code>.
</p>

<h3>1. Clone the repository</h3>

```bash
git clone https://github.com/Rittiporn12/RoadAware.git
cd RoadAware
```

<h3>2. Start the API</h3>

```bash
python3.9 -m venv .venv
.venv/bin/pip install -r backend/requirements-api.txt -c backend/constraints-runtime.txt
.venv/bin/python backend/scripts/run_api_server.py --national
```

<p>The API runs at <code>http://127.0.0.1:8000</code>.</p>

<h3>3. Start the website</h3>

```bash
cd frontend
npm install
npm run dev
```

<p>Open the local URL shown in the terminal.</p>

```bash
http://127.0.0.1:5173/
```

<p>
  On macOS you can also double-click <code>Start API National.command</code> and <code>Start Website.command</code>.
</p>

<hr />

<h2 align="center">Project Structure</h2>

```txt
RoadAware/
├── backend/
│   ├── notebooks/     # data and ML pipeline (01–25, *_national = nationwide)
│   ├── config/        # settings for each pipeline stage
│   ├── api/           # FastAPI service used by the website
│   ├── scripts/       # notebook runners, API server, voice helper
│   ├── reports/       # summary reports and evaluation results
│   └── tests/         # pytest
├── frontend/
│   ├── public/
│   └── src/           # React app (map, briefing, drive mode)
├── workflow/          # hash locks the API checks before loading the model
├── docs/
└── README.md
```

<hr />

<h2 align="center">Available Scripts</h2>

<table align="center">
  <tr>
    <th>Command</th>
    <th>Description</th>
  </tr>
  <tr>
    <td><code>run_api_server.py --national</code></td>
    <td>Start the API with the nationwide model</td>
  </tr>
  <tr>
    <td><code>npm run dev</code></td>
    <td>Start the website (development server)</td>
  </tr>
  <tr>
    <td><code>npm run dev:phone</code></td>
    <td>HTTPS server on your Wi-Fi for testing GPS on a phone</td>
  </tr>
  <tr>
    <td><code>npm run build</code></td>
    <td>Build the website for production</td>
  </tr>
  <tr>
    <td><code>pytest backend/tests</code></td>
    <td>Run the backend tests</td>
  </tr>
  <tr>
    <td><code>tts_proxy.py</code></td>
    <td>Optional local voice for drive-mode warnings (macOS Thai voices)</td>
  </tr>
</table>

<hr />

<h2 align="center">How to Use</h2>

<table align="center">
  <tr>
    <th>Step</th>
    <th>Description</th>
  </tr>
  <tr>
    <td>1</td>
    <td>Enter an origin and a destination, or pick them on the map.</td>
  </tr>
  <tr>
    <td>2</td>
    <td>Choose the departure day and time.</td>
  </tr>
  <tr>
    <td>3</td>
    <td>Click <b>ตรวจเส้นทางนี้</b> (Check this route).</td>
  </tr>
  <tr>
    <td>4</td>
    <td>Read the number of points to take care, and tap a point for its details.</td>
  </tr>
  <tr>
    <td>5</td>
    <td>Follow a suggestion if one appears (another route or departure time).</td>
  </tr>
  <tr>
    <td>6</td>
    <td>Click <b>เริ่มเดินทาง</b> (Start trip) to get voice warnings while you drive.</td>
  </tr>
</table>

<hr />

<h2 align="center">Data and Services Used</h2>

<p align="center">
  Map data © OpenStreetMap contributors (ODbL) · Place search: Photon (komoot) · Routing: OSRM<br />
  Country boundary: geoBoundaries (CC BY 4.0) and Natural Earth · Weather: Open-Meteo<br />
  Accident records: Ministry of Transport, Thailand · Highways: Department of Highways, Thailand
</p>

<hr />

<h2 align="center">Author</h2>

<div align="center">

<p>
  <b>Rittiporn Phungphai</b>
</p>

<p>
  Computer Science Student<br />
  Software Development | Full-Stack Development | AI & Automation | Software Quality
</p>

<p>
  <a href="https://github.com/Rittiporn12">
    GitHub Profile
  </a>
  &nbsp;|&nbsp;
  <a href="https://rittiporn12.github.io/portfolio/">
    Portfolio Website
  </a>
</p>

</div>

<hr />

<div align="center">

<p>
  <b>Thank you for visiting RoadAware.</b>
</p>

<p>
  Drive safely, and take care at the numbered points.
</p>

</div>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:334155,45:0b6e69,75:0f172a,100:020617&height=100&section=footer" alt="Footer" />
