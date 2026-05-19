interface Props {
  size?: number;
  className?: string;
}

export function NexoraLogo({ size = 32, className }: Props) {
  return (
    <svg
      viewBox="0 0 120 120"
      width={size}
      height={size}
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Nexora"
    >
      {/* Hexagon outline */}
      <polygon
        points="60,10 100,32 100,76 60,98 20,76 20,32"
        stroke="currentColor"
        strokeWidth="3"
        fill="none"
      />
      {/* N letter inside */}
      <path
        d="M 38 32 L 38 76 L 50 76 L 50 50 L 70 76 L 82 76 L 82 32 L 70 32 L 70 58 L 50 32 Z"
        fill="currentColor"
      />
      {/* Node dots at hex corners */}
      <circle cx="60" cy="10" r="4" fill="currentColor" />
      <circle cx="100" cy="32" r="4" fill="currentColor" />
      <circle cx="100" cy="76" r="4" fill="currentColor" />
      <circle cx="60" cy="98" r="4" fill="currentColor" />
      <circle cx="20" cy="76" r="4" fill="currentColor" />
      <circle cx="20" cy="32" r="4" fill="currentColor" />
    </svg>
  );
}
