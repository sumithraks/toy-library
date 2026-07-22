export type User = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  is_email_verified: boolean;
  is_staff: boolean;
  role: "MEMBER" | "STAFF" | "ADMIN";
  is_active: boolean;
  date_joined: string;
};

export type MembershipTier = {
  id: string;
  code: "SILVER" | "PLATINUM" | "DIAMOND";
  name: string;
  description: string;
  joining_fee: string;
  deposit_amount: string;
  renewal_fee: string;
  max_concurrent_checkouts: number;
  loan_period_days: number;
  complimentary_extension_days: number;
  is_active: boolean;
};

export type MembershipSignOff = {
  id: string;
  membership: string;
  status: "REQUESTED" | "APPROVED" | "REJECTED" | "REFUNDED";
  requested_at: string;
  requested_by: string | null;
  approved_at: string | null;
  approved_by: string | null;
  rejection_reason: string;
  processed_at: string | null;
  processed_by: string | null;
  deposit_amount_due: string;
  deposit_amount_returned: string | null;
  deduction_reason: string;
};

export type Membership = {
  id: string;
  user: string;
  tier: MembershipTier;
  status: "PENDING_PAYMENT" | "ACTIVE" | "PENDING_TERMINATION" | "DISCONTINUED";
  joined_at: string | null;
  renewed_through: string | null;
  discontinued_at: string | null;
  sign_off: MembershipSignOff | null;
};

export type Toy = {
  id: string;
  model_name: string;
  make: string;
  min_age_years: number | null;
  age_rating_label: string;
  description: string;
  status:
    | "INTAKE"
    | "AVAILABLE"
    | "RESERVED"
    | "CHECKED_OUT"
    | "OVERDUE"
    | "BROKEN"
    | "UNDER_REPAIR"
    | "RETIRED";
  condition: "NEW" | "LIGHTLY_USED" | "USED" | "DAMAGED";
  source: "PURCHASED" | "DONATED";
  donation: string | null;
  image: string | null;
  barcode_or_sku: string | null;
};

export type ToyGroup = {
  make: string;
  model_name: string;
  total_count: number;
  available_count: number;
  min_age_years: number | null;
};

export type CheckoutRecord = {
  id: string;
  toy: string;
  member: string;
  membership: string;
  checked_out_at: string;
  original_due_date: string;
  current_due_date: string;
  complimentary_extension_used: boolean;
  complimentary_extension_available: boolean;
  paid_extension_rate: string;
  status: "ACTIVE" | "RETURNED" | "OVERDUE";
  returned_at: string | null;
  return_condition: string;
};

export type Reservation = {
  id: string;
  toy: string;
  user: string;
  reserved_at: string;
  pickup_by_date: string;
  pickup_deadline: string;
  status: "ACTIVE" | "PICKED_UP" | "EXPIRED" | "CANCELLED";
};

export type WaitlistEntry = {
  id: string;
  toy: string;
  user: string;
  joined_at: string;
  status: "WAITING" | "CONVERTED_TO_RESERVATION" | "EXPIRED" | "CANCELLED";
};

export type LedgerEntry = {
  id: string;
  user: string;
  entry_type: string;
  amount: string;
  direction: "CHARGE" | "CREDIT";
  status: "PENDING" | "PAID" | "WAIVED" | "CANCELLED";
  due_date: string | null;
  paid_at: string | null;
  notes: string;
  created_at: string;
};

export type NotificationLogEntry = {
  id: string;
  event_type: string;
  channel: "EMAIL" | "PUSH" | "IN_APP";
  title: string;
  body: string;
  action_url: string;
  sent_at: string;
  read_at: string | null;
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
