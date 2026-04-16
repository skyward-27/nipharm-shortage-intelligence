const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

export interface NewsArticle {
  title: string;
  description: string;
  source: string;
  url: string;
  publishedAt: string;
  image?: string;
}

export interface Signal {
  [key: string]: any;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface Drug {
  id: string;
  name: string;
  discount: number;
  risk_level: string;
  shortage_probability: number;
}

export interface Concession {
  drug_name: string;
  price: number;
  date: string;
  source: string;
}

// Health check — use /ping (lightweight, no model dependency, 5s timeout)
export const healthCheck = async () => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);
  try {
    const res = await fetch(`${API_URL}/ping`, { signal: controller.signal });
    if (!res.ok) throw new Error("Backend health check failed");
    return res.json();
  } finally {
    clearTimeout(timer);
  }
};

// News endpoints
export const fetchNews = async (): Promise<NewsArticle[]> => {
  const res = await fetch(`${API_URL}/news`);
  if (!res.ok) throw new Error("Failed to fetch news");
  const data = await res.json();
  // Backend returns {success, count, articles:[]} - extract the array
  return Array.isArray(data) ? data : (data.articles || []);
};

// Signals endpoints
export const fetchSignals = async (): Promise<Signal> => {
  const res = await fetch(`${API_URL}/signals`);
  if (!res.ok) throw new Error("Failed to fetch signals");
  return res.json();
};

// Chat endpoint
export const chatWithGroq = async (
  message: string,
  history: ChatMessage[]
): Promise<{ response: string; timestamp: string }> => {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      chat_history: history,
    }),
  });
  if (!res.ok) throw new Error("Failed to send chat message");
  return res.json();
};

// Drug search endpoint
export const searchDrugs = async (query: string = ""): Promise<Drug[]> => {
  const params = new URLSearchParams();
  if (query) params.append("search", query);

  const res = await fetch(`${API_URL}/drugs?${params}`);
  if (!res.ok) throw new Error("Failed to search drugs");
  return res.json();
};

// Concessions endpoint
export const fetchConcessions = async (): Promise<Concession[]> => {
  const res = await fetch(`${API_URL}/concessions`);
  if (!res.ok) throw new Error("Failed to fetch concessions");
  return res.json();
};
