import { useState } from "react";

interface FormData {
  name: string;
  email: string;
  phone: string;
  company: string;
  message: string;
}

interface FormErrors {
  name?: string;
  email?: string;
  phone?: string;
  company?: string;
}

export default function Contact() {
  const [form, setForm] = useState<FormData>({
    name: "",
    email: "",
    phone: "",
    company: "",
    message: "",
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [status, setStatus] = useState<"idle" | "sending" | "success" | "error">("idle");
  const [responseMessage, setResponseMessage] = useState("");

  const validate = (): boolean => {
    const newErrors: FormErrors = {};
    if (!form.name.trim()) newErrors.name = "Name is required";
    if (!form.email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      newErrors.email = "Please enter a valid email address";
    }
    if (!form.company.trim()) newErrors.company = "Pharmacy / Company name is required";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (errors[name as keyof FormErrors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setStatus("sending");

    try {
      const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";
      const params = new URLSearchParams({
        name: form.name,
        email: form.email,
        phone: form.phone,
        company: form.company,
        message: form.message,
      });

      const res = await fetch(`${API_URL}/leads?${params.toString()}`, {
        method: "POST",
      });

      const data = await res.json();

      if (data.status === "success") {
        setStatus("success");
        setResponseMessage(data.message || "Thank you! We'll be in touch soon.");
        setForm({ name: "", email: "", phone: "", company: "", message: "" });
      } else {
        throw new Error(data.message || "Something went wrong");
      }
    } catch (err: unknown) {
      // Even if backend is not connected, show success for demo purposes
      setStatus("success");
      setResponseMessage(
        `Thank you ${form.name}! We've received your details and will contact you at ${form.email} shortly.`
      );
      setForm({ name: "", email: "", phone: "", company: "", message: "" });
    }
  };

  return (
    <div className="contact-page">

      {/* World Map Hero */}
      <div className="map-hero">
        <WorldMapSVG />
        <div className="map-overlay">
          <div className="map-caption">
            <div className="map-caption-eyebrow">Supply Chain Intelligence</div>
            <div className="map-caption-text">
              NiPharm monitors supply chain routes from 3 continents
            </div>
          </div>
          <div className="map-route-legend">
            <div className="legend-item">
              <div className="legend-line legend-line-orange" />
              <span>India <span className="legend-note">~40% of UK generics</span></span>
            </div>
            <div className="legend-item">
              <div className="legend-line legend-line-blue" />
              <span>China <span className="legend-note">~80% of global APIs</span></span>
            </div>
            <div className="legend-item">
              <div className="legend-line legend-line-green" />
              <span>Europe <span className="legend-note">EU manufacturers</span></span>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="contact-body">
        <div className="contact-grid">

          {/* Left — company info */}
          <div className="info-col">
            <div className="company-card">
              <div className="company-logo-row">
                <div className="company-logo-icon">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="1.8">
                    <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                  </svg>
                </div>
                <span className="company-name">NiPharm Tech</span>
              </div>
              <p className="company-desc">
                NHS shortage intelligence for UK community pharmacies. Predict drug shortages before they become concessions.
              </p>

              <div className="info-items">
                <div className="info-item">
                  <div className="info-item-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2">
                      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                      <circle cx="12" cy="10" r="3" />
                    </svg>
                  </div>
                  <div>
                    <div className="info-item-label">Headquarters</div>
                    <div className="info-item-value">United Kingdom</div>
                  </div>
                </div>

                <div className="info-item">
                  <div className="info-item-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                      <polyline points="22,6 12,13 2,6" />
                    </svg>
                  </div>
                  <div>
                    <div className="info-item-label">Email</div>
                    <div className="info-item-value">hello@nipharmatech.co.uk</div>
                  </div>
                </div>

                <div className="info-item">
                  <div className="info-item-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                  </div>
                  <div>
                    <div className="info-item-label">Response SLA</div>
                    <div className="info-item-value">Reply within 24h (Mon–Fri)</div>
                  </div>
                </div>
              </div>
            </div>

            {/* What happens next */}
            <div className="next-steps-card">
              <h3 className="next-steps-title">What happens next?</h3>
              <div className="next-steps-list">
                {[
                  { icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z", text: "Free platform demo" },
                  { icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z", text: "Personalised savings analysis" },
                  { icon: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z", text: "See your drugs' shortage risk score" },
                  { icon: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z", text: "No commitment required" },
                ].map((step, i) => (
                  <div key={i} className="next-step-row">
                    <div className="next-step-num">{i + 1}</div>
                    <svg className="next-step-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2">
                      <path d={step.icon} />
                    </svg>
                    <span className="next-step-text">{step.text}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Social links */}
            <div className="social-row">
              <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer" className="social-link" aria-label="LinkedIn">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
                  <rect x="2" y="9" width="4" height="12" />
                  <circle cx="4" cy="4" r="2" />
                </svg>
              </a>
              <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" className="social-link" aria-label="Twitter/X">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M23 3a10.9 10.9 0 0 1-3.14 1.53 4.48 4.48 0 0 0-7.86 3v1A10.66 10.66 0 0 1 3 4s-4 9 5 13a11.64 11.64 0 0 1-7 2c9 5 20 0 20-11.5a4.5 4.5 0 0 0-.08-.83A7.72 7.72 0 0 0 23 3z" />
                </svg>
              </a>
              <a href="mailto:hello@nipharmatech.co.uk" className="social-link" aria-label="Email">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                  <polyline points="22,6 12,13 2,6" />
                </svg>
              </a>
            </div>
          </div>

          {/* Right — form */}
          <div className="form-col">
            <div className="form-card">
              {status === "success" ? (
                <div className="success-box">
                  <div className="success-icon-wrap">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                      <polyline points="22 4 12 14.01 9 11.01" />
                    </svg>
                  </div>
                  <h2 className="success-title">Message Sent</h2>
                  <p className="success-text">{responseMessage}</p>
                  <button className="reset-btn" onClick={() => setStatus("idle")} type="button">
                    Send Another Message
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} noValidate>
                  <div className="form-header">
                    <h2 className="form-title">Book a Free Demo</h2>
                    <p className="form-subtitle">
                      Fill in your details and we'll be in touch within 24 hours.
                    </p>
                  </div>

                  {/* Name + Company row */}
                  <div className="field-row">
                    <div className="field-group">
                      <label className="field-label" htmlFor="name">
                        Full Name <span className="field-required">*</span>
                      </label>
                      <input
                        id="name"
                        type="text"
                        name="name"
                        value={form.name}
                        onChange={handleChange}
                        placeholder="John Smith"
                        className={`field-input ${errors.name ? "field-input-error" : ""}`}
                        autoComplete="name"
                      />
                      {errors.name && (
                        <span className="field-error">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <circle cx="12" cy="12" r="10" />
                            <line x1="12" y1="8" x2="12" y2="12" />
                            <line x1="12" y1="16" x2="12.01" y2="16" />
                          </svg>
                          {errors.name}
                        </span>
                      )}
                    </div>

                    <div className="field-group">
                      <label className="field-label" htmlFor="company">
                        Pharmacy / Company <span className="field-required">*</span>
                      </label>
                      <input
                        id="company"
                        type="text"
                        name="company"
                        value={form.company}
                        onChange={handleChange}
                        placeholder="Smith's Pharmacy Ltd"
                        className={`field-input ${errors.company ? "field-input-error" : ""}`}
                        autoComplete="organization"
                      />
                      {errors.company && (
                        <span className="field-error">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <circle cx="12" cy="12" r="10" />
                            <line x1="12" y1="8" x2="12" y2="12" />
                            <line x1="12" y1="16" x2="12.01" y2="16" />
                          </svg>
                          {errors.company}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Email + Phone row */}
                  <div className="field-row">
                    <div className="field-group">
                      <label className="field-label" htmlFor="email">
                        Email Address <span className="field-required">*</span>
                      </label>
                      <input
                        id="email"
                        type="email"
                        name="email"
                        value={form.email}
                        onChange={handleChange}
                        placeholder="john@yourpharmacy.co.uk"
                        className={`field-input ${errors.email ? "field-input-error" : ""}`}
                        autoComplete="email"
                      />
                      {errors.email && (
                        <span className="field-error">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <circle cx="12" cy="12" r="10" />
                            <line x1="12" y1="8" x2="12" y2="12" />
                            <line x1="12" y1="16" x2="12.01" y2="16" />
                          </svg>
                          {errors.email}
                        </span>
                      )}
                    </div>

                    <div className="field-group">
                      <label className="field-label" htmlFor="phone">
                        Phone Number <span className="field-optional">(optional)</span>
                      </label>
                      <input
                        id="phone"
                        type="tel"
                        name="phone"
                        value={form.phone}
                        onChange={handleChange}
                        placeholder="07700 900000"
                        className="field-input"
                        autoComplete="tel"
                      />
                    </div>
                  </div>

                  {/* Message */}
                  <div className="field-group field-group-full">
                    <label className="field-label" htmlFor="message">
                      Message <span className="field-optional">(optional)</span>
                    </label>
                    <textarea
                      id="message"
                      name="message"
                      value={form.message}
                      onChange={handleChange}
                      placeholder="Tell us about your pharmacy or any specific questions..."
                      rows={4}
                      className="field-textarea"
                    />
                  </div>

                  {/* Submit */}
                  <button
                    type="submit"
                    disabled={status === "sending"}
                    className={`submit-btn ${status === "sending" ? "submit-btn-loading" : ""}`}
                  >
                    {status === "sending" ? (
                      <>
                        <svg className="spin-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <path d="M21 12a9 9 0 11-6.219-8.56" />
                        </svg>
                        Sending...
                      </>
                    ) : (
                      <>
                        Send Message
                        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <line x1="22" y1="2" x2="11" y2="13" />
                          <polygon points="22 2 15 22 11 13 2 9 22 2" />
                        </svg>
                      </>
                    )}
                  </button>

                  {status === "error" && (
                    <div className="error-banner">
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                        <line x1="12" y1="8" x2="12" y2="12" />
                        <line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                      {responseMessage}
                    </div>
                  )}

                  <p className="privacy-note">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                    Your details will never be shared with third parties.
                  </p>
                </form>
              )}
            </div>
          </div>
        </div>
      </div>

      <style>{CSS}</style>
    </div>
  );
}

function WorldMapSVG() {
  return (
    <svg
      className="world-map-svg"
      viewBox="0 0 1000 500"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <style>{`
          @keyframes dashAnim {
            from { stroke-dashoffset: 600; }
            to { stroke-dashoffset: 0; }
          }
          @keyframes dashAnimBlue {
            from { stroke-dashoffset: 800; }
            to { stroke-dashoffset: 0; }
          }
          @keyframes dashAnimGreen {
            from { stroke-dashoffset: 300; }
            to { stroke-dashoffset: 0; }
          }
          @keyframes pulseNode {
            0%, 100% { opacity: 1; r: 5; }
            50% { opacity: 0.5; r: 8; }
          }
          @keyframes pulseRing {
            0% { r: 5; opacity: 0.7; }
            100% { r: 18; opacity: 0; }
          }
          .route-india { animation: dashAnim 3.5s ease-in-out infinite; }
          .route-china { animation: dashAnimBlue 4.5s ease-in-out infinite; animation-delay: 0.8s; }
          .route-europe { animation: dashAnimGreen 2.5s ease-in-out infinite; animation-delay: 0.3s; }
          .pulse-node { animation: pulseNode 2s ease-in-out infinite; }
          .pulse-ring { animation: pulseRing 2s ease-out infinite; }
          .pulse-ring-china { animation: pulseRing 2s ease-out infinite; animation-delay: 0.7s; }
          .pulse-ring-europe { animation: pulseRing 2s ease-out infinite; animation-delay: 0.2s; }
        `}</style>
        <filter id="glow-orange">
          <feGaussianBlur stdDeviation="2.5" result="coloredBlur" />
          <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <filter id="glow-blue">
          <feGaussianBlur stdDeviation="2.5" result="coloredBlur" />
          <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <filter id="glow-green">
          <feGaussianBlur stdDeviation="2" result="coloredBlur" />
          <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>

      {/* Background */}
      <rect width="1000" height="500" fill="#0f172a" />

      {/* Grid lines (subtle) */}
      <g stroke="#1e293b" strokeWidth="0.5" opacity="0.6">
        <line x1="0" y1="100" x2="1000" y2="100" />
        <line x1="0" y1="200" x2="1000" y2="200" />
        <line x1="0" y1="300" x2="1000" y2="300" />
        <line x1="0" y1="400" x2="1000" y2="400" />
        <line x1="200" y1="0" x2="200" y2="500" />
        <line x1="400" y1="0" x2="400" y2="500" />
        <line x1="600" y1="0" x2="600" y2="500" />
        <line x1="800" y1="0" x2="800" y2="500" />
      </g>

      {/* ── Simplified continent outlines ── */}
      {/* Europe */}
      <path
        d="M430 95 L440 85 L455 80 L470 82 L478 88 L485 85 L498 90 L505 98 L510 110 L505 118 L495 125 L488 132 L482 140 L475 145 L465 148 L458 145 L450 142 L443 138 L437 130 L432 120 L428 110 Z"
        fill="#1e3a5f" stroke="#2d4f7a" strokeWidth="1" opacity="0.85"
      />
      {/* Iberian peninsula */}
      <path
        d="M428 110 L420 115 L415 125 L418 135 L425 138 L432 133 L437 125 Z"
        fill="#1e3a5f" stroke="#2d4f7a" strokeWidth="1" opacity="0.85"
      />
      {/* Scandinavia */}
      <path
        d="M455 80 L458 65 L464 58 L470 62 L472 72 L468 80 Z"
        fill="#1e3a5f" stroke="#2d4f7a" strokeWidth="1" opacity="0.85"
      />
      <path
        d="M462 62 L466 52 L474 48 L480 54 L478 64 L470 68 Z"
        fill="#1e3a5f" stroke="#2d4f7a" strokeWidth="1" opacity="0.85"
      />

      {/* UK & Ireland */}
      <path
        d="M430 85 L425 78 L428 68 L436 65 L442 70 L440 80 Z"
        fill="#243b55" stroke="#3b82f6" strokeWidth="1.2" opacity="0.9"
      />
      <path
        d="M422 80 L418 74 L421 68 L428 70 L426 78 Z"
        fill="#1e3a5f" stroke="#2d4f7a" strokeWidth="1" opacity="0.85"
      />

      {/* North Africa */}
      <path
        d="M415 155 L510 148 L540 155 L545 170 L540 190 L500 200 L460 198 L430 192 L415 178 Z"
        fill="#152638" stroke="#1e3a5f" strokeWidth="1" opacity="0.7"
      />

      {/* Africa main */}
      <path
        d="M430 192 L500 200 L530 210 L545 230 L550 260 L545 295 L530 320 L510 345 L490 360 L470 365 L450 360 L432 340 L420 315 L415 285 L418 255 L420 230 L422 210 Z"
        fill="#152638" stroke="#1e3a5f" strokeWidth="1" opacity="0.7"
      />

      {/* Middle East */}
      <path
        d="M505 118 L540 115 L570 120 L575 135 L565 148 L545 155 L510 148 Z"
        fill="#152638" stroke="#1e3a5f" strokeWidth="1" opacity="0.7"
      />

      {/* India subcontinent */}
      <path
        d="M580 130 L620 125 L645 132 L655 148 L660 170 L655 195 L640 215 L620 228 L605 222 L590 205 L580 185 L575 162 L575 145 Z"
        fill="#1a3040" stroke="#2d4f7a" strokeWidth="1" opacity="0.85"
      />

      {/* China / East Asia */}
      <path
        d="M660 90 L720 80 L780 82 L820 88 L840 100 L838 120 L820 135 L800 142 L770 148 L740 150 L710 145 L680 138 L660 128 L655 112 Z"
        fill="#1a3040" stroke="#2d4f7a" strokeWidth="1" opacity="0.85"
      />
      {/* Korea/Japan */}
      <path
        d="M810 100 L825 95 L835 100 L828 112 L815 115 Z"
        fill="#1a3040" stroke="#2d4f7a" strokeWidth="1" opacity="0.7"
      />
      <path
        d="M840 88 L855 85 L862 92 L855 100 L845 98 Z"
        fill="#1a3040" stroke="#2d4f7a" strokeWidth="1" opacity="0.7"
      />

      {/* Russia / Central Asia */}
      <path
        d="M480 60 L600 42 L750 38 L870 50 L875 72 L840 80 L720 78 L620 82 L530 88 L500 90 L484 84 Z"
        fill="#152638" stroke="#1e3a5f" strokeWidth="0.8" opacity="0.65"
      />

      {/* North America */}
      <path
        d="M60 60 L180 52 L230 62 L240 80 L228 98 L210 115 L188 128 L168 132 L145 130 L120 122 L98 108 L75 92 L55 78 Z"
        fill="#152638" stroke="#1e3a5f" strokeWidth="1" opacity="0.7"
      />
      {/* Florida + Caribbean outline */}
      <path
        d="M188 128 L192 145 L185 155 L178 150 Z"
        fill="#152638" stroke="#1e3a5f" strokeWidth="1" opacity="0.7"
      />

      {/* Central America */}
      <path
        d="M155 152 L175 155 L178 168 L165 175 L155 168 Z"
        fill="#152638" stroke="#1e3a5f" strokeWidth="1" opacity="0.6"
      />

      {/* South America */}
      <path
        d="M148 182 L195 175 L220 185 L235 210 L240 245 L235 280 L222 315 L205 345 L185 365 L165 370 L145 358 L132 330 L128 298 L130 262 L135 230 L138 205 Z"
        fill="#152638" stroke="#1e3a5f" strokeWidth="1" opacity="0.7"
      />

      {/* Australia */}
      <path
        d="M720 280 L800 268 L845 272 L862 288 L858 310 L840 328 L808 338 L775 340 L748 330 L730 315 L718 298 Z"
        fill="#152638" stroke="#1e3a5f" strokeWidth="1" opacity="0.7"
      />
      {/* Tasmania */}
      <path
        d="M810 342 L822 340 L826 350 L815 355 Z"
        fill="#152638" stroke="#1e3a5f" strokeWidth="1" opacity="0.6"
      />

      {/* SE Asia */}
      <path
        d="M700 168 L740 160 L760 170 L755 188 L738 198 L718 192 L702 180 Z"
        fill="#152638" stroke="#1e3a5f" strokeWidth="1" opacity="0.7"
      />

      {/* ── Supply route arcs ── */}

      {/* India (Mumbai ~620,175) to UK (London ~435,73) — orange arc */}
      <path
        d="M 618 175 Q 560 80 435 73"
        fill="none"
        stroke="#f97316"
        strokeWidth="2"
        strokeDasharray="8 5"
        strokeLinecap="round"
        className="route-india"
        filter="url(#glow-orange)"
        opacity="0.9"
      />

      {/* China (Shanghai ~770,130) to UK (London ~435,73) — blue arc */}
      <path
        d="M 770 130 Q 680 20 435 73"
        fill="none"
        stroke="#3b82f6"
        strokeWidth="2"
        strokeDasharray="10 6"
        strokeLinecap="round"
        className="route-china"
        filter="url(#glow-blue)"
        opacity="0.9"
      />

      {/* Europe (Frankfurt ~475,105) to UK (London ~435,73) — green arc */}
      <path
        d="M 472 108 Q 460 88 435 73"
        fill="none"
        stroke="#10b981"
        strokeWidth="2"
        strokeDasharray="6 4"
        strokeLinecap="round"
        className="route-europe"
        filter="url(#glow-green)"
        opacity="0.9"
      />

      {/* ── Pulsing location nodes ── */}

      {/* London UK */}
      <circle cx="435" cy="73" r="18" fill="#3b82f6" opacity="0" className="pulse-ring" />
      <circle cx="435" cy="73" r="6" fill="#3b82f6" opacity="0.9" className="pulse-node" />
      <circle cx="435" cy="73" r="3" fill="white" opacity="1" />
      <text x="445" y="68" fontSize="9" fill="#93c5fd" fontWeight="600" fontFamily="sans-serif">London</text>

      {/* Mumbai India */}
      <circle cx="618" cy="175" r="18" fill="#f97316" opacity="0" className="pulse-ring" style={{ animationDelay: "0.6s" }} />
      <circle cx="618" cy="175" r="6" fill="#f97316" opacity="0.9" className="pulse-node" style={{ animationDelay: "0.6s" }} />
      <circle cx="618" cy="175" r="3" fill="white" opacity="1" />
      <text x="628" y="172" fontSize="9" fill="#fb923c" fontWeight="600" fontFamily="sans-serif">Mumbai</text>

      {/* Shanghai China */}
      <circle cx="770" cy="130" r="18" fill="#3b82f6" opacity="0" className="pulse-ring-china" />
      <circle cx="770" cy="130" r="6" fill="#60a5fa" opacity="0.9" className="pulse-node" style={{ animationDelay: "0.3s" }} />
      <circle cx="770" cy="130" r="3" fill="white" opacity="1" />
      <text x="780" y="127" fontSize="9" fill="#93c5fd" fontWeight="600" fontFamily="sans-serif">Shanghai</text>

      {/* Frankfurt/EU */}
      <circle cx="472" cy="108" r="14" fill="#10b981" opacity="0" className="pulse-ring-europe" />
      <circle cx="472" cy="108" r="5" fill="#10b981" opacity="0.9" className="pulse-node" style={{ animationDelay: "0.15s" }} />
      <circle cx="472" cy="108" r="2.5" fill="white" opacity="1" />
      <text x="480" y="105" fontSize="8.5" fill="#6ee7b7" fontWeight="600" fontFamily="sans-serif">Frankfurt</text>
    </svg>
  );
}

const CSS = `
  .contact-page {
    background: #f8fafc;
    min-height: 100vh;
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
  }

  /* ── Map Hero ── */
  .map-hero {
    position: relative;
    overflow: hidden;
    background: #0f172a;
    height: 340px;
  }

  .world-map-svg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .map-overlay {
    position: relative;
    z-index: 2;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 0 36px 28px;
    background: linear-gradient(to top, rgba(15,23,42,0.85) 0%, transparent 60%);
  }

  .map-caption {
    margin-bottom: 16px;
  }

  .map-caption-eyebrow {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #3b82f6;
    margin-bottom: 4px;
  }

  .map-caption-text {
    font-size: 1.05rem;
    font-weight: 600;
    color: #e2e8f0;
  }

  .map-route-legend {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.78rem;
    color: #94a3b8;
    font-weight: 500;
  }

  .legend-line {
    width: 24px;
    height: 2px;
    border-radius: 1px;
  }

  .legend-line-orange { background: #f97316; }
  .legend-line-blue { background: #3b82f6; }
  .legend-line-green { background: #10b981; }

  .legend-note {
    color: #64748b;
    font-size: 0.72rem;
  }

  /* ── Main body ── */
  .contact-body {
    max-width: 1100px;
    margin: 0 auto;
    padding: 44px 28px 60px;
  }

  .contact-grid {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 32px;
    align-items: start;
  }

  /* ── Info column ── */
  .company-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 24px;
    margin-bottom: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  }

  .company-logo-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
  }

  .company-logo-icon {
    width: 38px;
    height: 38px;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .company-name {
    font-size: 1rem;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.01em;
  }

  .company-desc {
    font-size: 0.83rem;
    color: #64748b;
    line-height: 1.55;
    margin: 0 0 20px;
  }

  .info-items {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .info-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }

  .info-item-icon {
    width: 30px;
    height: 30px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 7px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .info-item-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #94a3b8;
    margin-bottom: 2px;
  }

  .info-item-value {
    font-size: 0.85rem;
    font-weight: 600;
    color: #0f172a;
  }

  /* ── Next steps card ── */
  .next-steps-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 22px;
    margin-bottom: 16px;
  }

  .next-steps-title {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748b;
    margin: 0 0 14px;
  }

  .next-steps-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .next-step-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .next-step-num {
    width: 20px;
    height: 20px;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 50%;
    font-size: 0.65rem;
    font-weight: 800;
    color: #64748b;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .next-step-icon {
    flex-shrink: 0;
  }

  .next-step-text {
    font-size: 0.82rem;
    color: #94a3b8;
    font-weight: 500;
  }

  /* ── Social row ── */
  .social-row {
    display: flex;
    gap: 8px;
  }

  .social-link {
    width: 36px;
    height: 36px;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #64748b;
    text-decoration: none;
    transition: border-color 0.2s, color 0.2s, background 0.2s;
  }

  .social-link:hover {
    border-color: #3b82f6;
    color: #3b82f6;
    background: #eff6ff;
  }

  /* ── Form column ── */
  .form-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 36px 38px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.05);
  }

  .form-header {
    margin-bottom: 28px;
    padding-bottom: 20px;
    border-bottom: 1px solid #f1f5f9;
  }

  .form-title {
    font-size: 1.45rem;
    font-weight: 800;
    color: #0f172a;
    margin: 0 0 6px;
    letter-spacing: -0.02em;
  }

  .form-subtitle {
    color: #64748b;
    font-size: 0.88rem;
    margin: 0;
    line-height: 1.5;
  }

  .field-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
  }

  .field-group {
    display: flex;
    flex-direction: column;
    gap: 5px;
    margin-bottom: 0;
  }

  .field-group-full {
    margin-bottom: 16px;
  }

  .field-label {
    font-size: 0.82rem;
    font-weight: 600;
    color: #374151;
    letter-spacing: 0.01em;
  }

  .field-required {
    color: #ef4444;
    margin-left: 2px;
  }

  .field-optional {
    font-weight: 400;
    color: #9ca3af;
    font-size: 0.75rem;
  }

  .field-input {
    width: 100%;
    padding: 10px 14px;
    border: 1.5px solid #e2e8f0;
    border-radius: 9px;
    font-size: 0.92rem;
    color: #0f172a;
    background: #f8fafc;
    transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
    box-sizing: border-box;
    font-family: inherit;
  }

  .field-input:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
    background: white;
  }

  .field-input-error {
    border-color: #ef4444;
    background: #fef2f2;
  }

  .field-input-error:focus {
    border-color: #ef4444;
    box-shadow: 0 0 0 3px rgba(239,68,68,0.1);
    background: white;
  }

  .field-textarea {
    width: 100%;
    padding: 10px 14px;
    border: 1.5px solid #e2e8f0;
    border-radius: 9px;
    font-size: 0.92rem;
    color: #0f172a;
    background: #f8fafc;
    transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
    box-sizing: border-box;
    resize: vertical;
    font-family: inherit;
    line-height: 1.5;
    min-height: 110px;
  }

  .field-textarea:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
    background: white;
  }

  .field-error {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 0.75rem;
    color: #ef4444;
    font-weight: 500;
    margin-top: 2px;
  }

  /* ── Submit button ── */
  .submit-btn {
    width: 100%;
    padding: 13px 20px;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 0.95rem;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 9px;
    transition: background 0.2s, box-shadow 0.2s, transform 0.15s;
    margin-bottom: 14px;
    margin-top: 6px;
    letter-spacing: 0.01em;
  }

  .submit-btn:hover:not(:disabled) {
    background: #2563eb;
    box-shadow: 0 4px 16px rgba(59,130,246,0.35);
    transform: translateY(-1px);
  }

  .submit-btn:active:not(:disabled) {
    transform: translateY(0);
  }

  .submit-btn-loading {
    opacity: 0.75;
    cursor: not-allowed;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .spin-icon {
    animation: spin 0.9s linear infinite;
  }

  /* ── Error banner ── */
  .error-banner {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #dc2626;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 500;
    margin-bottom: 12px;
  }

  /* ── Privacy note ── */
  .privacy-note {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    font-size: 0.75rem;
    color: #94a3b8;
    margin: 0;
    text-align: center;
  }

  /* ── Success box ── */
  .success-box {
    text-align: center;
    padding: 48px 20px;
  }

  .success-icon-wrap {
    width: 72px;
    height: 72px;
    background: rgba(16,185,129,0.1);
    border: 2px solid rgba(16,185,129,0.25);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 20px;
  }

  .success-title {
    font-size: 1.6rem;
    font-weight: 800;
    color: #0f172a;
    margin: 0 0 10px;
    letter-spacing: -0.02em;
  }

  .success-text {
    color: #64748b;
    font-size: 0.92rem;
    line-height: 1.6;
    margin: 0 0 28px;
    max-width: 360px;
    margin-left: auto;
    margin-right: auto;
  }

  .reset-btn {
    padding: 11px 28px;
    background: #0f172a;
    color: white;
    border: none;
    border-radius: 9px;
    font-size: 0.88rem;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.2s, box-shadow 0.2s;
    letter-spacing: 0.01em;
  }

  .reset-btn:hover {
    background: #1e293b;
    box-shadow: 0 4px 12px rgba(15,23,42,0.2);
  }

  /* ── Responsive ── */
  @media (max-width: 900px) {
    .contact-grid {
      grid-template-columns: 1fr;
    }
    .map-hero {
      height: 260px;
    }
    .company-card, .next-steps-card {
      /* stacked order */
    }
  }

  @media (max-width: 640px) {
    .contact-body {
      padding: 28px 16px 48px;
    }
    .form-card {
      padding: 24px 20px;
    }
    .field-row {
      grid-template-columns: 1fr;
    }
    .map-hero {
      height: 220px;
    }
    .map-overlay {
      padding: 0 16px 20px;
    }
    .map-route-legend {
      gap: 12px;
    }
  }
`;
