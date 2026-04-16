import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

interface Drug {
  id: string;
  name: string;
  price: number;
}

interface BulkTier {
  id: string;
  label: string;
  range: string;
  discount: number;
}

interface BasketItem {
  drug: Drug;
  units: number;
  tier: BulkTier;
  monthlyStandard: number;
  monthlyBulk: number;
  monthlySaving: number;
  annualSaving: number;
}

const DRUGS: Drug[] = [
  { id: "amox-21", name: "Amoxicillin 500mg caps x21", price: 1.20 },
  { id: "amox-100", name: "Amoxicillin 500mg caps x100", price: 4.80 },
  { id: "metf-28", name: "Metformin 500mg tabs x28", price: 0.85 },
  { id: "metf-100", name: "Metformin 500mg tabs x100", price: 2.40 },
  { id: "omep-28", name: "Omeprazole 20mg caps x28", price: 1.50 },
  { id: "omep-100", name: "Omeprazole 20mg caps x100", price: 4.20 },
  { id: "lisin-28", name: "Lisinopril 10mg tabs x28", price: 0.92 },
  { id: "amlo-28", name: "Amlodipine 5mg tabs x28", price: 0.87 },
  { id: "ator-28", name: "Atorvastatin 40mg tabs x28", price: 1.15 },
  { id: "para-32", name: "Paracetamol 500mg tabs x32", price: 0.50 },
  { id: "para-100", name: "Paracetamol 500mg tabs x100", price: 1.20 },
  { id: "ibup-24", name: "Ibuprofen 400mg tabs x24", price: 0.75 },
  { id: "rami-28", name: "Ramipril 5mg caps x28", price: 1.08 },
  { id: "lans-28", name: "Lansoprazole 30mg caps x28", price: 1.45 },
  { id: "sert-28", name: "Sertraline 50mg tabs x28", price: 1.22 },
  { id: "levo-28", name: "Levothyroxine 50mcg tabs x28", price: 0.95 },
  { id: "salb-inh", name: "Salbutamol 100mcg inhaler", price: 2.75 },
  { id: "coam-21", name: "Co-amoxiclav 500/125mg tabs x21", price: 2.80 },
  { id: "trim-14", name: "Trimethoprim 200mg tabs x14", price: 0.95 },
  { id: "furo-28", name: "Furosemide 40mg tabs x28", price: 0.65 },
];

const TIERS: BulkTier[] = [
  { id: "standard", label: "Standard", range: "1–49 units", discount: 0 },
  { id: "bronze", label: "Bronze", range: "50–99 units", discount: 8 },
  { id: "silver", label: "Silver", range: "100–249 units", discount: 15 },
  { id: "gold", label: "Gold", range: "250+ units", discount: 22 },
];

