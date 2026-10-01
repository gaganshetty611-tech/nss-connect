import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import EventCard from '../components/EventCard'
import { CategoryBadge, StatusBadge } from '../components/ui'

describe('badges', () => {
  it('shows display names for categories', () => {
    render(<CategoryBadge category="ABP1" />)
    expect(screen.getByText('ABP 1')).toBeInTheDocument()
  })
  it('prettifies status', () => {
    render(<StatusBadge status="WAITLISTED" />)
    expect(screen.getByText('Waitlisted')).toBeInTheDocument()
  })
})

describe('EventCard', () => {
  it('renders event data passed from the API', () => {
    render(
      <MemoryRouter>
        <EventCard event={{ id: 7, title: 'Beach Clean-up', category: 'ABP1', date: '2026-10-01', start_time: '07:00:00', end_time: '10:00:00', location: 'Juhu', spots_left: 0, organizer_display: 'Green NGO', ngo_verified: true, required_skills: ['Waste'] }} />
      </MemoryRouter>,
    )
    expect(screen.getByText('Beach Clean-up')).toBeInTheDocument()
    expect(screen.getByText('Full – waitlist')).toBeInTheDocument()
    expect(screen.getByRole('link')).toHaveAttribute('href', '/events/7')
  })
})
