/**
 * RiskLens AI — Financial & Metric Formatting Utilities
 * 
 * Strict Guidelines:
 * - Currency Unit is always explicitly 'CU'. Never invent USD/EUR symbols.
 * - Source NULL values return a consistent em-dash '—' or 'NULL'.
 * - Accurate decimal rounding adhering to financial audit rules.
 */

export function formatCU(
  amount: number | null | undefined,
  compact: boolean = false
): string {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return '—';
  }

  if (compact) {
    const abs = Math.abs(amount);
    if (abs >= 1e9) {
      return `${(amount / 1e9).toFixed(2)}B CU`;
    }
    if (abs >= 1e6) {
      return `${(amount / 1e6).toFixed(2)}M CU`;
    }
    if (abs >= 1e3) {
      return `${(amount / 1e3).toFixed(1)}K CU`;
    }
  }

  return `${amount.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })} CU`;
}

export function formatPct(
  rate: number | null | undefined,
  decimals: number = 2
): string {
  if (rate === null || rate === undefined || isNaN(rate)) {
    return '—';
  }
  return `${rate.toFixed(decimals)}%`;
}

export function formatInt(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) {
    return '—';
  }
  return val.toLocaleString();
}

export function formatFloat(
  val: number | null | undefined,
  decimals: number = 2
): string {
  if (val === null || val === undefined || isNaN(val)) {
    return '—';
  }
  return val.toFixed(decimals);
}

export function formatNullDisplay(val: any, fallback: string = 'NULL'): string {
  if (val === null || val === undefined || val === '') {
    return fallback;
  }
  return String(val);
}
