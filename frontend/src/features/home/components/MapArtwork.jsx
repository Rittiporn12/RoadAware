// Illustrative geography only; no map service or live accident data is used.
export default function MapArtwork() {
  const streets = Array.from({ length: 28 }, (_, i) => ({
    x: i * 42,
    y: i * 29,
  }));
  return (
    <svg
      className="map-artwork"
      viewBox="0 0 1000 600"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      <defs>
        <pattern
          id="blocks"
          width="63"
          height="49"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(-19)"
        >
          <rect width="63" height="49" fill="#e9edef" />
          <rect x="5" y="5" width="24" height="15" rx="2" fill="#dfe4e6" />
          <rect x="33" y="5" width="24" height="15" rx="2" fill="#e1e6e7" />
          <rect x="5" y="26" width="52" height="17" rx="2" fill="#e0e5e6" />
          <path d="M0 24h63M31 0v24" stroke="white" strokeWidth="3" />
        </pattern>
      </defs>
      <rect width="1000" height="600" fill="url(#blocks)" />
      <g fill="#cde3cc">
        <path d="m640 44 115 12-17 113-105-22Z" />
        <path d="m428 331 70-17 26 68-56 25Z" />
        <path d="m55 396 86-20 32 97-107 27Z" />
        <path d="m852 427 89-17 41 119-98 22Z" />
        <path d="m234 0 97 9-8 79-75-7Z" />
      </g>
      <g stroke="#fff" strokeWidth="6" fill="none">
        {streets.map(({ x, y }, i) => (
          <path
            key={i}
            d={`M${x - 200} 0 ${x + 70} 600 M0 ${y} 1000 ${y - 270}`}
          />
        ))}
      </g>
      <path
        d="M322-30C365 82 191 134 221 247S379 316 350 421 380 542 476 630"
        stroke="#b0dff0"
        strokeWidth="38"
        fill="none"
      />
      <path
        d="M322-30C365 82 191 134 221 247S379 316 350 421 380 542 476 630"
        stroke="#98d3ec"
        strokeWidth="19"
        fill="none"
      />
      <g fill="none" stroke="#fff" strokeWidth="12">
        <path d="m72-20 439 650M524-20  -4 563M657-20  -6 720M-10 290 1040 83M4 435 1020 256M460-20 76 620M710-20 470 620" />
      </g>
      <g fill="none" stroke="#f2d79a" strokeWidth="5">
        <path d="m72-20 439 650M524-20  -4 563M657-20  -6 720M-10 290 1040 83M4 435 1020 256M710-20 470 620" />
      </g>
      <g fill="#8593a2" fontSize="16" fontFamily="Tahoma, sans-serif">
        <text x="305" y="146">
          เขตดุสิต
        </text>
        <text x="408" y="239">
          เขตพญาไท
        </text>
        <text x="470" y="328">
          เขตห้วยขวาง
        </text>
        <text x="334" y="441">
          เขตคลองสาน
        </text>
        <text x="150" y="489">
          เขตบางกอกใหญ่
        </text>
        <text x="741" y="546">
          เขตบางนา
        </text>
        <text x="271" y="359" fill="#324b64" fontSize="27" fontWeight="600">
          กรุงเทพมหานคร
        </text>
      </g>
    </svg>
  );
}
