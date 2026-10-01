import { useEffect, useRef, useState } from 'react'

/**
 * Camera QR scanner (html5-qrcode). Works in mobile browsers over HTTPS (or localhost).
 * Calls onScan(text) once per successful decode.
 */
export default function QRScanner({ onScan }) {
  const containerId = useRef(`qr-${Math.random().toString(36).slice(2)}`)
  const [error, setError] = useState(null)
  const scanned = useRef(false)

  useEffect(() => {
    let scanner
    let stopped = false
    if (!window.isSecureContext) {
      setError('Camera access needs HTTPS. Open the app through the tunnel URL (https://…) or on localhost.')
      return undefined
    }
    import('html5-qrcode')
      .then(({ Html5Qrcode }) => {
        if (stopped) return
        scanner = new Html5Qrcode(containerId.current)
        return scanner.start(
          { facingMode: 'environment' },
          { fps: 10, qrbox: { width: 240, height: 240 } },
          (text) => {
            if (scanned.current) return
            scanned.current = true
            onScan(text)
          },
          () => {},
        )
      })
      .catch((e) => setError(e?.message || 'Could not start the camera. Allow camera permission and try again.'))
    return () => {
      stopped = true
      if (scanner?.isScanning) scanner.stop().catch(() => {})
    }
  }, [onScan])

  return (
    <div>
      <div id={containerId.current} className="mx-auto aspect-square w-full max-w-sm overflow-hidden rounded-2xl bg-slate-900" />
      {error && <p className="mt-3 text-center text-sm text-red-600">{error}</p>}
    </div>
  )
}
