const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type StaffRole = "founder" | "city_lead" | "event_lead";
export type UserType = "staff" | "volunteer";

export interface CurrentUser {
  user_type: UserType;
  id: number;
  name: string;
  role: StaffRole | null;
  city_id: number | null;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json();
}

export function login(loginIdentifier: string, password: string): Promise<CurrentUser> {
  return request<CurrentUser>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ login_identifier: loginIdentifier, password }),
  });
}

export function logout(): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/auth/logout", { method: "POST" });
}

export function me(): Promise<CurrentUser> {
  return request<CurrentUser>("/auth/me");
}

// --- Org: cities / venues / staff ---

export interface City {
  id: number;
  name: string;
  active: boolean;
}

export interface Venue {
  id: number;
  name: string;
  city_id: number;
  address: string;
  capacity: number;
  active: boolean;
}

export interface Staff {
  id: number;
  name: string;
  phone: string;
  email: string | null;
  login_identifier: string;
  role: StaffRole;
  city_id: number | null;
  active: boolean;
}

export const listCities = () => request<City[]>("/cities");
export const createCity = (payload: { name: string; active?: boolean }) =>
  request<City>("/cities", { method: "POST", body: JSON.stringify(payload) });
export const updateCity = (id: number, payload: Partial<Pick<City, "name" | "active">>) =>
  request<City>(`/cities/${id}`, { method: "PATCH", body: JSON.stringify(payload) });

export const listVenues = () => request<Venue[]>("/venues");
export const getVenue = (id: number) => request<Venue>(`/venues/${id}`);
export const createVenue = (payload: Omit<Venue, "id" | "active"> & { active?: boolean }) =>
  request<Venue>("/venues", { method: "POST", body: JSON.stringify(payload) });
export const updateVenue = (id: number, payload: Partial<Omit<Venue, "id" | "city_id">>) =>
  request<Venue>(`/venues/${id}`, { method: "PATCH", body: JSON.stringify(payload) });

export const listStaff = () => request<Staff[]>("/staff");
export const createStaff = (payload: {
  name: string;
  phone: string;
  email?: string | null;
  login_identifier: string;
  password: string;
  role: StaffRole;
  city_id?: number | null;
}) => request<Staff>("/staff", { method: "POST", body: JSON.stringify(payload) });
export const updateStaff = (id: number, payload: Partial<Omit<Staff, "id" | "login_identifier">>) =>
  request<Staff>(`/staff/${id}`, { method: "PATCH", body: JSON.stringify(payload) });

// --- Events ---

export type EventCategory = "art" | "social" | "wellness" | "cooking";
export type EventStatus = "draft" | "published" | "started" | "awaiting_review" | "closed" | "cancelled";

export interface Event {
  id: number;
  title: string;
  category: EventCategory;
  city_id: number;
  venue_id: number;
  starts_at: string;
  capacity: number;
  lead_id: number;
  status: EventStatus;
  started_at: string | null;
}

export const listEvents = (filters?: { city_id?: number; venue_id?: number; status_?: EventStatus }) => {
  const params = new URLSearchParams();
  if (filters?.city_id != null) params.set("city_id", String(filters.city_id));
  if (filters?.venue_id != null) params.set("venue_id", String(filters.venue_id));
  if (filters?.status_ != null) params.set("status_", filters.status_);
  const qs = params.toString();
  return request<Event[]>(`/events${qs ? `?${qs}` : ""}`);
};
export const getEvent = (id: number) => request<Event>(`/events/${id}`);
export const createEvent = (payload: Omit<Event, "id" | "status" | "started_at">) =>
  request<Event>("/events", { method: "POST", body: JSON.stringify(payload) });
