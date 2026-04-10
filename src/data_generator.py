import pandas as pd
import os

OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../data/payment_data.csv"
)

# Fixed success rates per PSP
SUCCESS_RATES = {
    # Africa — clear 2-tier gap for faster bandit convergence
    "Relworx":       0.65,
    "Fincra":        0.75,
    "Korapay":       0.60,
    "Dusupay":       0.55,
    "Payaza":        0.50,
    "Quidax":        0.45,
    "Partner_S":     0.45,
    "Partner_T":     0.45,
    "Partner_U":     0.45,
    # APAC
    "Xendit":        0.75,
    "Partner_A":     0.75,
    "LianLian_Pay":  0.67,
    "Coins.ph":      0.67,
    "Partner_B":     0.67,
    "Paymongo":      0.60,
    "Partner_C":     0.60,
    "Partner_D":     0.60,
    "BitcoinVN":     0.55,
    "Partner_E":     0.55,
    "Partner_F":     0.55,
    "Directa24":     0.45,
    "Partner_G":     0.45,
    "Partner_H":     0.45,
    "Partner_I":     0.45,
    "Partner_J":     0.45,
    # Europe / Americas
    "Checkout.com":  0.75,
    "Partner_K":     0.75,
    "OpenPayd":      0.67,
    "ClearJunction": 0.67,
    "Partner_L":     0.67,
    "Bitso":         0.60,
    "Partner_M":     0.60,
    "Partner_N":     0.60,
    "PaySafe":       0.55,
    "Partner_O":     0.55,
    "Partner_P":     0.55,
    "Partner_Q":     0.45,
    "Partner_R":     0.45,
    "Partner_T":     0.67,
    "Partner_U":     0.69,
    "Partner_V":     0.72,
    "Partner_W":     0.45,
    "Partner_X":     0.75,
    "Partner_Y":     0.60,
    "Partner_Z":     0.55,
    "Partner_AA":    0.67,
    "Partner_AB":    0.45,
    "Partner_AC":    0.60,
    "Partner_AD":    0.67,
}

# Cost and latency tiers
PREMIUM_PSPS = {"Checkout.com", "Relworx", "Xendit", "Fincra"}
GOOD_PSPS    = {
    "Coins.ph", "BitcoinVN", "Bitso", "OpenPayd", "ClearJunction",
    "Korapay", "Dusupay", "Payaza", "Quidax", "Paymongo",
    "LianLian_Pay", "Directa24", "PaySafe",
}

def _tier(psp):
    if psp in PREMIUM_PSPS:
        return "premium"
    if psp in GOOD_PSPS:
        return "good"
    return "budget"

COST_MAP    = {"premium": 2.50, "good": 1.80, "budget": 1.20}
LATENCY_MAP = {"premium": 600,  "good": 1000, "budget": 1600}

COVERAGE = [
    ("Indonesia",    ["Xendit", "LianLian_Pay", "Partner_A", "Partner_B", "Partner_C"],
                     ["GoPay", "OVO", "DANA", "ShopeePay", "BANK_TRANSFER"]),
    ("Philippines",  ["Coins.ph", "Paymongo", "Partner_D", "Partner_E", "Partner_F"],
                     ["GCash", "PayMaya", "BANK_TRANSFER"]),
    ("Vietnam",      ["BitcoinVN", "Partner_G", "Partner_H", "Partner_I", "Partner_J"],
                     ["MoMo", "ZaloPay", "Viettel_Pay"]),
    ("Thailand",     ["Directa24", "Partner_K", "Partner_L", "Partner_M", "Partner_N"],
                     ["PromptPay", "BANK_TRANSFER"]),
    ("Malaysia",     ["Directa24", "Partner_O", "Partner_P", "Partner_Q", "Partner_R"],
                     ["FPX", "Touch_n_Go", "BANK_TRANSFER"]),
    ("Nigeria",      ["Quidax", "Korapay", "Fincra", "Dusupay", "Relworx", "Payaza"],
                     ["BANK_TRANSFER"]),
    ("Kenya",        ["Fincra", "Dusupay", "Relworx", "Payaza", "Partner_S"],
                     ["M-Pesa", "BANK_TRANSFER"]),
    ("Ghana",        ["Fincra", "Dusupay", "Relworx", "Payaza", "Partner_T"],
                     ["MTN_Mobile_Money", "BANK_TRANSFER"]),
    ("Tanzania",     ["Fincra", "Dusupay", "Relworx", "Payaza", "Partner_U"],
                     ["Airtel_Money", "HaloPesa", "BANK_TRANSFER"]),
    ("EU",           ["Checkout.com", "OpenPayd", "ClearJunction", "PaySafe", "Partner_V"],
                     ["SEPA", "OPEN_BANKING"]),
    ("Brazil",       ["Bitso", "Partner_W", "Partner_X", "Partner_Y", "Partner_Z"],
                     ["PIX", "BANK_TRANSFER"]),
    ("Mexico",       ["Bitso", "Partner_W", "Partner_X", "Partner_Y", "Partner_Z"],
                     ["SPEI", "BANK_TRANSFER"]),
    ("Chile",        ["Partner_W", "Partner_X", "Partner_Y", "Partner_Z", "Partner_AA"],
                     ["BANK_TRANSFER"]),
    ("USA",          ["Checkout.com", "ClearJunction", "Partner_AB", "Partner_AC", "Partner_AD"],
                     ["ACH", "WIRE"]),
]


def generate():
    rows = []

    for country, partners, methods in COVERAGE:
        for partner in partners:
            tier = _tier(partner)
            for method in methods:
                rows.append({
                    "country":        country,
                    "payment_method": method,
                    "psp":            partner,
                    "success_rate":   SUCCESS_RATES[partner],
                    "base_cost":      COST_MAP[tier],
                    "percent_cost":   0.015,
                    "latency_ms":     LATENCY_MAP[tier],
                })

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Generated {len(df)} rows → {OUTPUT_PATH}")
    print(f"Countries: {df['country'].nunique()}  |  Partners: {df['psp'].nunique()}  |  Methods: {df['payment_method'].nunique()}")


if __name__ == "__main__":
    generate()
