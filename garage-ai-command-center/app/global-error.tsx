"use client"

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html>
      <body style={{ fontFamily: "system-ui", padding: 40, background: "#fff", color: "#333" }}>
        <h1>Something went wrong</h1>
        <pre style={{ background: "#f5f5f5", padding: 16, borderRadius: 8, overflow: "auto" }}>
          {error.message}
          {"\n\n"}
          {error.stack}
        </pre>
        <button
          onClick={reset}
          style={{ marginTop: 16, padding: "8px 16px", cursor: "pointer" }}
        >
          Try again
        </button>
      </body>
    </html>
  )
}
