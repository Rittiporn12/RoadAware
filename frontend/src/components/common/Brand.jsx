export default function Brand() {
  return (
    <div className="brand" aria-label="RoadAware">
      <svg
        width="49"
        height="48"
        viewBox="0 0 49 48"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M16 19h16l15 23a4 4 0 0 1-3 6H5a4 4 0 0 1-3-6Z"
          fill="#10274b"
        />
        <path
          d="m21 24-5 12 2 10"
          stroke="white"
          strokeWidth="2"
          strokeDasharray="5 4"
        />
        <path
          d="M39 14c0 10-12 22-12 22S15 24 15 14a12 12 0 1 1 24 0Z"
          fill="#ff7a2a"
        />
        <circle cx="27" cy="13" r="4.5" fill="white" />
      </svg>
      <span>
        RoadAware<span className="brand-dot">.</span>
      </span>
    </div>
  );
}
