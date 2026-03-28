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

  // Trigger animation whenever annual saving changes
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
    // Prevent duplicate drug entries — update existing
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

  return (
    <div className="calc-page">
      <div className="calc-container">

        {/* Hero Header */}
        <div className="calc-header">
          <h1>Bulk Savings Calculator</h1>
          <p className="calc-subtitle">
            Find out exactly how much your pharmacy could save by ordering in bulk — using live NHS Drug Tariff prices.
          </p>
        </div>

        <div className="calc-layout">

          {/* Left panel — inputs */}
          <div className="calc-inputs-panel">

            {/* Drug Selector */}
            <div className="calc-card">
              <h2 className="card-title">1. Select Drug</h2>
              <select
                className="drug-select"
                value={selectedDrugId}
                onChange={(e) => setSelectedDrugId(e.target.value)}
              >
                {DRUGS.map((drug) => (
                  <option key={drug.id} value={drug.id}>
                    {drug.name} — {formatGBP(drug.price)} (NHS Tariff)
                  </option>
                ))}
              </select>
              <div className="drug-price-tag">
                NHS Drug Tariff unit price: <strong>{formatGBP(selectedDrug.price)}</strong>
              </div>
            </div>

            {/* Monthly Usage */}
            <div className="calc-card">
              <h2 className="card-title">2. Monthly Usage</h2>
              <div className="usage-controls">
                <input
                  type="range"
                  min={10}
                  max={1000}
                  step={10}
                  value={units}
                  onChange={(e) => handleUnitsSlider(parseInt(e.target.value, 10))}
                  className="usage-slider"
                />
                <div className="usage-number-wrap">
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
              </div>
              <div className="slider-labels">
                <span>10</span>
                <span>250</span>
                <span>500</span>
                <span>750</span>
                <span>1,000</span>
              </div>
            </div>

            {/* Bulk Tier Selector */}
            <div className="calc-card">
              <h2 className="card-title">3. Choose Bulk Tier</h2>
              <div className="tier-options">
                {TIERS.map((tier) => (
                  <label
                    key={tier.id}
                    className={`tier-option ${selectedTierId === tier.id ? "tier-selected" : ""} tier-${tier.id}`}
                  >
                    <input
                      type="radio"
                      name="bulk-tier"
                      value={tier.id}
                      checked={selectedTierId === tier.id}
                      onChange={() => setSelectedTierId(tier.id)}
                      className="tier-radio"
                    />
                    <div className="tier-content">
                      <div className="tier-header-row">
                        <span className="tier-name">{tier.label}</span>
                        <span className="tier-discount-badge">
                          {tier.discount === 0 ? "No discount" : `-${tier.discount}%`}
                        </span>
                      </div>
                      <span className="tier-range">{tier.range}</span>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Add to Basket */}
            <button className="add-basket-btn" onClick={handleAddToBasket}>
              + Add to Savings Basket
            </button>
          </div>

          {/* Right panel — live results */}
          <div className="calc-results-panel">
            <div className="results-card">
              <h2 className="results-title">Live Savings Estimate</h2>

              <div className="results-grid">
                <div className="result-row">
                  <span className="result-label">Standard monthly spend</span>
                  <span className="result-value neutral">{formatGBP(monthlyStandard)}</span>
                </div>
                <div className="result-row">
                  <span className="result-label">
                    Bulk price
                    {selectedTier.discount > 0 && (
                      <span className="inline-badge"> -{selectedTier.discount}%</span>
                    )}
                  </span>
                  <span className="result-value blue">{formatGBP(monthlyBulk)}</span>
                </div>
                <div className="result-divider" />
                <div className="result-row">
                  <span className="result-label">Monthly saving</span>
                  <span className="result-value green">
                    {formatGBP(monthlySaving)}
                    {savingPercent > 0 && (
                      <span className="saving-pct"> ({savingPercent}%)</span>
                    )}
                  </span>
                </div>
                <div className="result-row">
                  <span className="result-label">Annual saving</span>
                  <span className="result-value green">{formatGBP(annualSaving)}</span>
                </div>
              </div>

              {/* Savings Banner */}
              <div
                key={savingsAnimKey}
                className={`savings-banner ${annualSaving > 0 ? "savings-banner-active" : "savings-banner-zero"}`}
              >
                {annualSaving > 0 ? (
                  <>
                    <div className="banner-emoji">💰</div>
                    <div className="banner-text">
                      You could save{" "}
                      <span className="banner-amount">{formatGBP(annualSaving)}</span>{" "}
                      per year on this drug alone
                    </div>
                  </>
                ) : (
                  <>
                    <div className="banner-emoji">📊</div>
                    <div className="banner-text">
                      Select a bulk tier to see your savings
                    </div>
                  </>
                )}
              </div>

              {/* Tier comparison mini-table */}
              <div className="tier-compare">
                <h3 className="compare-title">Compare all tiers for this drug</h3>
                <table className="compare-table">
                  <thead>
                    <tr>
                      <th>Tier</th>
                      <th>Discount</th>
                      <th>Monthly Price</th>
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
                        >
                          <td>{tier.label}</td>
                          <td>{tier.discount === 0 ? "—" : `-${tier.discount}%`}</td>
                          <td>{formatGBP(bulkPrice)}</td>
                          <td className={aSaving > 0 ? "compare-saving" : ""}>{aSaving > 0 ? formatGBP(aSaving) : "—"}</td>
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
              <h2 className="basket-title">Savings Basket</h2>
              <span className="basket-count">{basket.length} drug{basket.length !== 1 ? "s" : ""}</span>
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
                  {basket.map((item) => (
                    <tr key={item.drug.id}>
                      <td className="basket-drug-name">{item.drug.name}</td>
                      <td>{item.units.toLocaleString()}</td>
                      <td>
                        <span className={`tier-pill tier-pill-${item.tier.id}`}>
                          {item.tier.label}
                        </span>
                      </td>
                      <td>{formatGBP(item.monthlyStandard)}</td>
                      <td>{formatGBP(item.monthlyBulk)}</td>
                      <td className="table-saving">{formatGBP(item.monthlySaving)}</td>
                      <td className="table-annual">{formatGBP(item.annualSaving)}</td>
                      <td>
                        <button
                          className="remove-btn"
                          onClick={() => handleRemoveFromBasket(item.drug.id)}
                          title="Remove"
                        >
                          ×
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="basket-totals">
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
                <div className="total-icon">🏆</div>
                <div className="total-text">
                  <div className="total-headline">
                    Total potential annual saving across your basket
                  </div>
                  <div className="total-amount">{formatGBP(totalAnnualSaving)}</div>
                  <div className="total-sub">
                    That's {formatGBPShort(totalMonthlySaving)} per month — {formatGBPShort(totalAnnualSaving)} per year
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* CTA Section */}
        <div className="cta-section">
          <div className="cta-content">
            <h2>Ready to lock in these savings?</h2>
            <p>
              Our team will build a fully personalised bulk procurement plan based on your pharmacy's dispensing data.
            </p>
            <button className="cta-btn" onClick={() => navigate("/contact")}>
              Get Your Custom Bulk Quote →
            </button>
          </div>
        </div>
      </div>

      <style>{`
        .calc-page {
          background: #f4f6f9;
          min-height: 100vh;
          padding: 24px 0 48px;
        }

        .calc-container {
          max-width: 1300px;
          margin: 0 auto;
          padding: 0 20px;
        }

        /* Header */
        .calc-header {
          text-align: center;
          margin-bottom: 40px;
        }

        .calc-header h1 {
          font-size: 2.4rem;
          font-weight: 800;
          color: #1a1a1a;
          margin: 0 0 12px;
        }

        .calc-subtitle {
          font-size: 1.1rem;
          color: #555;
          max-width: 680px;
          margin: 0 auto;
          line-height: 1.6;
        }

        /* Two-column layout */
        .calc-layout {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 28px;
          margin-bottom: 40px;
          align-items: start;
        }

        /* Cards */
        .calc-card {
          background: white;
          border-radius: 14px;
          padding: 24px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.06);
          margin-bottom: 20px;
        }

        .card-title {
          font-size: 1rem;
          font-weight: 700;
          color: #1976d2;
          text-transform: uppercase;
          letter-spacing: 0.6px;
          margin: 0 0 16px;
        }

        /* Drug Selector */
        .drug-select {
          width: 100%;
          padding: 12px 14px;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          font-size: 0.95rem;
          color: #1a1a1a;
          background: white;
          cursor: pointer;
          transition: border-color 0.2s;
          appearance: auto;
        }

        .drug-select:focus {
          outline: none;
          border-color: #1976d2;
        }

        .drug-price-tag {
          margin-top: 10px;
          font-size: 0.9rem;
          color: #666;
          padding: 8px 12px;
          background: #f0f4ff;
          border-radius: 6px;
        }

        /* Usage Controls */
        .usage-controls {
          display: flex;
          flex-direction: column;
          gap: 14px;
        }

        .usage-slider {
          width: 100%;
          height: 6px;
          accent-color: #1976d2;
          cursor: pointer;
        }

        .usage-number-wrap {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .usage-number-input {
          width: 90px;
          padding: 10px 12px;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          font-size: 1.1rem;
          font-weight: 700;
          color: #1a1a1a;
          text-align: center;
          transition: border-color 0.2s;
        }

        .usage-number-input:focus {
          outline: none;
          border-color: #1976d2;
        }

        .usage-unit-label {
          color: #666;
          font-size: 0.9rem;
        }

        .slider-labels {
          display: flex;
          justify-content: space-between;
          font-size: 0.78rem;
          color: #aaa;
          margin-top: 4px;
        }

        /* Tier Options */
        .tier-options {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }

        .tier-option {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          padding: 14px;
          border: 2px solid #e0e0e0;
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.2s;
          background: white;
        }

        .tier-option:hover {
          border-color: #1976d2;
          background: #f0f4ff;
        }

        .tier-selected {
          border-color: #1976d2 !important;
          background: #e8f0fd !important;
        }

        .tier-radio {
          margin-top: 2px;
          accent-color: #1976d2;
        }

        .tier-content {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .tier-header-row {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }

        .tier-name {
          font-weight: 700;
          font-size: 0.95rem;
          color: #1a1a1a;
        }

        .tier-discount-badge {
          font-size: 0.78rem;
          font-weight: 700;
          padding: 2px 7px;
          border-radius: 12px;
          background: #e8f5e9;
          color: #2e7d32;
        }

        .tier-standard .tier-discount-badge {
          background: #f5f5f5;
          color: #888;
        }

        .tier-range {
          font-size: 0.8rem;
          color: #888;
        }

        /* Add to Basket Button */
        .add-basket-btn {
          width: 100%;
          padding: 16px;
          background: #1976d2;
          color: white;
          border: none;
          border-radius: 10px;
          font-size: 1rem;
          font-weight: 700;
          cursor: pointer;
          transition: background 0.2s, box-shadow 0.2s;
          letter-spacing: 0.2px;
        }

        .add-basket-btn:hover {
          background: #1565c0;
          box-shadow: 0 4px 14px rgba(25,118,210,0.3);
        }

        /* Results Panel */
        .results-card {
          background: white;
          border-radius: 14px;
          padding: 28px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.06);
          position: sticky;
          top: 90px;
        }

        .results-title {
          font-size: 1.2rem;
          font-weight: 700;
          color: #1a1a1a;
          margin: 0 0 20px;
          padding-bottom: 14px;
          border-bottom: 2px solid #f0f0f0;
        }

        .results-grid {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin-bottom: 24px;
        }

        .result-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .result-label {
          font-size: 0.95rem;
          color: #555;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .inline-badge {
          font-size: 0.78rem;
          font-weight: 700;
          padding: 2px 6px;
          border-radius: 10px;
          background: #e8f5e9;
          color: #2e7d32;
        }

        .result-value {
          font-size: 1.1rem;
          font-weight: 700;
        }

        .result-value.neutral { color: #555; }
        .result-value.blue { color: #1976d2; }
        .result-value.green { color: #2e7d32; }

        .saving-pct {
          font-size: 0.85rem;
          font-weight: 600;
          color: #4caf50;
        }

        .result-divider {
          height: 1px;
          background: #f0f0f0;
          margin: 4px 0;
        }

        /* Savings Banner */
        .savings-banner {
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 24px;
          display: flex;
          align-items: center;
          gap: 16px;
          animation: bannerPop 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
        }

        .savings-banner-active {
          background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%);
          border: 2px solid #a5d6a7;
        }

        .savings-banner-zero {
          background: #f5f5f5;
          border: 2px solid #e0e0e0;
        }

        @keyframes bannerPop {
          0% { transform: scale(0.95); opacity: 0.6; }
          100% { transform: scale(1); opacity: 1; }
        }

        .banner-emoji {
          font-size: 2.2rem;
          flex-shrink: 0;
        }

        .banner-text {
          font-size: 0.95rem;
          color: #333;
          line-height: 1.5;
        }

        .banner-amount {
          font-size: 1.6rem;
          font-weight: 800;
          color: #1b5e20;
          display: inline-block;
        }

        /* Tier Compare Table */
        .tier-compare {
          border-top: 1px solid #f0f0f0;
          padding-top: 20px;
        }

        .compare-title {
          font-size: 0.85rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: #888;
          margin: 0 0 12px;
        }

        .compare-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.88rem;
        }

        .compare-table th {
          text-align: left;
          padding: 6px 8px;
          color: #999;
          font-weight: 600;
          border-bottom: 1px solid #f0f0f0;
        }

        .compare-table td {
          padding: 8px 8px;
          color: #444;
          border-bottom: 1px solid #f9f9f9;
        }

        .compare-row-active td {
          background: #e8f0fd;
          font-weight: 700;
          color: #1565c0;
        }

        .compare-saving {
          color: #2e7d32;
          font-weight: 600;
        }

        /* Basket Section */
        .basket-section {
          background: white;
          border-radius: 14px;
          padding: 28px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.06);
          margin-bottom: 36px;
        }

        .basket-header-row {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 20px;
        }

        .basket-title {
          font-size: 1.4rem;
          font-weight: 700;
          color: #1a1a1a;
          margin: 0;
        }

        .basket-count {
          background: #1976d2;
          color: white;
          font-size: 0.82rem;
          font-weight: 700;
          padding: 3px 10px;
          border-radius: 20px;
        }

        .basket-table-wrap {
          overflow-x: auto;
          margin-bottom: 24px;
        }

        .basket-table {
          width: 100%;
          border-collapse: collapse;
          min-width: 700px;
          font-size: 0.9rem;
        }

        .basket-table th {
          background: #f8f9fa;
          padding: 10px 12px;
          text-align: left;
          font-weight: 600;
          color: #555;
          border-bottom: 2px solid #e0e0e0;
          white-space: nowrap;
        }

        .basket-table td {
          padding: 12px 12px;
          border-bottom: 1px solid #f0f0f0;
          color: #333;
          vertical-align: middle;
        }

        .basket-drug-name {
          font-weight: 600;
          color: #1a1a1a;
        }

        .table-saving {
          color: #2e7d32;
          font-weight: 600;
        }

        .table-annual {
          color: #1b5e20;
          font-weight: 700;
          font-size: 0.95rem;
        }

        .tier-pill {
          display: inline-block;
          padding: 3px 10px;
          border-radius: 20px;
          font-size: 0.78rem;
          font-weight: 700;
        }

        .tier-pill-standard { background: #f5f5f5; color: #666; }
        .tier-pill-bronze { background: #fff3e0; color: #e65100; }
        .tier-pill-silver { background: #eceff1; color: #37474f; }
        .tier-pill-gold { background: #fff8e1; color: #f57f17; }

        .basket-totals td {
          border-top: 2px solid #e0e0e0;
          padding: 14px 12px;
          background: #f8f9fa;
        }

        .totals-label {
          font-weight: 700;
          color: #1a1a1a;
          text-align: right;
        }

        .total-cell {
          font-size: 1.05rem;
          font-weight: 800;
        }

        .remove-btn {
          background: #ffebee;
          color: #c62828;
          border: none;
          border-radius: 6px;
          width: 28px;
          height: 28px;
          font-size: 1.1rem;
          line-height: 1;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: background 0.2s;
        }

        .remove-btn:hover {
          background: #ef9a9a;
        }

        /* Total Banner */
        .total-banner {
          background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);
          border-radius: 12px;
          padding: 24px 28px;
          color: white;
        }

        .total-banner-inner {
          display: flex;
          align-items: center;
          gap: 20px;
        }

        .total-icon {
          font-size: 3rem;
          flex-shrink: 0;
        }

        .total-text {
          flex: 1;
        }

        .total-headline {
          font-size: 1rem;
          opacity: 0.9;
          margin-bottom: 6px;
        }

        .total-amount {
          font-size: 2.8rem;
          font-weight: 800;
          letter-spacing: -1px;
          line-height: 1;
        }

        .total-sub {
          font-size: 0.9rem;
          opacity: 0.8;
          margin-top: 6px;
        }

        /* CTA Section */
        .cta-section {
          text-align: center;
          padding: 48px 20px;
          background: white;
          border-radius: 14px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        }

        .cta-content h2 {
          font-size: 1.9rem;
          font-weight: 800;
          color: #1a1a1a;
          margin: 0 0 12px;
        }

        .cta-content p {
          color: #666;
          font-size: 1.05rem;
          max-width: 520px;
          margin: 0 auto 28px;
          line-height: 1.6;
        }

        .cta-btn {
          padding: 16px 40px;
          background: #1976d2;
          color: white;
          border: none;
          border-radius: 10px;
          font-size: 1.1rem;
          font-weight: 700;
          cursor: pointer;
          transition: background 0.2s, box-shadow 0.2s, transform 0.2s;
          letter-spacing: 0.2px;
        }

        .cta-btn:hover {
          background: #1565c0;
          box-shadow: 0 6px 20px rgba(25,118,210,0.35);
          transform: translateY(-2px);
        }

        /* Responsive */
        @media (max-width: 900px) {
          .calc-layout {
            grid-template-columns: 1fr;
          }

          .results-card {
            position: static;
          }

          .tier-options {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 600px) {
          .calc-header h1 {
            font-size: 1.7rem;
          }

          .total-amount {
            font-size: 2rem;
          }

          .total-banner-inner {
            flex-direction: column;
            text-align: center;
          }

          .cta-content h2 {
            font-size: 1.4rem;
          }

          .cta-btn {
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
}
