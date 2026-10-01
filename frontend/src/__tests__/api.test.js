import { describe, expect, it } from 'vitest'
import { errorMessage, toFormData } from '../services/api'

describe('errorMessage', () => {
  it('prefers DRF detail', () => {
    expect(errorMessage({ response: { data: { detail: 'Nope' } } })).toBe('Nope')
  })
  it('joins field errors', () => {
    expect(errorMessage({ response: { data: { email: ['Taken.'], non_field_errors: ['Bad.'] } } })).toBe('email: Taken. • Bad.')
  })
  it('explains network failures', () => {
    expect(errorMessage({ message: 'Network Error' })).toMatch(/Cannot reach the server/)
  })
})

describe('toFormData', () => {
  it('repeats array keys and skips empty values', () => {
    const fd = toFormData({ a: '1', skills: ['x', 'y'], empty: '', none: null })
    expect(fd.getAll('skills')).toEqual(['x', 'y'])
    expect(fd.has('empty')).toBe(false)
    expect(fd.get('a')).toBe('1')
  })
})