export const updateEvent = (id: number, payload: Partial<Omit<Event, "id" | "status" | "city_id" | "started_at">>) =>
  request<Event>(`/events/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
export const publishEvent = (id: number) => request<Event>(`/events/${id}/publish`, { method: "POST" });
export const cancelEvent = (id: number) => request<Event>(`/events/${id}/cancel`, { method: "POST" });
export const closeDoor = (id: number) => request<Event>(`/events/${id}/close-door`, { method: "POST" });
export const duplicateEvent = (id: number, startsAt: string) =>
  request<Event>(`/events/${id}/duplicate`, { method: "POST", body: JSON.stringify({ starts_at: startsAt }) });

// --- Contacts / bookings ---

export type BookingStatus = "initiated" | "confirmed" | "checked_in" | "cancelled" | "abandoned" | "no_show";
export type BookingSource = "razorpay" | "bms" | "district" | "manual" | "csv";

export interface Contact {
  id: number;
  phone: string;
  name: string;
  email: string | null;
  city_id: number | null;
  opted_out: boolean;
}

export interface Booking {
  id: number;
  contact_id: number;
  event_id: number;
  status: BookingStatus;
  source: BookingSource;
  amount: number;
  external_id: string | null;
  created_at: string;
}

export const listContacts = (cityId?: number) =>
  request<Contact[]>(`/contacts${cityId != null ? `?city_id=${cityId}` : ""}`);
export const getContact = (id: number) => request<Contact>(`/contacts/${id}`);
export const updateContact = (id: number, payload: Partial<Omit<Contact, "id">>) =>
  request<Contact>(`/contacts/${id}`, { method: "PATCH", body: JSON.stringify(payload) });

export const listBookings = (filters?: { event_id?: number; contact_id?: number }) => {
  const params = new URLSearchParams();
  if (filters?.event_id != null) params.set("event_id", String(filters.event_id));
  if (filters?.contact_id != null) params.set("contact_id", String(filters.contact_id));
  const qs = params.toString();
  return request<Booking[]>(`/bookings${qs ? `?${qs}` : ""}`);
};
export const createManualBooking = (payload: {
  event_id: number;
  phone: string;
  name: string;
  email?: string | null;
  amount?: number;
}) => request<Booking>("/bookings/manual", { method: "POST", body: JSON.stringify(payload) });
export const checkInBooking = (eventId: number, bookingId: number) =>
  request<Booking>(`/events/${eventId}/checkin/${bookingId}`, { method: "POST" });

export interface DoorRosterEntry {
  booking_id: number;
  name: string;
  phone: string;
  status: BookingStatus;
}

export const listDoorRoster = (eventId: number) => request<DoorRosterEntry[]>(`/events/${eventId}/door-roster`);

export async function importBookingsCsv(eventId: number, file: File) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/events/${eventId}/bookings/import`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json() as Promise<{ created: number; skipped_duplicate: number; errors: { row: number; error: string }[] }>;
}

// --- Volunteers / assignments ---

export interface Volunteer {
  id: number;
  name: string;
  phone: string;
  email: string | null;
  login_identifier: string;
  city_id: number;
  skills: EventCategory[];
  cached_score: number;
  remarks: string | null;
  events_done: number;
  active: boolean;
}

export type AssignmentStatus = "pending" | "accepted" | "declined" | "expired";

export interface Assignment {
  id: number;
  event_id: number;
  volunteer_id: number;
  status: AssignmentStatus;
  assigned_by: number;
  responded_at: string | null;
  coordinator_note: string | null;
  rating: number | null;
}

export const listVolunteers = (cityId?: number) =>
  request<Volunteer[]>(`/volunteers${cityId != null ? `?city_id=${cityId}` : ""}`);
export const getVolunteer = (id: number) => request<Volunteer>(`/volunteers/${id}`);
export const createVolunteer = (payload: {
  name: string;
  phone: string;
  email?: string | null;
  login_identifier: string;
  password: string;
  city_id: number;
  skills?: EventCategory[];
}) => request<Volunteer>("/volunteers", { method: "POST", body: JSON.stringify(payload) });
export const updateVolunteer = (id: number, payload: Partial<Omit<Volunteer, "id" | "login_identifier" | "cached_score" | "events_done">>) =>
  request<Volunteer>(`/volunteers/${id}`, { method: "PATCH", body: JSON.stringify(payload) });

export const listAssignments = (filters?: { event_id?: number; volunteer_id?: number }) => {
  const params = new URLSearchParams();
  if (filters?.event_id != null) params.set("event_id", String(filters.event_id));
  if (filters?.volunteer_id != null) params.set("volunteer_id", String(filters.volunteer_id));
  const qs = params.toString();
  return request<Assignment[]>(`/assignments${qs ? `?${qs}` : ""}`);
};
export const createAssignment = (payload: { event_id: number; volunteer_id: number; coordinator_note?: string | null }) =>
  request<Assignment>("/assignments", { method: "POST", body: JSON.stringify(payload) });
export const respondToAssignment = (assignmentId: number, accept: boolean) =>
  request<Assignment>(`/assignments/${assignmentId}/respond`, { method: "POST", body: JSON.stringify({ accept }) });

export const myAssignments = () => request<Assignment[]>("/volunteers/me/assignments");
export const myWeeklyAvailability = () => request<{ days: number[] }>("/volunteers/me/availability/weekly");
export const setMyWeeklyAvailability = (days: number[]) =>
  request<{ days: number[] }>("/volunteers/me/availability/weekly", { method: "PUT", body: JSON.stringify({ days }) });

// --- Notifications ---

export interface Notification {
  id: number;
  recipient_type: "staff" | "volunteer";
  recipient_id: number;
  title: string;
  body: string;
  action_type: string | null;
  action_ref: number | null;
  read_at: string | null;
  created_at: string;
}

export const listNotifications = (unreadOnly = false) =>
  request<Notification[]>(`/notifications${unreadOnly ? "?unread_only=true" : ""}`);
export const markNotificationRead = (id: number) =>
  request<Notification>(`/notifications/${id}/read`, { method: "POST" });

