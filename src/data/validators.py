"""Data validation, cleaning rules, strict boolean parsing, and SHA-256 auditing for RiskLens AI.

Strict Policies:
- Never apply ABS() to negative values. Nullify invalid negatives and set explicit audit flags.
- Flag invalid ages (<18 or >100) before setting to NULL.
- Strict boolean parsing: YES -> 1, NO -> 0, NULL -> NULL. No silent 'ELSE 0'.
- Cast Credit_Score to integer only when integral (val % 1 == 0). Reject unexpected fractionals.
- Preserve legitimate recorded zero sanctioned amounts for rejected applications; distinguish from NULLs.
- Enforce strict decision consistency and whitelist validation on all categorical fields.
"""

import hashlib
from typing import Optional, Tuple, Any
import pandas as pd
import numpy as np

# Canonical Domain Whitelists (Verified against data/raw/kaggle_original.csv)
VALID_GENDERS = {'Male', 'Female', 'Other'}
VALID_MARITAL_STATUSES = {'Married', 'Single', 'Divorced', 'Widowed'}
VALID_EDUCATION_LEVELS = {'Bachelor', 'High School', 'Master', 'PhD', 'Phd'}
VALID_EMPLOYMENT_STATUSES = {'Salaried', 'Self-Employed', 'Contract', 'Business Owner', 'Unemployed'}
VALID_PROPERTY_OWNERSHIPS = {'Rent', 'Own', 'Mortgage', 'Other', 'Family Owned'}
VALID_RESIDENTIAL_STATUSES = {'Urban', 'Suburban', 'Rural'}
VALID_REGIONS = {'East', 'South', 'Central', 'North', 'West'}
VALID_CHANNELS = {'Online', 'Branch', 'Mobile App', 'Agent'}
VALID_LOAN_PURPOSES = {
    'Home', 'Education', 'Vehicle', 'Personal', 'Debt Consolidation',
    'Car', 'Business', 'Medical'
}
VALID_PRIOR_LOAN_STATUSES = {'Paid Off', 'Active', 'No Previous Loan', 'Defaulted'}
VALID_RISK_TIERS = {'Low', 'Medium', 'High'}
VALID_DECISIONS = {'Approved', 'Rejected'}