function formatGBP(amount: number): string {
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

function formatGBPShort(amount: number): string {
  if (amount >= 1000) {
    return `£${(amount / 1000).toFixed(1)}k`;
  }
  return formatGBP(amount);
}

export default function Calculator() {
  const navigate = useNavigate();

  const [selectedDrugId, setSelectedDrugId] = useState<string>(DRUGS[0].id);
  const [units, setUnits] = useState<number>(100);
  const [unitsInput, setUnitsInput] = useState<string>("100");
  const [selectedTierId, setSelectedTierId] = useState<string>("silver");
  const [basket, setBasket] = useState<BasketItem[]>([]);
  const [savingsAnimKey, setSavingsAnimKey] = useState<number>(0);
  const prevAnnualRef = useRef<number>(0);

  const selectedDrug = DRUGS.find((d) => d.id === selectedDrugId) || DRUGS[0];
  const selectedTier = TIERS.find((t) => t.id === selectedTierId) || TIERS[0];

  const monthlyStandard = selectedDrug.price * units;
  const discountFactor = 1 - selectedTier.discount / 100;
  const monthlyBulk = monthlyStandard * discountFactor;
  const monthlySaving = monthlyStandard - monthlyBulk;
  const savingPercent = selectedTier.discount;
  const annualSaving = monthlySaving * 12;

  useEffect(() => {
    if (annualSaving !== prevAnnualRef.current) {
      setSavingsAnimKey((k) => k + 1);
      prevAnnualRef.current = annualSaving;
    }
  }, [annualSaving]);

  const handleUnitsSlider = (value: number) => {
    setUnits(value);
    setUnitsInput(String(value));
  };

  const handleUnitsTextInput = (raw: string) => {
    setUnitsInput(raw);
    const parsed = parseInt(raw, 10);
    if (!isNaN(parsed) && parsed >= 10 && parsed <= 1000) {
      setUnits(parsed);
    }
  };

  const handleUnitsBlur = () => {
    const parsed = parseInt(unitsInput, 10);
    if (isNaN(parsed) || parsed < 10) {
      setUnits(10);
      setUnitsInput("10");
    } else if (parsed > 1000) {
      setUnits(1000);
      setUnitsInput("1000");
    } else {
      setUnitsInput(String(parsed));
    }
  };

  const handleAddToBasket = () => {
    setBasket((prev) => {
      const existing = prev.findIndex((item) => item.drug.id === selectedDrug.id);
      const newItem: BasketItem = {
        drug: selectedDrug,
        units,
        tier: selectedTier,
        monthlyStandard,
        monthlyBulk,
        monthlySaving,
        annualSaving,
      };
      if (existing !== -1) {
        const updated = [...prev];
        updated[existing] = newItem;
        return updated;
      }
      return [...prev, newItem];
    });
  };

  const handleRemoveFromBasket = (drugId: string) => {
    setBasket((prev) => prev.filter((item) => item.drug.id !== drugId));
  };

  const totalAnnualSaving = basket.reduce((sum, item) => sum + item.annualSaving, 0);
  const totalMonthlySaving = basket.reduce((sum, item) => sum + item.monthlySaving, 0);

  // Slider fill percentage
  const sliderFill = ((units - 10) / (1000 - 10)) * 100;

  // Tier threshold markers on slider track (50, 100, 250 out of 1000)
  const marker50 = ((50 - 10) / (1000 - 10)) * 100;
  const marker100 = ((100 - 10) / (1000 - 10)) * 100;
  const marker250 = ((250 - 10) / (1000 - 10)) * 100;

  return (
    <div className="calc-page">
      {/* Dark Hero Header */}
      <div className="calc-hero">
        <div className="calc-hero-inner">
          <div className="hero-text">
            <div className="hero-eyebrow">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2.5">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
              NHS Drug Tariff · Live Pricing
            </div>
            <h1 className="hero-title">Bulk Savings Calculator</h1>
            <p className="hero-subtitle">
              Find out exactly how much your pharmacy could save ordering in bulk — using live NHS Drug Tariff prices.
            </p>
          </div>
          <div key={savingsAnimKey} className="hero-kpi-card">
            <div className="kpi-label">Projected Annual Saving</div>
            <div className={`kpi-amount ${annualSaving > 0 ? "kpi-amount-active" : "kpi-amount-zero"}`}>
              {formatGBP(annualSaving)}
            </div>
            <div className="kpi-sub">
              {annualSaving > 0
                ? `${formatGBP(monthlySaving)}/mo · ${selectedTier.discount}% off ${selectedTier.label} tier`
                : "Select a tier to see savings"}
            </div>
            {annualSaving > 0 && (
              <div className="kpi-bar-wrap">
                <div className="kpi-bar-track">
                  <div
                    className="kpi-bar-fill"
                    style={{ width: `${Math.min(selectedTier.discount / 22 * 100, 100)}%` }}
                  />
                </div>
                <span className="kpi-bar-pct">{selectedTier.discount}% off</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="calc-container">
        <div className="calc-layout">

          {/* Left panel — inputs */}
          <div className="calc-inputs-panel">

            {/* Drug Selector */}
            <div className="calc-card">
              <div className="card-step-label">
                <span className="step-number">1</span>
                <h2 className="card-title">Select Drug</h2>
              </div>
              <div className="select-wrap">
                <select
                  className="drug-select"
                  value={selectedDrugId}
                  onChange={(e) => setSelectedDrugId(e.target.value)}
                >
                  {DRUGS.map((drug) => (
                    <option key={drug.id} value={drug.id}>
                      {drug.name}
                    </option>
                  ))}
                </select>
                <div className="select-arrow">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </div>
              </div>
              <div className="drug-price-tag">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2">
                  <line x1="12" y1="1" x2="12" y2="23" />
                  <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                </svg>
                NHS Drug Tariff unit price:
                <strong className="price-highlight">{formatGBP(selectedDrug.price)}</strong>
              </div>
            </div>

            {/* Monthly Usage */}
            <div className="calc-card">
              <div className="card-step-label">
                <span className="step-number">2</span>
                <h2 className="card-title">Monthly Usage</h2>
              </div>
              <div className="usage-value-row">
                <input
                  type="number"
                  min={10}
                  max={1000}
                  value={unitsInput}
                  onChange={(e) => handleUnitsTextInput(e.target.value)}
                  onBlur={handleUnitsBlur}
                  className="usage-number-input"
                />
                <span className="usage-unit-label">units / month</span>
              </div>
              <div className="slider-container">
                <div className="slider-track-wrap">
                  <div className="slider-track-bg" />
                  <div className="slider-track-fill" style={{ width: `${sliderFill}%` }} />
                  {/* Threshold markers */}
                  <div className="slider-marker" style={{ left: `${marker50}%` }} title="50 units — Bronze threshold" />
                  <div className="slider-marker" style={{ left: `${marker100}%` }} title="100 units — Silver threshold" />
                  <div className="slider-marker" style={{ left: `${marker250}%` }} title="250 units — Gold threshold" />
                  <input
                    type="range"
                    min={10}
                    max={1000}
                    step={10}
                    value={units}
                    onChange={(e) => handleUnitsSlider(parseInt(e.target.value, 10))}
                    className="usage-slider"
                  />
                </div>
                <div className="slider-tier-labels">
                  <span style={{ left: `${marker50}%` }}>50</span>
                  <span style={{ left: `${marker100}%` }}>100</span>
                  <span style={{ left: `${marker250}%` }}>250</span>
                </div>
              </div>
              <div className="slider-range-labels">
                <span>10</span>
                <span>1,000</span>
              </div>
            </div>

            {/* Bulk Tier Selector */}
            <div className="calc-card">
              <div className="card-step-label">
                <span className="step-number">3</span>
                <h2 className="card-title">Choose Bulk Tier</h2>
              </div>
              <div className="tier-cards">
                {TIERS.map((tier) => {
                  const isActive = selectedTierId === tier.id;
                  const tierColors: Record<string, string> = {
                    standard: "#64748b",
                    bronze: "#f59e0b",
                    silver: "#94a3b8",
                    gold: "#eab308",
                  };
                  return (
                    <button
                      key={tier.id}
                      className={`tier-card tier-card-${tier.id} ${isActive ? "tier-card-active" : ""}`}
                      onClick={() => setSelectedTierId(tier.id)}
                      type="button"
                      style={isActive ? { borderColor: tierColors[tier.id] } : undefined}
                    >
                      <input
                        type="radio"
                        name="bulk-tier"
                        value={tier.id}
                        checked={isActive}
                        onChange={() => setSelectedTierId(tier.id)}
                        className="tier-radio-hidden"
                      />
                      <div className="tier-card-top">
                        <span className="tier-card-name">{tier.label}</span>
                        <span
                          className={`tier-discount-pill ${tier.discount === 0 ? "tier-discount-none" : "tier-discount-active"}`}
                          style={tier.discount > 0 ? { background: `${tierColors[tier.id]}22`, color: tierColors[tier.id] } : undefined}
                        >
                          {tier.discount === 0 ? "No discount" : `-${tier.discount}%`}
                        </span>
                      </div>
                      <span className="tier-card-range">{tier.range}</span>
                      {isActive && (
                        <div className="tier-card-check">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Add to Basket */}
            <button className="add-basket-btn" onClick={handleAddToBasket} type="button">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <path d="M16 10a4 4 0 0 1-8 0" />
              </svg>
              Add to Savings Basket
            </button>
          </div>

          {/* Right panel — live results */}
          <div className="calc-results-panel">
            <div className="results-card">
              <div className="results-header">
                <h2 className="results-title">Live Savings Estimate</h2>
                <span className="results-drug-badge">{selectedDrug.name.split(" ").slice(0, 2).join(" ")}</span>
              </div>

              {/* Comparison bar */}
              <div className="comparison-section">
                <div className="comparison-label-row">
                  <span className="comparison-label">You pay</span>
                  <span className="comparison-label">Standard</span>
                </div>
                <div className="comparison-bars">
                  <div className="comp-bar-row">
                    <span className="comp-bar-tag comp-bar-tag-blue">Bulk</span>
                    <div className="comp-bar-track">
                      <div
                        className="comp-bar-fill comp-bar-blue"
                        style={{ width: `${(monthlyBulk / monthlyStandard) * 100}%` }}
                      />
                    </div>
                    <span className="comp-bar-val">{formatGBP(monthlyBulk)}</span>
                  </div>
                  <div className="comp-bar-row">
                    <span className="comp-bar-tag comp-bar-tag-neutral">Std</span>
                    <div className="comp-bar-track">
                      <div className="comp-bar-fill comp-bar-neutral" style={{ width: "100%" }} />
                    </div>
                    <span className="comp-bar-val comp-bar-val-neutral">{formatGBP(monthlyStandard)}</span>
                  </div>
                </div>
              </div>

              {/* Key metrics */}
              <div className="metrics-grid">
                <div className="metric-cell">
                  <div className="metric-icon-wrap metric-green">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5">
                      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
                      <polyline points="17 6 23 6 23 12" />
                    </svg>
                  </div>
                  <div className="metric-val metric-val-green">{formatGBP(monthlySaving)}</div>
                  <div className="metric-desc">Monthly saving</div>
                  {savingPercent > 0 && <div className="metric-badge">{savingPercent}% off</div>}
                </div>
                <div className="metric-cell">
                  <div className="metric-icon-wrap metric-green">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5">
                      <rect x="3" y="3" width="18" height="18" rx="2" />
                      <path d="M3 9h18M9 21V9" />
                    </svg>
                  </div>
                  <div className="metric-val metric-val-green">{formatGBP(annualSaving)}</div>
                  <div className="metric-desc">Annual saving</div>
                </div>
                <div className="metric-cell">
                  <div className="metric-icon-wrap metric-blue">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2.5">
                      <line x1="12" y1="1" x2="12" y2="23" />
                      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                    </svg>
                  </div>
                  <div className="metric-val metric-val-blue">{formatGBP(monthlyBulk)}</div>
                  <div className="metric-desc">Bulk monthly cost</div>
                </div>
                <div className="metric-cell">
                  <div className="metric-icon-wrap metric-amber">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2.5">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                  </div>
                  <div className="metric-val metric-val-amber">
                    {annualSaving > 0 ? `${Math.ceil(monthlyBulk / monthlySaving)} mo` : "—"}
                  </div>
                  <div className="metric-desc">Payback period</div>
                </div>
              </div>

              {/* Savings banner */}
              <div
                key={savingsAnimKey}
                className={`savings-banner ${annualSaving > 0 ? "savings-banner-active" : "savings-banner-zero"}`}
              >
                {annualSaving > 0 ? (
                  <>
                    <div className="banner-icon-wrap">
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                        <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                      </svg>
                    </div>
                    <div className="banner-text">
                      Save <span className="banner-amount">{formatGBP(annualSaving)}</span> per year on this drug alone
                    </div>
                  </>
                ) : (
                  <>
                    <div className="banner-icon-wrap banner-icon-muted">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2">
                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                      </svg>
                    </div>
                    <div className="banner-text banner-text-muted">Select a bulk tier to see your savings</div>
                  </>
                )}
              </div>

              {/* Tier comparison table */}
              <div className="tier-compare">
                <h3 className="compare-title">All tiers at current usage</h3>
                <table className="compare-table">
                  <thead>
                    <tr>
                      <th>Tier</th>
                      <th>Discount</th>
                      <th>Monthly</th>
                      <th>Annual Saving</th>
                    </tr>
                  </thead>
                  <tbody>
                    {TIERS.map((tier) => {
                      const bulkPrice = monthlyStandard * (1 - tier.discount / 100);
                      const aSaving = (monthlyStandard - bulkPrice) * 12;
                      return (
                        <tr
                          key={tier.id}
                          className={selectedTierId === tier.id ? "compare-row-active" : ""}
                          onClick={() => setSelectedTierId(tier.id)}
                          style={{ cursor: "pointer" }}
                        >
                          <td>
                            <span className={`tier-dot tier-dot-${tier.id}`} />
                            {tier.label}
                          </td>
                          <td>{tier.discount === 0 ? "—" : `-${tier.discount}%`}</td>
                          <td>{formatGBP(bulkPrice)}</td>
                          <td className={aSaving > 0 ? "compare-saving" : "compare-zero"}>
                            {aSaving > 0 ? formatGBP(aSaving) : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        {/* Multi-drug Basket Summary */}
        {basket.length > 0 && (
          <div className="basket-section">
            <div className="basket-header-row">
              <div className="basket-header-left">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2">
                  <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <path d="M16 10a4 4 0 0 1-8 0" />
                </svg>
                <h2 className="basket-title">Savings Basket</h2>
                <span className="basket-count">{basket.length} drug{basket.length !== 1 ? "s" : ""}</span>
              </div>
              <div className="basket-totals-preview">
                <span className="basket-total-label">Total annual</span>
                <span className="basket-total-val">{formatGBP(totalAnnualSaving)}</span>
              </div>
            </div>

            <div className="basket-table-wrap">
              <table className="basket-table">
                <thead>
                  <tr>
                    <th>Drug</th>
                    <th>Units/mo</th>
                    <th>Tier</th>
                    <th>Std. Monthly</th>
                    <th>Bulk Monthly</th>
                    <th>Monthly Saving</th>
                    <th>Annual Saving</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {basket.map((item, idx) => (
                    <tr key={item.drug.id} className={idx % 2 === 0 ? "basket-row-even" : "basket-row-odd"}>
                      <td className="basket-drug-name">{item.drug.name}</td>
                      <td className="basket-td-num">{item.units.toLocaleString()}</td>
                      <td>
                        <span className={`tier-pill tier-pill-${item.tier.id}`}>
                          {item.tier.label}
                        </span>
                      </td>
                      <td className="basket-td-num">{formatGBP(item.monthlyStandard)}</td>
                      <td className="basket-td-num">{formatGBP(item.monthlyBulk)}</td>
                      <td className="table-saving">{formatGBP(item.monthlySaving)}</td>
                      <td className="table-annual">{formatGBP(item.annualSaving)}</td>
                      <td>
                        <button
                          className="remove-btn"
                          onClick={() => handleRemoveFromBasket(item.drug.id)}
                          title="Remove from basket"
                          type="button"
                        >
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <line x1="18" y1="6" x2="6" y2="18" />
                            <line x1="6" y1="6" x2="18" y2="18" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="basket-totals-row">
                    <td colSpan={5} className="totals-label">Total across all drugs</td>
                    <td className="table-saving total-cell">{formatGBP(totalMonthlySaving)}/mo</td>
                    <td className="table-annual total-cell">{formatGBP(totalAnnualSaving)}/yr</td>
                    <td></td>
                  </tr>
                </tfoot>
              </table>
            </div>

            {/* Total savings summary */}
            <div className="total-banner">
              <div className="total-banner-inner">
                <div className="total-icon-wrap">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="1.8">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 6v2M12 16v2M8 12h8M8.5 8.5l1.5 1.5M14 14l1.5 1.5M8.5 15.5L10 14M14 10l1.5-1.5" />
                    <path d="M12 8v8M9 10.5h6M9 13.5h6" />
                  </svg>
                </div>
                <div className="total-text">
                  <div className="total-headline">Total potential annual saving across your basket</div>
                  <div className="total-amount">{formatGBP(totalAnnualSaving)}</div>
                  <div className="total-sub">
                    {formatGBPShort(totalMonthlySaving)}/month · {formatGBPShort(totalAnnualSaving)}/year
                  </div>
                </div>
                <div className="total-breakdown">
                  {basket.slice(0, 3).map((item) => (
                    <div key={item.drug.id} className="total-breakdown-row">
                      <span className={`tier-pill tier-pill-${item.tier.id}`}>{item.tier.label}</span>
                      <span className="breakdown-drug">{item.drug.name.split(" ").slice(0, 2).join(" ")}</span>
                      <span className="breakdown-saving">{formatGBP(item.annualSaving)}/yr</span>
                    </div>
                  ))}
                  {basket.length > 3 && <div className="breakdown-more">+{basket.length - 3} more</div>}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* CTA Section */}
        <div className="cta-section">
          <div className="cta-inner">
            <div className="cta-icon-wrap">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="1.8">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <div className="cta-text">
              <h2 className="cta-title">Ready to lock in these savings?</h2>
              <p className="cta-desc">
                Our team will build a fully personalised bulk procurement plan based on your pharmacy's dispensing data.
              </p>
            </div>
            <button className="cta-btn" onClick={() => navigate("/contact")} type="button">
              Get Your Custom Bulk Quote
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <style>{CSS}</style>
    </div>
  );
}

const CSS = `
  .calc-page {
    background: #f8fafc;
    min-height: 100vh;
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
  }

  /* ── Hero ── */
  .calc-hero {
    background: #0f172a;
    padding: 52px 0 48px;
    border-bottom: 1px solid #1e293b;
  }

  .calc-hero-inner {
    max-width: 1300px;
    margin: 0 auto;
    padding: 0 28px;
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 40px;
    align-items: center;
  }

  .hero-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #3b82f6;
    background: rgba(59,130,246,0.1);
    border: 1px solid rgba(59,130,246,0.25);
    padding: 4px 12px;
    border-radius: 20px;
    margin-bottom: 16px;
  }

  .hero-title {
    font-size: 2.6rem;
    font-weight: 800;
    color: #f8fafc;
    margin: 0 0 12px;
    letter-spacing: -0.03em;
    line-height: 1.15;
  }

  .hero-subtitle {
    font-size: 1.05rem;
    color: #94a3b8;
    margin: 0;
    max-width: 540px;
    line-height: 1.65;
  }

  /* Hero KPI card */
  .hero-kpi-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 24px 28px;
    min-width: 260px;
    animation: kpiPop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  @keyframes kpiPop {
    0% { transform: scale(0.94); opacity: 0.5; }
    100% { transform: scale(1); opacity: 1; }
  }

  .kpi-label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748b;
    margin-bottom: 8px;
  }

  .kpi-amount {
    font-size: 2.4rem;
    font-weight: 800;
    letter-spacing: -0.04em;
    line-height: 1;
    margin-bottom: 8px;
    transition: color 0.3s;
  }

  .kpi-amount-active { color: #10b981; }
  .kpi-amount-zero { color: #475569; }

  .kpi-sub {
    font-size: 0.8rem;
    color: #64748b;
    margin-bottom: 14px;
    line-height: 1.4;
  }

  .kpi-bar-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .kpi-bar-track {
    flex: 1;
    height: 4px;
    background: #334155;
    border-radius: 2px;
    overflow: hidden;
  }

  .kpi-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #10b981, #34d399);
    border-radius: 2px;
    transition: width 0.4s ease;
  }

  .kpi-bar-pct {
    font-size: 0.75rem;
    font-weight: 700;
    color: #10b981;
    white-space: nowrap;
  }

  /* ── Layout ── */
  .calc-container {
    max-width: 1300px;
    margin: 0 auto;
    padding: 36px 28px 60px;
  }

  .calc-layout {
    display: grid;
    grid-template-columns: 440px 1fr;
    gap: 28px;
    margin-bottom: 36px;
    align-items: start;
  }

  /* ── Cards ── */
  .calc-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 22px 24px;
    margin-bottom: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  }

  .card-step-label {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
  }

  .step-number {
    width: 26px;
    height: 26px;
    background: #0f172a;
    color: #f8fafc;
    border-radius: 50%;
    font-size: 0.75rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .card-title {
    font-size: 0.85rem;
    font-weight: 700;
    color: #0f172a;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin: 0;
  }

  /* ── Drug selector ── */
  .select-wrap {
    position: relative;
    margin-bottom: 12px;
  }

  .drug-select {
    width: 100%;
    padding: 11px 42px 11px 14px;
    border: 1.5px solid #cbd5e1;
    border-radius: 9px;
    font-size: 0.92rem;
    color: #0f172a;
    background: #f8fafc;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    transition: border-color 0.2s, box-shadow 0.2s;
    font-weight: 500;
  }

  .drug-select:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.12);
    background: white;
  }

  .select-arrow {
    position: absolute;
    right: 13px;
    top: 50%;
    transform: translateY(-50%);
    color: #64748b;
    pointer-events: none;
    display: flex;
    align-items: center;
  }

  .drug-price-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.83rem;
    color: #475569;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    padding: 6px 12px;
    border-radius: 7px;
  }

  .price-highlight {
    color: #1d4ed8;
    font-weight: 700;
    margin-left: 2px;
  }

  /* ── Slider ── */
  .usage-value-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 18px;
  }

  .usage-number-input {
    width: 88px;
    padding: 10px 12px;
    border: 1.5px solid #cbd5e1;
    border-radius: 9px;
    font-size: 1.25rem;
    font-weight: 800;
    color: #0f172a;
    text-align: center;
    background: #f8fafc;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .usage-number-input:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.12);
    background: white;
  }

  .usage-unit-label {
    font-size: 0.88rem;
    color: #64748b;
    font-weight: 500;
  }

  .slider-container {
    position: relative;
    padding-bottom: 28px;
  }

  .slider-track-wrap {
    position: relative;
    height: 20px;
    display: flex;
    align-items: center;
    margin-bottom: 4px;
  }

  .slider-track-bg {
    position: absolute;
    left: 0; right: 0;
    height: 4px;
    background: #e2e8f0;
    border-radius: 2px;
  }

  .slider-track-fill {
    position: absolute;
    left: 0;
    height: 4px;
    background: linear-gradient(90deg, #3b82f6, #60a5fa);
    border-radius: 2px;
    pointer-events: none;
    transition: width 0.1s;
  }

  .slider-marker {
    position: absolute;
    width: 2px;
    height: 10px;
    background: #f59e0b;
    border-radius: 1px;
    transform: translateX(-50%);
    z-index: 1;
  }

  .usage-slider {
    position: absolute;
    left: 0; right: 0;
    width: 100%;
    height: 20px;
    opacity: 0;
    cursor: pointer;
    margin: 0;
    padding: 0;
    z-index: 2;
  }

  .slider-tier-labels {
    position: relative;
    height: 18px;
  }

  .slider-tier-labels span {
    position: absolute;
    transform: translateX(-50%);
    font-size: 0.68rem;
    font-weight: 700;
    color: #f59e0b;
    top: 0;
  }

  .slider-range-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.72rem;
    color: #94a3b8;
    font-weight: 500;
    margin-top: 2px;
  }

  /* ── Tier Cards ── */
  .tier-cards {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .tier-card {
    position: relative;
    padding: 14px 14px 12px;
    border: 1.5px solid #e2e8f0;
    border-radius: 11px;
    background: white;
    cursor: pointer;
    text-align: left;
    transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .tier-card:hover {
    border-color: #93c5fd;
    background: #f0f9ff;
    box-shadow: 0 2px 8px rgba(59,130,246,0.1);
  }

  .tier-card-active {
    background: #f0f9ff;
    box-shadow: 0 2px 10px rgba(59,130,246,0.15);
  }

  .tier-radio-hidden {
    position: absolute;
    opacity: 0;
    pointer-events: none;
  }

  .tier-card-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
  }

  .tier-card-name {
    font-size: 0.9rem;
    font-weight: 700;
    color: #0f172a;
  }

  .tier-discount-pill {
    font-size: 0.7rem;
    font-weight: 800;
    padding: 2px 8px;
    border-radius: 20px;
    white-space: nowrap;
  }

  .tier-discount-none {
    background: #f1f5f9;
    color: #94a3b8;
  }

  .tier-discount-active {
    background: rgba(16,185,129,0.12);
    color: #059669;
  }

  .tier-card-range {
    font-size: 0.75rem;
    color: #64748b;
    font-weight: 500;
  }

  .tier-card-check {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 18px;
    height: 18px;
    background: #3b82f6;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
  }

  /* tier gold/bronze/silver/standard accent */
  .tier-card-gold.tier-card-active { background: #fefce8; }
  .tier-card-bronze.tier-card-active { background: #fff7ed; }
  .tier-card-silver.tier-card-active { background: #f8fafc; }

  /* ── Add basket btn ── */
  .add-basket-btn {
    width: 100%;
    padding: 15px 20px;
    background: #0f172a;
    color: white;
    border: none;
    border-radius: 11px;
    font-size: 0.95rem;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    transition: background 0.2s, box-shadow 0.2s, transform 0.15s;
    letter-spacing: 0.01em;
  }

  .add-basket-btn:hover {
    background: #1e293b;
    box-shadow: 0 4px 16px rgba(15,23,42,0.25);
    transform: translateY(-1px);
  }

  .add-basket-btn:active {
    transform: translateY(0);
  }

  /* ── Results card ── */
  .results-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 26px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    position: sticky;
    top: 84px;
  }

  .results-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid #f1f5f9;
  }

  .results-title {
    font-size: 1rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 0.8rem;
  }

  .results-drug-badge {
    font-size: 0.72rem;
    font-weight: 600;
    color: #475569;
    background: #f1f5f9;
    padding: 4px 10px;
    border-radius: 20px;
    border: 1px solid #e2e8f0;
  }

  /* ── Comparison bars ── */
  .comparison-section {
    margin-bottom: 22px;
  }

  .comparison-label-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #94a3b8;
    margin-bottom: 8px;
  }

  .comparison-bars {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .comp-bar-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .comp-bar-tag {
    font-size: 0.68rem;
    font-weight: 700;
    width: 34px;
    text-align: center;
    padding: 2px 6px;
    border-radius: 4px;
    flex-shrink: 0;
  }

  .comp-bar-tag-blue {
    background: rgba(59,130,246,0.12);
    color: #3b82f6;
  }

  .comp-bar-tag-neutral {
    background: #f1f5f9;
    color: #94a3b8;
  }

  .comp-bar-track {
    flex: 1;
    height: 8px;
    background: #f1f5f9;
    border-radius: 4px;
    overflow: hidden;
  }

  .comp-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.35s ease;
  }

  .comp-bar-blue {
    background: linear-gradient(90deg, #3b82f6, #60a5fa);
  }

  .comp-bar-neutral {
    background: #cbd5e1;
  }

  .comp-bar-val {
    font-size: 0.82rem;
    font-weight: 700;
    color: #3b82f6;
    width: 70px;
    text-align: right;
    flex-shrink: 0;
  }

  .comp-bar-val-neutral {
    color: #94a3b8;
  }

  /* ── Metrics grid ── */
  .metrics-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 20px;
  }

  .metric-cell {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .metric-icon-wrap {
    width: 28px;
    height: 28px;
    border-radius: 7px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 4px;
  }

  .metric-green { background: rgba(16,185,129,0.1); }
  .metric-blue { background: rgba(59,130,246,0.1); }
  .metric-amber { background: rgba(245,158,11,0.1); }

  .metric-val {
    font-size: 1.15rem;
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.02em;
  }

  .metric-val-green { color: #10b981; }
  .metric-val-blue { color: #3b82f6; }
  .metric-val-amber { color: #f59e0b; }

  .metric-desc {
    font-size: 0.72rem;
    color: #94a3b8;
    font-weight: 500;
  }

  .metric-badge {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 800;
    background: rgba(16,185,129,0.12);
    color: #059669;
    padding: 1px 6px;
    border-radius: 10px;
    margin-top: 2px;
    width: fit-content;
  }

  /* ── Savings banner ── */
  .savings-banner {
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    animation: bannerPop 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .savings-banner-active {
    background: rgba(16,185,129,0.07);
    border: 1px solid rgba(16,185,129,0.25);
  }

  .savings-banner-zero {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
  }

  @keyframes bannerPop {
    0% { transform: scale(0.96); opacity: 0.5; }
    100% { transform: scale(1); opacity: 1; }
  }

  .banner-icon-wrap {
    width: 36px;
    height: 36px;
    background: rgba(16,185,129,0.1);
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .banner-icon-muted {
    background: #f1f5f9;
  }

  .banner-text {
    font-size: 0.88rem;
    color: #334155;
    line-height: 1.4;
    font-weight: 500;
  }

  .banner-text-muted {
    color: #94a3b8;
  }

  .banner-amount {
    font-size: 1.1rem;
    font-weight: 800;
    color: #059669;
  }

  /* ── Tier compare ── */
  .tier-compare {
    border-top: 1px solid #f1f5f9;
    padding-top: 18px;
  }

  .compare-title {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
    margin: 0 0 10px;
  }

  .compare-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.83rem;
  }

  .compare-table th {
    text-align: left;
    padding: 5px 8px;
    color: #94a3b8;
    font-weight: 600;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid #f1f5f9;
  }

  .compare-table td {
    padding: 8px 8px;
    color: #475569;
    border-bottom: 1px solid #f8fafc;
  }

  .compare-table td:first-child {
    display: flex;
    align-items: center;
    gap: 7px;
    font-weight: 600;
    color: #334155;
  }

  .tier-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .tier-dot-standard { background: #94a3b8; }
  .tier-dot-bronze { background: #f59e0b; }
  .tier-dot-silver { background: #cbd5e1; }
  .tier-dot-gold { background: #eab308; }

  .compare-row-active td {
    background: #eff6ff;
    font-weight: 700;
    color: #1d4ed8;
  }

  .compare-saving {
    color: #059669;
    font-weight: 700;
  }

  .compare-zero {
    color: #cbd5e1;
  }

  /* ── Basket Section ── */
  .basket-section {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 26px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    margin-bottom: 28px;
  }

  .basket-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid #f1f5f9;
  }

  .basket-header-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .basket-title {
    font-size: 1rem;
    font-weight: 800;
    color: #0f172a;
    margin: 0;
    letter-spacing: -0.01em;
  }

  .basket-count {
    background: #3b82f6;
    color: white;
    font-size: 0.72rem;
    font-weight: 800;
    padding: 3px 10px;
    border-radius: 20px;
    letter-spacing: 0.02em;
  }

  .basket-totals-preview {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
  }

  .basket-total-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #94a3b8;
  }

  .basket-total-val {
    font-size: 1.3rem;
    font-weight: 800;
    color: #10b981;
    letter-spacing: -0.03em;
  }

  .basket-table-wrap {
    overflow-x: auto;
    margin-bottom: 20px;
    border-radius: 9px;
    border: 1px solid #e2e8f0;
  }

  .basket-table {
    width: 100%;
    border-collapse: collapse;
    min-width: 700px;
    font-size: 0.86rem;
  }

  .basket-table th {
    background: #f8fafc;
    padding: 10px 14px;
    text-align: left;
    font-weight: 700;
    color: #64748b;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-bottom: 1px solid #e2e8f0;
    white-space: nowrap;
  }

  .basket-table td {
    padding: 12px 14px;
    border-bottom: 1px solid #f1f5f9;
    color: #334155;
    vertical-align: middle;
  }

  .basket-row-even td { background: white; }
  .basket-row-odd td { background: #f8fafc; }

  .basket-drug-name {
    font-weight: 600;
    color: #0f172a;
    font-size: 0.87rem;
  }

  .basket-td-num {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.84rem;
    color: #475569;
  }

  .table-saving {
    color: #059669;
    font-weight: 700;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }

  .table-annual {
    color: #047857;
    font-weight: 800;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }

  .tier-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.03em;
    text-transform: uppercase;
  }

  .tier-pill-standard { background: #f1f5f9; color: #64748b; }
  .tier-pill-bronze { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
  .tier-pill-silver { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
  .tier-pill-gold { background: #fefce8; color: #92400e; border: 1px solid #fde68a; }

  .basket-totals-row td {
    border-top: 2px solid #e2e8f0;
    padding: 13px 14px;
    background: #f8fafc;
  }

  .totals-label {
    font-weight: 700;
    color: #0f172a;
    text-align: right;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .total-cell {
    font-size: 0.95rem;
    font-weight: 800;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }

  .remove-btn {
    background: #fef2f2;
    color: #dc2626;
    border: 1px solid #fecaca;
    border-radius: 6px;
    width: 28px;
    height: 28px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s, border-color 0.15s;
  }

  .remove-btn:hover {
    background: #fee2e2;
    border-color: #fca5a5;
  }

  /* ── Total Banner ── */
  .total-banner {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border-radius: 12px;
    padding: 24px 28px;
    border: 1px solid #334155;
  }

  .total-banner-inner {
    display: flex;
    align-items: center;
    gap: 24px;
  }

  .total-icon-wrap {
    width: 60px;
    height: 60px;
    background: rgba(16,185,129,0.1);
    border: 1px solid rgba(16,185,129,0.2);
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .total-text {
    flex: 1;
  }

  .total-headline {
    font-size: 0.8rem;
    color: #94a3b8;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 4px;
  }

  .total-amount {
    font-size: 2.6rem;
    font-weight: 800;
    color: #10b981;
    letter-spacing: -0.05em;
    line-height: 1;
    margin-bottom: 6px;
  }

  .total-sub {
    font-size: 0.82rem;
    color: #64748b;
    font-weight: 500;
  }

  .total-breakdown {
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 200px;
  }

  .total-breakdown-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.78rem;
  }

  .breakdown-drug {
    color: #94a3b8;
    flex: 1;
    font-weight: 500;
  }

  .breakdown-saving {
    color: #10b981;
    font-weight: 700;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.75rem;
  }

  .breakdown-more {
    font-size: 0.72rem;
    color: #475569;
    font-weight: 600;
    padding-top: 2px;
  }

  /* ── CTA Section ── */
  .cta-section {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 36px 40px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  }

  .cta-inner {
    display: flex;
    align-items: center;
    gap: 24px;
  }

  .cta-icon-wrap {
    width: 56px;
    height: 56px;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .cta-text {
    flex: 1;
  }

  .cta-title {
    font-size: 1.3rem;
    font-weight: 800;
    color: #0f172a;
    margin: 0 0 6px;
    letter-spacing: -0.02em;
  }

  .cta-desc {
    color: #64748b;
    font-size: 0.92rem;
    margin: 0;
    line-height: 1.55;
  }

  .cta-btn {
    padding: 14px 28px;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 0.92rem;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
    transition: background 0.2s, box-shadow 0.2s, transform 0.15s;
    flex-shrink: 0;
  }

  .cta-btn:hover {
    background: #2563eb;
    box-shadow: 0 6px 20px rgba(59,130,246,0.35);
    transform: translateY(-1px);
  }

  .cta-btn:active {
    transform: translateY(0);
  }

  /* ── Responsive ── */
  @media (max-width: 1100px) {
    .calc-layout {
      grid-template-columns: 1fr;
    }
    .results-card {
      position: static;
    }
    .calc-hero-inner {
      grid-template-columns: 1fr;
    }
    .hero-kpi-card {
      max-width: 360px;
    }
  }

  @media (max-width: 760px) {
    .calc-hero {
      padding: 36px 0 32px;
    }
    .hero-title {
      font-size: 1.8rem;
    }
    .tier-cards {
      grid-template-columns: 1fr;
    }
    .cta-inner {
      flex-direction: column;
      align-items: flex-start;
      gap: 16px;
    }
    .cta-btn {
      width: 100%;
      justify-content: center;
    }
    .total-banner-inner {
      flex-direction: column;
      align-items: flex-start;
    }
    .total-amount {
      font-size: 2rem;
    }
    .metrics-grid {
      grid-template-columns: 1fr 1fr;
    }
  }

  @media (max-width: 480px) {
    .calc-container {
      padding: 20px 16px 40px;
    }
    .calc-hero-inner {
      padding: 0 16px;
    }
    .metrics-grid {
      grid-template-columns: 1fr;
    }
    .basket-header-row {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
    }
  }
`;
