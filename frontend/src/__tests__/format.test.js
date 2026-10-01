import { describe, expect, it } from 'vitest'
import { extractToken, pretty, toISODate } from '../utils/format'

describe('extractToken', () => {
  const token = 'aB3_-xY9aB3_-xY9aB3_-xY9aB3_-xY9aB3_-xY9aB3'
  it('reads the token from a full check-in URL', () => {
    expect(extractToken(`https://abc.trycloudflare.com/attendance/check-in/${token}`)).toBe(token)
  })
  it('accepts a bare token', () => {
    expect(extractToken(token)).toBe(token)
  })
  it('rejects unrelated QR content', () => {
    expect(extractToken('https://example.com/hello')).toBeNull()
    expect(extractToken('')).toBeNull()
  })
})

describe('helpers', () => {
  it('formats ISO dates in local time', () => {
    expect(toISODate(new Date(2026, 0, 5))).toBe('2026-01-05')
  })
  it('prettifies enum values', () => {
    expect(pretty('WAITLISTED')).toBe('Waitlisted')
  })
})