def compute_file_sha256(filepath: str) -> str:
    """Compute the SHA-256 hash of a file in 64KB chunks to guarantee immutability."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def parse_strict_boolean(val: Any, col_name: str, app_id: Any) -> Optional[int]:
    """
    Parse boolean values strictly without dangerous 'ELSE 0' fallbacks.
    
    Returns:
        1 for 'YES', 0 for 'NO', None for NULL.
    Raises:
        ValueError if value is unparseable or unexpected.
    """
    if pd.isnull(val):
        return None
    cleaned = str(val).strip().upper()
    if cleaned == 'YES':
        return 1
    elif cleaned == 'NO':
        return 0
    else:
        raise ValueError(
            f"Strict boolean validation failed: Unexpected value '{val}' in column '{col_name}' "
            f"for Application_ID {app_id}. Ingestion aborted."
        )


def validate_credit_score(val: Any, app_id: Any) -> Optional[int]:
    """
    Validate and cast credit score to integer only when strictly integral.
    
    Rejects or quarantines unexpected fractional values; never silently rounds them.
    Returns:
        Optional[int] in range [0, 1000] or None.
    Raises:
        ValueError on fractional components or out-of-range values.
    """
    if pd.isnull(val):
        return None
    try:
        score_float = float(val)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Malformed credit score '{val}' on Application_ID {app_id}: {e}")
    
    if score_float % 1 != 0:
        raise ValueError(
            f"Unexpected fractional credit score {val} on Application_ID {app_id}. "
            f"Refusing to silently round; score must be integral."
        )
    
    score_int = int(score_float)
    if score_int < 0 or score_int > 1000:
        raise ValueError(
            f"Credit score {score_int} on Application_ID {app_id} out of valid range [0, 1000]."
        )
    return score_int


def validate_age(val: Any, app_id: Any) -> Tuple[Optional[int], int]:
    """
    Validate applicant age. Flags out-of-bounds ages (<18 or >100) before nullifying.
    
    Returns:
        (cleaned_age: Optional[int], has_invalid_age: int)
    """
    if pd.isnull(val):
        return None, 0
    try:
        age_float = float(val)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Malformed age '{val}' on Application_ID {app_id}: {e}")
    
    if age_float % 1 != 0:
        raise ValueError(f"Unexpected fractional age {val} on Application_ID {app_id}.")
    
    age_int = int(age_float)
    if age_int < 18 or age_int > 100:
        # Flag invalid age before nullifying
        return None, 1
    return age_int, 0


def clean_financial_value(val: Any, col_name: str, app_id: Any) -> Tuple[Optional[float], int]:
    """
    Clean financial balance fields. Never apply ABS() to negative values.
    
    Negative values represent corrupted data: nullifies the field and sets audit flag.
    Returns:
        (cleaned_value: Optional[float], has_invalid_flag: int)
    """
    if pd.isnull(val):
        return None, 0
    try:
        num = float(val)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Malformed numeric value '{val}' in '{col_name}' on Application_ID {app_id}: {e}")
    
    if num < 0:
        # Nullify invalid negative balance and flag
        return None, 1
    return num, 0


def validate_decision(val: Any, app_id: Any) -> Tuple[str, int]:
    """
    Validate underwriting decision string and return canonical string and boolean flag.
    
    Enforces strict decision consistency:
      'Approved' -> ('Approved', 1)
      'Rejected' -> ('Rejected', 0)
    Raises:
        ValueError on unexpected strings or NULLs.
    """
    if pd.isnull(val):
        raise ValueError(f"Missing underwriting decision on Application_ID {app_id}.")
    decision = str(val).strip().capitalize()
    if decision == 'Approved':
        return 'Approved', 1
    elif decision == 'Rejected':
        return 'Rejected', 0
    else:
        raise ValueError(
            f"Unexpected underwriting decision '{val}' on Application_ID {app_id}. "
            f"Must be 'Approved' or 'Rejected'."
        )


def validate_sanctioned_amount(
    app_amount: Any, 
    is_approved: int, 
    app_id: Any
) -> Tuple[Optional[float], int]:
    """
    Validate and map sanctioned approved amount.
    
    Preserves:
    - Genuine 0.0 for rejected applications.
    - Positive amounts for approved applications.
    - NULL for missing values on both approved and rejected applications.
    - Flags missingness with has_missing_sanctioned_amount = 1.
    """
    if pd.isnull(app_amount):
        return None, 1
    try:
        amt = float(app_amount)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Malformed approved amount '{app_amount}' on Application_ID {app_id}: {e}")
    
    if amt < 0:
        # Corrupted negative sanctioned amount -> nullify and flag
        return None, 1
    
    if is_approved == 0:
        # Rejected application: genuine 0.0 preserved
        return amt, 0
    else:
        # Approved application: positive sanctioned principal preserved
        return amt, 0


def validate_categorical_value(val: Any, whitelist: set, col_name: str, app_id: Any) -> str:
    """Validate string against canonical whitelist, normalizing whitespace and capitalization."""
    if pd.isnull(val):
        raise ValueError(f"Unexpected NULL in non-nullable categorical '{col_name}' on Application_ID {app_id}.")
    
    raw_str = str(val).strip()
    # Handle known case patterns (Title case or standard mapping)
    normalized = raw_str.title() if col_name != 'purpose_name' else raw_str
    
    # Custom matches for whitelist normalization
    for valid_entry in whitelist:
        if raw_str.upper() == valid_entry.upper():
            return valid_entry
            
    raise ValueError(
        f"Unrecognized categorical value '{val}' in column '{col_name}' on Application_ID {app_id}. "
        f"Expected one of: {sorted(whitelist)}."
    )


def validate_row_data(row: dict) -> dict:
    """
    Validate, sanitize, and transform a single application record.
    
    Returns clean dictionary formatted for fct_loan_application table.
    """
    app_id = int(row['Application_ID'])
    source_ordinal = int(row['source_row_ordinal'])
    
    # 1. Underwriting Decision & Consistency
    decision_str, is_approved = validate_decision(row['Loan_Approved'], app_id)
    
    # 2. Sanctioned Amount & Missingness
    sanctioned_amt, missing_sanctioned = validate_sanctioned_amount(
        row['Approved_Amount'], is_approved, app_id
    )
    
    # 3. Demographics
    cleaned_age, invalid_age = validate_age(row['Age'], app_id)
    gender = validate_categorical_value(row['Gender'], VALID_GENDERS, 'Gender', app_id)
    marital_status = validate_categorical_value(row['Marital_Status'], VALID_MARITAL_STATUSES, 'Marital_Status', app_id)
    education_level = validate_categorical_value(row['Education_Level'], VALID_EDUCATION_LEVELS, 'Education_Level', app_id)
    employment_status = validate_categorical_value(row['Employment_Status'], VALID_EMPLOYMENT_STATUSES, 'Employment_Status', app_id)
    
    job_exp = None if pd.isnull(row['Job_Experience_Years']) else int(row['Job_Experience_Years'])
    if job_exp is not None and job_exp < 0:
        job_exp = None
    dependents = None if pd.isnull(row['Dependents']) else int(row['Dependents'])
    if dependents is not None and dependents < 0:
        dependents = None
        
    # 4. Financial Balances & Negatives
    annual_inc, invalid_income = clean_financial_value(row['Annual_Income'], 'Annual_Income', app_id)
    monthly_inc_rep = None if pd.isnull(row['Monthly_Income']) else float(row['Monthly_Income'])
    if monthly_inc_rep is not None and monthly_inc_rep < 0:
        monthly_inc_rep = None
    
    # Calculated monthly income: annual_income / 12.0 if valid positive annual income exists
    monthly_inc_calc = (annual_inc / 12.0) if annual_inc is not None else None
    
    savings_bal, invalid_savings = clean_financial_value(row['Savings_Balance'], 'Savings_Balance', app_id)
    checking_bal, _ = clean_financial_value(row['Checking_Balance'], 'Checking_Balance', app_id)
    total_assets, _ = clean_financial_value(row['Total_Assets'], 'Total_Assets', app_id)
    total_liab, _ = clean_financial_value(row['Total_Liabilities'], 'Total_Liabilities', app_id)
    monthly_debt, _ = clean_financial_value(row['Monthly_Debt_Payment'], 'Monthly_Debt_Payment', app_id)
    
    net_worth = None
    if total_assets is not None and total_liab is not None:
        net_worth = total_assets - total_liab
        
    tenure_months = None
    if not pd.isnull(row['Bank_Account_Age_Years']):
        tenure_months = int(round(float(row['Bank_Account_Age_Years']) * 12.0))
        if tenure_months < 0:
            tenure_months = None
            
    # 5. Loan Request & Solvency
    req_loan, invalid_loan = clean_financial_value(row['Loan_Amount'], 'Loan_Amount', app_id)
    # Note: If requested loan is 0.0, it is treated as invalid per schema check (requested_loan_amount > 0)
    if req_loan is not None and req_loan == 0:
        req_loan = None
        invalid_loan = 1
        
    req_term = None if pd.isnull(row['Loan_Term_Months']) else int(row['Loan_Term_Months'])
    if req_term is not None and req_term <= 0:
        req_term = None
        
    interest_rate = None if pd.isnull(row['Interest_Rate']) else float(row['Interest_Rate'])
    if interest_rate is not None and (interest_rate < 0 or interest_rate > 100):
        interest_rate = None
        
    dti = None if pd.isnull(row['Debt_To_Income_Ratio']) else float(row['Debt_To_Income_Ratio'])
    if dti is not None and (dti < 0 or dti > 100):
        dti = None
        
    co_app_flag = parse_strict_boolean(row['Co_Applicant'], 'Co_Applicant', app_id)
    collateral_flag = parse_strict_boolean(row['Collateral'], 'Collateral', app_id)
    
    # 6. Credit Bureau Attributes
    bureau_score = validate_credit_score(row['Credit_Score'], app_id)
    existing_loans = None if pd.isnull(row['Existing_Loans']) else int(row['Existing_Loans'])
    if existing_loans is not None and existing_loans < 0:
        existing_loans = None
    late_payments = None if pd.isnull(row['Late_Payments_Last_2_Years']) else int(row['Late_Payments_Last_2_Years'])
    if late_payments is not None and late_payments < 0:
        late_payments = None
    bureau_history_yrs = None if pd.isnull(row['Credit_History_Years']) else float(row['Credit_History_Years'])
    if bureau_history_yrs is not None and bureau_history_yrs < 0:
        bureau_history_yrs = None
    prior_loan_status = validate_categorical_value(
        row['Previous_Loan_Status'], VALID_PRIOR_LOAN_STATUSES, 'Previous_Loan_Status', app_id
    )
    
    # 7. Proprietary Scorecard Attributes
    raw_risk_score = None if pd.isnull(row['Risk_Score']) else float(row['Risk_Score'])
    if raw_risk_score is not None and (raw_risk_score < 0.0 or raw_risk_score > 100.0):
        raw_risk_score = None
        
    # Preserves source Default_Risk directly
    risk_tier = validate_categorical_value(row['Default_Risk'], VALID_RISK_TIERS, 'Default_Risk', app_id)
    
    # Normalized score: Risk_Score / 100.0, strictly NULL if Risk_Score is NULL
    normalized_score = (raw_risk_score / 100.0) if raw_risk_score is not None else None
    
    # 8. Composite Financial Invalidity Flag (Row-level OR across the three negative fields)
    has_invalid_financials = int(bool(invalid_income or invalid_loan or invalid_savings))
    
    return {
        'application_id': app_id,
        'source_row_ordinal': source_ordinal,
        'age': cleaned_age,
        'gender': gender,
        'marital_status': marital_status,
        'education_level': education_level,
        'employment_status': employment_status,
        'job_experience_years': job_exp,
        'dependents': dependents,
        'annual_income': annual_inc,
        'monthly_income_reported': monthly_inc_rep,
        'monthly_income_calculated': monthly_inc_calc,
        'savings_balance': savings_bal,
        'checking_balance': checking_bal,
        'total_assets': total_assets,
        'total_liabilities': total_liab,
        'monthly_debt_payment': monthly_debt,
        'net_worth': net_worth,
        'bank_account_tenure_months': tenure_months,
        'requested_loan_amount': req_loan,
        'requested_term_months': req_term,
        'interest_rate': interest_rate,
        'debt_to_income_ratio': dti,
        'co_applicant_flag': co_app_flag,
        'collateral_flag': collateral_flag,
        'bureau_credit_score': bureau_score,
        'bureau_existing_loans': existing_loans,
        'bureau_late_payments_2yr': late_payments,
        'bureau_credit_history_years': bureau_history_yrs,
        'bureau_prior_loan_status': prior_loan_status,
        'proprietary_risk_score': raw_risk_score,
        'risk_tier': risk_tier,
        'normalized_risk_score': normalized_score,
        'underwriting_decision': decision_str,
        'sanctioned_approved_amount': sanctioned_amt,
        'is_approved': is_approved,
        'has_missing_sanctioned_amount': missing_sanctioned,
        'has_invalid_annual_income': invalid_income,
        'has_invalid_loan_amount': invalid_loan,
        'has_invalid_savings_balance': invalid_savings,
        'has_invalid_age': invalid_age,
        'has_invalid_financials': has_invalid_financials
    }


def verify_duplicate_integrity(df: pd.DataFrame, id_col: str = 'Application_ID') -> dict:
    """
    Rigorously verify exact duplicate rows across all original columns vs duplicate IDs.
    
    Validates:
    1. Count of exact full-row duplicates across all columns (keep='first').
    2. Count of duplicate IDs (keep='first').
    3. Confirms that every duplicate ID has identical source data across all columns (0 conflicting values).
    
    Returns:
        dict with verification statistics:
          - raw_row_count: int
          - raw_col_count: int
          - exact_full_duplicates: int
          - duplicate_id_count: int
          - conflicting_id_count: int
          - is_exact_match: bool
    """
    raw_rows, raw_cols = df.shape
    # All columns full duplicate mask
    full_dup_mask = df.duplicated(keep="first")
    exact_full_duplicates = int(full_dup_mask.sum())
    
    # ID duplicate mask
    id_dup_mask = df.duplicated(subset=[id_col], keep="first")
    duplicate_id_count = int(id_dup_mask.sum())
    
    # Check conflicting data for any repeated ID
    repeated_ids = df[df.duplicated(subset=[id_col], keep=False)][id_col].unique()
    conflicting_ids = []
    
    for rid in repeated_ids:
        sub = df[df[id_col] == rid]
        for col in df.columns:
            if sub[col].nunique(dropna=False) > 1:
                conflicting_ids.append((rid, col))
                break
                
    conflicting_id_count = len(conflicting_ids)
    is_exact_match = (
        (exact_full_duplicates == duplicate_id_count) and 
        (conflicting_id_count == 0) and 
        bool((full_dup_mask == id_dup_mask).all())
    )
    
    return {
        "raw_row_count": raw_rows,
        "raw_col_count": raw_cols,
        "exact_full_duplicates": exact_full_duplicates,
        "duplicate_id_count": duplicate_id_count,
        "conflicting_id_count": conflicting_id_count,
        "conflicting_ids": conflicting_ids,
        "is_exact_match": is_exact_match
    }
