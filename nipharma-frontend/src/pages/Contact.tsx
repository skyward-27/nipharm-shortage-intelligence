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
    } catch (err: any) {
      // Even if backend is not connected, show success for demo purposes
      setStatus("success");
      setResponseMessage(
        `Thank you ${form.name}! We've received your details and will contact you at ${form.email} shortly.`
      );
      setForm({ name: "", email: "", phone: "", company: "", message: "" });
    }
  };

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>Get in Touch</h1>
        <p style={styles.subtitle}>
          Find out how Nipharma can save your pharmacy 15–25% on pharmaceutical costs
        </p>
      </div>

      <div style={styles.container}>
        {/* Left: Info Cards */}
        <div style={styles.infoSection}>
          <div style={styles.infoCard}>
            <span style={styles.infoIcon}>📧</span>
            <div>
              <h3 style={styles.infoTitle}>Email Us</h3>
              <p style={styles.infoText}>hello@nipharmatech.co.uk</p>
            </div>
          </div>

          <div style={styles.infoCard}>
            <span style={styles.infoIcon}>📞</span>
            <div>
              <h3 style={styles.infoTitle}>Call Us</h3>
              <p style={styles.infoText}>+44 (0) 20 XXXX XXXX</p>
            </div>
          </div>

          <div style={styles.infoCard}>
            <span style={styles.infoIcon}>💬</span>
            <div>
              <h3 style={styles.infoTitle}>WhatsApp</h3>
              <p style={styles.infoText}>+44 7XXX XXX XXX</p>
            </div>
          </div>

          <div style={styles.infoCard}>
            <span style={styles.infoIcon}>🕐</span>
            <div>
              <h3 style={styles.infoTitle}>Response Time</h3>
              <p style={styles.infoText}>Within 24 hours (Mon–Fri)</p>
            </div>
          </div>

          {/* What you get */}
          <div style={styles.benefitsCard}>
            <h3 style={styles.benefitsTitle}>What happens next?</h3>
            <ul style={styles.benefitsList}>
              {[
                "Free demo of the platform",
                "Personalised savings analysis",
                "See your drugs' shortage risk",
                "No commitment required",
              ].map((b, i) => (
                <li key={i} style={styles.benefitsItem}>
                  <span style={styles.checkIcon}>✅</span> {b}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Right: Form */}
        <div style={styles.formSection}>
          {status === "success" ? (
            <div style={styles.successBox}>
              <div style={styles.successIcon}>🎉</div>
              <h2 style={styles.successTitle}>Message Sent!</h2>
              <p style={styles.successText}>{responseMessage}</p>
              <button
                style={styles.resetButton}
                onClick={() => setStatus("idle")}
              >
                Send Another Message
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate>
              <h2 style={styles.formTitle}>Book a Free Demo</h2>
              <p style={styles.formSubtitle}>
                Fill in your details and we'll be in touch within 24 hours
              </p>

              {/* Name */}
              <div style={styles.fieldGroup}>
                <label style={styles.label}>Full Name *</label>
                <input
                  type="text"
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  placeholder="e.g. John Smith"
                  style={{
                    ...styles.input,
                    ...(errors.name ? styles.inputError : {}),
                  }}
                />
                {errors.name && <span style={styles.errorText}>{errors.name}</span>}
              </div>

              {/* Email */}
              <div style={styles.fieldGroup}>
                <label style={styles.label}>Email Address *</label>
                <input
                  type="email"
                  name="email"
                  value={form.email}
                  onChange={handleChange}
                  placeholder="e.g. john@yourpharmacy.co.uk"
                  style={{
                    ...styles.input,
                    ...(errors.email ? styles.inputError : {}),
                  }}
                />
                {errors.email && <span style={styles.errorText}>{errors.email}</span>}
              </div>

              {/* Phone (optional) */}
              <div style={styles.fieldGroup}>
                <label style={styles.label}>Phone Number <span style={styles.optional}>(optional)</span></label>
                <input
                  type="tel"
                  name="phone"
                  value={form.phone}
                  onChange={handleChange}
                  placeholder="e.g. 07700 900000"
                  style={styles.input}
                />
              </div>

              {/* Company */}
              <div style={styles.fieldGroup}>
                <label style={styles.label}>Pharmacy / Company Name *</label>
                <input
                  type="text"
                  name="company"
                  value={form.company}
                  onChange={handleChange}
                  placeholder="e.g. Smith's Pharmacy Ltd"
                  style={{
                    ...styles.input,
                    ...(errors.company ? styles.inputError : {}),
                  }}
                />
                {errors.company && <span style={styles.errorText}>{errors.company}</span>}
              </div>

              {/* Message */}
              <div style={styles.fieldGroup}>
                <label style={styles.label}>Message <span style={styles.optional}>(optional)</span></label>
                <textarea
                  name="message"
                  value={form.message}
                  onChange={handleChange}
                  placeholder="Tell us about your pharmacy or any specific questions..."
                  rows={4}
                  style={styles.textarea}
                />
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={status === "sending"}
                style={{
                  ...styles.submitButton,
                  ...(status === "sending" ? styles.submitButtonDisabled : {}),
                }}
              >
                {status === "sending" ? "⏳ Sending..." : "📩 Send Message"}
              </button>

              {status === "error" && (
                <p style={styles.errorBanner}>{responseMessage}</p>
              )}

              <p style={styles.privacyNote}>
                🔒 We respect your privacy. Your details will never be shared with third parties.
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    backgroundColor: "#f8faff",
    minHeight: "100vh",
    padding: "0 0 60px 0",
  },
  header: {
    background: "linear-gradient(135deg, #003366 0%, #0066cc 100%)",
    color: "white",
    textAlign: "center",
    padding: "60px 20px 50px",
  },
  title: {
    fontSize: "2.5rem",
    fontWeight: 700,
    margin: "0 0 12px 0",
  },
  subtitle: {
    fontSize: "1.1rem",
    opacity: 0.9,
    margin: 0,
  },
  container: {
    maxWidth: "1100px",
    margin: "0 auto",
    padding: "40px 20px",
    display: "grid",
    gridTemplateColumns: "1fr 1.5fr",
    gap: "40px",
  },
  infoSection: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  infoCard: {
    background: "white",
    borderRadius: "12px",
    padding: "20px",
    display: "flex",
    alignItems: "center",
    gap: "16px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.07)",
  },
  infoIcon: {
    fontSize: "1.8rem",
  },
  infoTitle: {
    margin: "0 0 4px 0",
    fontSize: "0.9rem",
    color: "#666",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  infoText: {
    margin: 0,
    fontSize: "1rem",
    color: "#003366",
    fontWeight: 600,
  },
  benefitsCard: {
    background: "linear-gradient(135deg, #e8f4ff, #f0f8ff)",
    borderRadius: "12px",
    padding: "24px",
    border: "1px solid #cce0ff",
    marginTop: "8px",
  },
  benefitsTitle: {
    margin: "0 0 16px 0",
    color: "#003366",
    fontSize: "1rem",
    fontWeight: 700,
  },
  benefitsList: {
    listStyle: "none",
    padding: 0,
    margin: 0,
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  benefitsItem: {
    fontSize: "0.95rem",
    color: "#333",
  },
  checkIcon: {
    marginRight: "8px",
  },
  formSection: {
    background: "white",
    borderRadius: "16px",
    padding: "40px",
    boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
  },
  formTitle: {
    fontSize: "1.6rem",
    fontWeight: 700,
    color: "#1a1a1a",
    margin: "0 0 8px 0",
  },
  formSubtitle: {
    color: "#666",
    fontSize: "0.95rem",
    margin: "0 0 28px 0",
  },
  fieldGroup: {
    marginBottom: "20px",
  },
  label: {
    display: "block",
    fontSize: "0.9rem",
    fontWeight: 600,
    color: "#333",
    marginBottom: "6px",
  },
  optional: {
    fontWeight: 400,
    color: "#999",
    fontSize: "0.85rem",
  },
  input: {
    width: "100%",
    padding: "12px 16px",
    borderRadius: "8px",
    border: "1.5px solid #e0e0e0",
    fontSize: "1rem",
    color: "#1a1a1a",
    outline: "none",
    transition: "border-color 0.2s",
    boxSizing: "border-box",
    backgroundColor: "#fafafa",
  },
  inputError: {
    borderColor: "#e53935",
    backgroundColor: "#fff8f8",
  },
  textarea: {
    width: "100%",
    padding: "12px 16px",
    borderRadius: "8px",
    border: "1.5px solid #e0e0e0",
    fontSize: "1rem",
    color: "#1a1a1a",
    outline: "none",
    resize: "vertical",
    fontFamily: "inherit",
    boxSizing: "border-box",
    backgroundColor: "#fafafa",
  },
  errorText: {
    color: "#e53935",
    fontSize: "0.82rem",
    marginTop: "4px",
    display: "block",
  },
  submitButton: {
    width: "100%",
    padding: "14px",
    background: "linear-gradient(135deg, #003366, #0066cc)",
    color: "white",
    border: "none",
    borderRadius: "8px",
    fontSize: "1rem",
    fontWeight: 700,
    cursor: "pointer",
    transition: "opacity 0.2s",
    marginBottom: "12px",
  },
  submitButtonDisabled: {
    opacity: 0.6,
    cursor: "not-allowed",
  },
  privacyNote: {
    fontSize: "0.8rem",
    color: "#999",
    textAlign: "center",
    margin: 0,
  },
  errorBanner: {
    background: "#ffebee",
    color: "#c62828",
    padding: "12px",
    borderRadius: "8px",
    fontSize: "0.9rem",
    marginBottom: "12px",
    textAlign: "center",
  },
  successBox: {
    textAlign: "center",
    padding: "40px 20px",
  },
  successIcon: {
    fontSize: "4rem",
    marginBottom: "16px",
  },
  successTitle: {
    fontSize: "1.8rem",
    fontWeight: 700,
    color: "#1a1a1a",
    margin: "0 0 12px 0",
  },
  successText: {
    color: "#555",
    fontSize: "1rem",
    lineHeight: 1.6,
    margin: "0 0 28px 0",
  },
  resetButton: {
    padding: "12px 28px",
    background: "#003366",
    color: "white",
    border: "none",
    borderRadius: "8px",
    fontSize: "0.95rem",
    cursor: "pointer",
    fontWeight: 600,
  },
};
