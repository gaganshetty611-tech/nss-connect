import { Link } from 'react-router-dom'
import { formatDate, formatTime } from '../utils/format'
import { CATEGORY_COLORS } from '../utils/constants'
import { CategoryBadge, StatusBadge, VerifiedBadge } from './ui'

// A roster entry, not a card: drives are presented like entries in a filing system —
// a colored tab per category (see CATEGORY_COLORS) rather than an identical white
// rounded card with an emoji-gradient placeholder image.
export default function EventCard({ event, showStatus = false }) {
  const full = event.spots_left === 0
  const tabColor = CATEGORY_COLORS[event.category] || '#4A4437'
  return (
    <Link
      to={`/events/${event.id}`}
      className="roster-row group items-start sm:items-center"
      style={{ '--tab-color': tabColor }}
    >
      {event.event_image ? (
        <img
          src={event.event_image}
          alt={event.title ? `${event.title} – cover image` : 'Drive cover image'}
          className="hidden h-16 w-16 shrink-0 rounded-sm object-cover ring-1 ring-ink/10 sm:block"
          loading="lazy"
        />
      ) : (
        <div className="hidden h-16 w-16 shrink-0 items-center justify-center rounded-sm text-xs font-semibold text-white sm:flex" style={{ backgroundColor: tabColor }}>
          {formatDate(event.date, { day: 'numeric' })}
          <span className="ml-0.5 font-normal opacity-80">{formatDate(event.date, { month: 'short' })}</span>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <CategoryBadge category={event.category} />
          {showStatus && <StatusBadge status={event.status} />}
        </div>
        <h3 className="truncate font-display text-base font-semibold text-ink group-hover:text-navy">{event.title}</h3>
        <p className="text-xs text-ink/55">
          {formatDate(event.date, { weekday: 'short', day: 'numeric', month: 'short' })} · {formatTime(event.start_time)}–{formatTime(event.end_time)} · {event.location}
        </p>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pt-1">
          <span className="flex min-w-0 items-center gap-1 text-xs text-ink/60">
            <span className="truncate">{event.organizer_display}</span>
            {event.ngo_verified && <VerifiedBadge verified />}
          </span>
          {event.required_skills?.length > 0 && (
            <span className="truncate text-xs text-ink/45">{event.required_skills.slice(0, 3).join(' · ')}</span>
          )}
        </div>
      </div>

      <span className={`shrink-0 self-center whitespace-nowrap text-xs font-semibold ${full ? 'text-flag-600' : 'text-olive'}`}>
        {full ? 'Full – waitlist' : `${event.spots_left} spots left`}
      </span>
    </Link>
  )
}
