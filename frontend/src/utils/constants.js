export const CATEGORIES = [
  { value: 'ABP1', label: 'ABP 1', hint: 'Environmental & Community Service' },
  { value: 'ABP2', label: 'ABP 2', hint: 'Health, Education & Awareness' },
  { value: 'COLLEGE_EVENT', label: 'College Event', hint: 'Hosted at college level' },
  { value: 'UNIVERSITY_EVENT', label: 'University Event', hint: 'University / inter-college level' },
]
export const CATEGORY_LABEL = Object.fromEntries(CATEGORIES.map((c) => [c.value, c.label]))

export const THEMES = [
  { value: 'ENVIRONMENT', label: 'Environment' },
  { value: 'COMMUNITY', label: 'Community Service' },
  { value: 'HEALTH', label: 'Health' },
  { value: 'EDUCATION', label: 'Education' },
  { value: 'AWARENESS', label: 'Awareness' },
  { value: 'OTHER', label: 'Other' },
]

export const ROLES = {
  VOLUNTEER: 'Volunteer',
  NSS_COORDINATOR: 'NSS Coordinator',
  NGO_ORGANIZER: 'NGO Organizer',
  COLLEGE_ADMIN: 'College Admin',
  UNIVERSITY_ADMIN: 'University Admin',
  SUPER_ADMIN: 'Super Admin',
}
export const ADMIN_ROLES = ['COLLEGE_ADMIN', 'UNIVERSITY_ADMIN', 'SUPER_ADMIN']
export const ORGANIZER_ROLES = ['NGO_ORGANIZER', 'NSS_COORDINATOR', ...ADMIN_ROLES]

export const WEEKDAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
export const INTERESTS = ['ABP1', 'ABP2', 'COLLEGE_EVENT', 'UNIVERSITY_EVENT', 'ENVIRONMENT', 'COMMUNITY', 'HEALTH', 'EDUCATION', 'AWARENESS']
export const FOCUS_AREAS = ['ENVIRONMENT', 'COMMUNITY', 'HEALTH', 'EDUCATION', 'AWARENESS', 'OTHER']

// Chosen for what the category actually is, not an arbitrary rainbow: ABP1 is
// environmental (olive), ABP2 is health/education (ochre, like a record stamp),
// college/university events use the institutional navy/flag-red pair.
export const CATEGORY_COLORS = {
  ABP1: '#55643A',
  ABP2: '#B4791F',
  COLLEGE_EVENT: '#1B2A63',
  UNIVERSITY_EVENT: '#C7291F',
}

export const STATUS_STYLES = {
  PENDING: 'bg-amber-50 text-amber-700 ring-amber-200',
  APPROVED: 'bg-green-50 text-green-700 ring-green-200',
  VERIFIED: 'bg-green-50 text-green-700 ring-green-200',
  ACCEPTED: 'bg-green-50 text-green-700 ring-green-200',
  PRESENT: 'bg-green-50 text-green-700 ring-green-200',
  COMPLETED: 'bg-slate-100 text-slate-700 ring-slate-200',
  ONGOING: 'bg-blue-50 text-blue-700 ring-blue-200',
  WAITLISTED: 'bg-sky-50 text-sky-700 ring-sky-200',
  LATE: 'bg-amber-50 text-amber-700 ring-amber-200',
  REJECTED: 'bg-red-50 text-red-700 ring-red-200',
  ABSENT: 'bg-red-50 text-red-700 ring-red-200',
  SUSPENDED: 'bg-red-50 text-red-700 ring-red-200',
  CANCELLED: 'bg-slate-100 text-slate-500 ring-slate-200',
  WITHDRAWN: 'bg-slate-100 text-slate-500 ring-slate-200',
}
