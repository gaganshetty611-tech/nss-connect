import { useRef } from 'react'

/**
 * Lightweight bot protection for public forms (the API also rate-limits auth endpoints).
 *  - honeypot: a hidden field humans never fill in
 *  - timing: real people need more than ~1s to complete a form
 * Usage: const { honeypot, isBot } = useSpamGuard(register); render {honeypot}; in onSubmit: if (isBot(values)) return
 */
export function useSpamGuard(register) {
  const startedAt = useRef(Date.now())
  const honeypot = (
    <div aria-hidden="true" style={{ position: 'absolute', left: '-9999px', width: 1, height: 1, overflow: 'hidden' }}>
      <label>
        Leave this field empty
        <input type="text" tabIndex={-1} autoComplete="off" {...register('website')} />
      </label>
    </div>
  )
  const isBot = (values) => Boolean(values?.website) || Date.now() - startedAt.current < 1000
  return { honeypot, isBot }
}
