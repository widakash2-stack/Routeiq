import pandas as pd
import os

OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../data/payment_data.csv"
)

# =========================
# SUCCESS RATES
# Premium: 0.75-0.85 | Good: 0.65-0.75 | Standard: 0.55-0.65
# =========================
SUCCESS_RATES = {
    # Premium
    "Xendit":        0.82,
    "Fincra":        0.80,
    "checkout":      0.80,
    "korapay":       0.78,
    "Passpoint":     0.76,
    # Good
    "payok":         0.74,
    "paymongo":      0.72,
    "relworx":       0.72,
    "yellowcard":    0.70,
    "directa24":     0.70,
    "bitso":         0.68,
    "openpayd":      0.68,
    "clearjunction": 0.67,
    "tazapay":       0.67,
    "Alfred":        0.66,
    # Standard
    "1vnpay":        0.64,
    "altpay":        0.63,
    "awepay":        0.62,
    "Bitlipa":       0.62,
    "brick":         0.62,
    "cobre":         0.61,
    "Innovative":    0.61,
    "apaylo":        0.60,
    "wingpay":       0.60,
    "M2pay":         0.60,
    "Vimoni":        0.60,
    "BRLA":          0.59,
    "Shimatomo":     0.59,
    "Banxa":         0.58,
    "CoinsPH":       0.58,
    "Sasapay":       0.58,
    "payaza":        0.57,
    "Dusupay":       0.57,
    "Afriex":        0.56,
}

# =========================
# TIERS
# =========================
PREMIUM_PSPS = {"Xendit", "Fincra", "checkout", "korapay", "Passpoint"}
GOOD_PSPS    = {
    "payok", "paymongo", "relworx", "yellowcard", "directa24",
    "bitso", "openpayd", "clearjunction", "tazapay", "Alfred",
}

def _tier(psp):
    if psp in PREMIUM_PSPS:
        return "premium"
    if psp in GOOD_PSPS:
        return "good"
    return "standard"

# Cost ranges: premium $2.00-2.50, good $1.50-2.00, standard $1.00-1.50
COST_MAP = {
    "premium":  2.25,
    "good":     1.75,
    "standard": 1.25,
}

# Latency: premium 600-800ms, good 800-1200ms, standard 1200-1800ms
LATENCY_MAP = {
    "premium":  700,
    "good":     1000,
    "standard": 1500,
}

# =========================
# COVERAGE
# (currency, [psps], [payment_methods])
# Grouped by currency so routing_engine can key on currency/method
# =========================
COVERAGE = [
    # ── APAC ──────────────────────────────────────────────────────────────
    ("VND",  ["1vnpay", "awepay", "M2pay"],
             ["Local Wallet", "Bank Transfer", "MoMo", "VietQR"]),
    ("THB",  ["awepay", "payok", "M2pay"],
             ["Thai QR", "Bank Transfer"]),
    ("MYR",  ["awepay", "M2pay"],
             ["FPX", "DuitNow"]),
    ("IDR",  ["awepay", "brick", "payok"],
             ["Bank Transfer", "QRIS", "Ewallet", "Dana", "OVO"]),
    ("PHP",  ["Xendit", "paymongo", "Innovative", "wingpay", "CoinsPH"],
             ["ShopeePay", "GrabPay", "GCash", "QRPH", "Bank Transfer", "PayMaya"]),
    ("JPY",  ["Shimatomo"],
             ["Bank Transfer"]),
    ("AUD",  ["Banxa"],
             ["PayID"]),

    # ── Africa ────────────────────────────────────────────────────────────
    ("NGN",  ["Fincra", "korapay", "yellowcard", "Passpoint"],
             ["Bank Transfer"]),
    ("KES",  ["Fincra", "korapay", "yellowcard", "Sasapay", "Passpoint"],
             ["M-Pesa", "Mobile Money"]),
    ("GHS",  ["korapay", "Bitlipa"],
             ["MTN", "Mobile Money"]),
    ("TZS",  ["Bitlipa", "relworx", "yellowcard", "payaza", "Dusupay"],
             ["Bank Transfer", "Mobile Money", "Airtel", "Vodacom M-Pesa"]),
    ("UGX",  ["Bitlipa", "relworx", "payaza", "Dusupay", "Fincra"],
             ["MTN", "Airtel", "Mobile Money"]),
    ("ZAR",  ["Bitlipa"],
             ["Bank Transfer"]),
    ("XOF",  ["payaza"],
             ["Wave"]),
    ("EGP",  ["Afriex"],
             ["Bank Transfer"]),
    ("XAF",  ["Afriex"],
             ["MTN"]),

    # ── Europe ────────────────────────────────────────────────────────────
    ("EUR",  ["altpay", "openpayd", "clearjunction"],
             ["Bank Transfer", "SEPA Bank Transfer"]),
    ("PLN",  ["Vimoni"],
             ["BLIK"]),

    # ── LATAM ─────────────────────────────────────────────────────────────
    ("MXN",  ["bitso", "directa24", "tazapay", "Alfred"],
             ["SPEI", "CODI", "Bank Transfer"]),
    ("COP",  ["bitso", "cobre", "directa24", "Alfred"],
             ["PSE", "Bank Transfer"]),
    ("BRL",  ["bitso", "directa24", "tazapay", "BRLA", "Alfred"],
             ["PIX", "PIX QR", "Bank Transfer"]),
    ("ARS",  ["bitso"],
             ["Bank Transfer"]),
    ("CLP",  ["directa24"],
             ["Bank Transfer"]),
    ("PEN",  ["directa24"],
             ["Bank Transfer"]),

    # ── North America ─────────────────────────────────────────────────────
    ("CAD",  ["apaylo"],
             ["Interac Bank Transfer"]),

    # ── Global ────────────────────────────────────────────────────────────
    ("GLOBAL", ["checkout"],
               ["Card", "Apple Pay", "Google Pay"]),
]


def generate():
    rows = []

    for currency, partners, methods in COVERAGE:
        for partner in partners:
            tier = _tier(partner)
            sr   = SUCCESS_RATES.get(partner, 0.60)
            for method in methods:
                rows.append({
                    "country":        currency,   # keyed by currency throughout the system
                    "payment_method": method,
                    "psp":            partner,
                    "success_rate":   sr,
                    "base_cost":      COST_MAP[tier],
                    "percent_cost":   0.015,
                    "latency_ms":     LATENCY_MAP[tier],
                })

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Generated {len(df)} rows → {OUTPUT_PATH}")
    print(f"Currencies: {df['country'].nunique()}  |  Partners: {df['psp'].nunique()}  |  Methods: {df['payment_method'].nunique()}")
    return df


if __name__ == "__main__":
    generate()