// --- Knowledge system: event autopsies / decisions / issues ---

export interface EventAutopsy {
  id: number;
  event_id: number;
  submitted_by: number;
  attendance_actual: number;
  venue_rating: number;
  what_worked: string;
  what_didnt: string;
  submitted_at: string;
}

export interface PendingAutopsyEvent {
  id: number;
  title: string;
  city_id: number;
  venue_id: number;
  starts_at: string;
}

export interface Decision {
  id: number;
  title: string;
  body: string;
  author_id: number;
  city_id: number | null;
  venue_id: number | null;
  category: EventCategory | null;
  decided_at: string;
  created_at: string;
  updated_at: string;
}

export type RaisedByType = "staff" | "volunteer";
export type IssueStatus = "open" | "resolved";
export type IssueLevel = "event_lead" | "city_lead" | "founder";

export interface Issue {
  id: number;
  title: string;
  body: string;
  raised_by_type: RaisedByType;
  raised_by_id: number;
  event_id: number | null;
  venue_id: number | null;
  volunteer_id: number | null;
  status: IssueStatus;
  current_level: IssueLevel;
  resolution_note: string | null;
  resolved_by: number | null;
  created_at: string;
  resolved_at: string | null;
}

export const getAutopsy = (eventId: number) => request<EventAutopsy>(`/events/${eventId}/autopsy`);
export const submitAutopsy = (
  eventId: number,
  payload: {
    attendance_actual: number;
    venue_rating: number;
    what_worked: string;
    what_didnt: string;
    volunteer_ratings?: { assignment_id: number; rating: number; coordinator_note?: string | null }[];
  }
) => request<EventAutopsy>(`/events/${eventId}/autopsy`, { method: "POST", body: JSON.stringify(payload) });
export const listVenueAutopsies = (venueId: number, limit?: number) =>
  request<EventAutopsy[]>(`/venues/${venueId}/autopsies${limit != null ? `?limit=${limit}` : ""}`);
export const listPendingAutopsies = (cityId?: number) =>
  request<PendingAutopsyEvent[]>(`/autopsies/pending${cityId != null ? `?city_id=${cityId}` : ""}`);

export const listDecisions = (params?: { cityId?: number; venueId?: number; category?: EventCategory; q?: string }) => {
  const qs = new URLSearchParams();
  if (params?.cityId != null) qs.set("city_id", String(params.cityId));
  if (params?.venueId != null) qs.set("venue_id", String(params.venueId));
  if (params?.category) qs.set("category", params.category);
  if (params?.q) qs.set("q", params.q);
  const suffix = qs.toString();
  return request<Decision[]>(`/decisions${suffix ? `?${suffix}` : ""}`);
};
export const getDecision = (id: number) => request<Decision>(`/decisions/${id}`);
export const createDecision = (payload: {
  title: string;
  body: string;
  city_id?: number | null;
  venue_id?: number | null;
  category?: EventCategory | null;
  decided_at: string;
}) => request<Decision>("/decisions", { method: "POST", body: JSON.stringify(payload) });
export const updateDecision = (
  id: number,
  payload: Partial<Pick<Decision, "title" | "body" | "city_id" | "venue_id" | "category" | "decided_at">>
) => request<Decision>(`/decisions/${id}`, { method: "PATCH", body: JSON.stringify(payload) });

export const listIssues = (params?: { cityId?: number; venueId?: number; eventId?: number }) => {
  const qs = new URLSearchParams();
  if (params?.cityId != null) qs.set("city_id", String(params.cityId));
  if (params?.venueId != null) qs.set("venue_id", String(params.venueId));
  if (params?.eventId != null) qs.set("event_id", String(params.eventId));
  const suffix = qs.toString();
  return request<Issue[]>(`/issues${suffix ? `?${suffix}` : ""}`);
};
export const getIssue = (id: number) => request<Issue>(`/issues/${id}`);
export const createIssue = (payload: {
  title: string;
  body: string;
  event_id?: number | null;
  venue_id?: number | null;
  volunteer_id?: number | null;
}) => request<Issue>("/issues", { method: "POST", body: JSON.stringify(payload) });
export const escalateIssue = (id: number) => request<Issue>(`/issues/${id}/escalate`, { method: "POST" });
export const resolveIssue = (id: number, resolutionNote: string) =>
  request<Issue>(`/issues/${id}/resolve`, { method: "POST", body: JSON.stringify({ resolution_note: resolutionNote }) });
export const issuePatternCount = (params: { venueId?: number; volunteerId?: number }) => {
  const qs = new URLSearchParams();
  if (params.venueId != null) qs.set("venue_id", String(params.venueId));
  if (params.volunteerId != null) qs.set("volunteer_id", String(params.volunteerId));
  return request<{ count: number }>(`/issues/pattern-count?${qs.toString()}`);
};
