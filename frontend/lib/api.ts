// Empty in production, where the backend serves this screen and the API from one address.
// In development it comes from .env.development.
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "") + "/api";

export type Status = "APPROVED" | "PARTIAL" | "REJECTED" | "MANUAL_REVIEW" | "RETAKE_PHOTO";
export type ImageVersion = "clean" | "photo" | "rough";

export type ItemDecision = {
  description: string;
  category: string;
  claimed: string;
  payable: string;
  reason: string;
};

export type Decision = {
  status: Status;
  claimed: string;
  approved: string;
  steps: string[];
  items: ItemDecision[];
};

export type ReadDocument = {
  document_type: string;
  provider_name: string | null;
  patient_name: string | null;
  doctor_name: string | null;
  bill_number: string | null;
  bill_date: string | null;
  diagnosis: string | null;
  line_items: { description: string; category: string; amount: number }[];
  discount: number | null;
  total_amount: number | null;
};

export type ClaimResult = { decision: Decision; documents: ReadDocument[] };

export type SampleClaim = {
  id: string;
  title: string;
  member: { name: string; used_this_year: number };
  submitted_on: string;
  documents: string[];
};

const SUFFIX: Record<ImageVersion, string> = { clean: ".png", photo: ".photo.jpg", rough: ".rough.jpg" };

export function sampleImageUrl(name: string, version: ImageVersion): string {
  return `${API_URL}/sample-files/${name}${SUFFIX[version]}`;
}

async function send<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new Error("Could not reach the server. Check that the backend is running.");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    // The backend sends a readable reason as a string; anything else is a form validation error.
    throw new Error(typeof body?.detail === "string" ? body.detail : "The request was not accepted. Check the form and try again.");
  }
  return body as T;
}

export const getSamples = () => send<SampleClaim[]>("/samples");

export const decideSample = (id: string, version: ImageVersion) =>
  send<ClaimResult>(`/samples/${id}?version=${version}`, { method: "POST" });

export const decideClaim = (form: FormData) => send<ClaimResult>("/claims", { method: "POST", body: form });
