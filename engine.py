"""
HackerRank Orchestrate September 2026 — "Buy or Wait?"
Data-Driven Deterministic Financial Decision Engine
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
import bisect
import csv
import os
import re

DECIMAL_ZERO = Decimal("0")
DECIMAL_CENT = Decimal("0.01")


def to_dec(val) -> Decimal:
    """Safe Decimal conversion helper."""
    if val is None:
        return DECIMAL_ZERO
    if isinstance(val, Decimal):
        return val
    s = str(val).strip().replace(",", "").replace("$", "")
    if not s or s.lower() in ("none", "nan", "null", ""):
        return DECIMAL_ZERO
    try:
        return Decimal(s)
    except Exception:
        return DECIMAL_ZERO


def round_curr(val: Decimal) -> Decimal:
    """Deterministic rounding to 2 decimal places."""
    return val.quantize(DECIMAL_CENT, rounding=ROUND_HALF_UP)


def parse_date(d_str: str):
    """Parse ISO date YYYY-MM-DD."""
    if not d_str:
        return None
    s = str(d_str).strip()
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def format_date(d) -> str:
    """Format datetime.date to YYYY-MM-DD."""
    return d.strftime("%Y-%m-%d") if d else ""


def format_amount(val: Decimal) -> str:
    """Format Decimal cleanly without floating point artifacts."""
    if val == val.to_integral():
        return str(int(val))
    return f"{val:.2f}".rstrip("0").rstrip(".")


class FinancialEngine:
    # Explicit Image Mappings specified by HackerRank Challenge
    IMAGE_MAPPINGS = {
        "image_01": Decimal("4365000"),
        "image_02": Decimal("100000"),
        "image_03": Decimal("79679.26"),
        "image_04": None,  # Explicitly unresolved / do NOT invent
        "image_05": Decimal("704.05"),
        "image_06": Decimal("1995"),
        "image_07": Decimal("8528"),
        "image_08": Decimal("15339"),
        "image_09": Decimal("723"),
        "image_10": Decimal("41272"),
        "image_11": Decimal("3650"),
        "image_12": (Decimal("33.50"), "USD"),  # Foreign currency converted exactly once
        "image_13": Decimal("2298"),
        "image_14": Decimal("4593"),
        "image_15": Decimal("9968"),
        "image_16": Decimal("393.22"),
    }

    PROTECTED_CATEGORIES = {
        "rent", "mortgage", "utilities", "utility", "healthcare",
        "health", "medical", "insurance", "loan", "debt", "groceries",
        "education", "tuition", "essential"
    }

    def __init__(self, data_dir: str = "dataset"):
        self.data_dir = data_dir
        self.profiles = {}
        self.events_by_user = {}
        self.events_by_id = {}
        self.image_by_event = {}
        self.options_by_request = {}
        self.rates_index = {}  # (from_curr, to_curr) -> list of (date_str, Decimal_rate)
        self.messages_by_user = {}

    def load_data(self):
        """Pre-indexes all datasets efficiently into fast lookup structures."""
        # 1. Images
        images_path = os.path.join(self.data_dir, "images.csv")
        if os.path.exists(images_path):
            with open(images_path, mode="r", encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    rel_id = r.get("related_event_id") or r.get("event_id")
                    img_id = (r.get("image_id") or "").strip()
                    if rel_id and img_id:
                        self.image_by_event[rel_id.strip()] = img_id

        # 2. Exchange Rates with Pre-Indexing for Logarithmic Binary Search
        fx_path = os.path.join(self.data_dir, "exchange_rates.csv")
        if os.path.exists(fx_path):
            raw_rates = {}
            with open(fx_path, mode="r", encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    from_c = (r.get("from_currency") or r.get("currency") or "").strip().upper()
                    to_c = (r.get("to_currency") or "USD").strip().upper()
                    dt = (r.get("date") or "").strip()
                    rate = to_dec(r.get("rate") or r.get("exchange_rate") or "1.0")
                    if from_c and dt:
                        raw_rates.setdefault((from_c, to_c), []).append((dt, rate))
            for key, lst in raw_rates.items():
                lst.sort(key=lambda x: x[0])
                self.rates_index[key] = lst

        # 3. Financial Profiles
        prof_path = os.path.join(self.data_dir, "financial_profiles.csv")
        if os.path.exists(prof_path):
            with open(prof_path, mode="r", encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    uid = (r.get("user_id") or r.get("profile_id") or "").strip()
                    prot_cats = set(self.PROTECTED_CATEGORIES)
                    for c in (r.get("protected_categories") or "").split(";"):
                        if c.strip():
                            prot_cats.add(c.strip().lower())
                    self.profiles[uid] = {
                        "user_id": uid,
                        "current_balance": to_dec(r.get("current_balance")),
                        "home_currency": (r.get("home_currency") or "USD").strip().upper(),
                        "minimum_balance_to_keep": to_dec(r.get("minimum_balance_to_keep")),
                        "monthly_income": to_dec(r.get("monthly_income")),
                        "protected_categories": prot_cats,
                        "preferences": r.get("preferences") or "",
                        "raw": r,
                    }

        # 4. Messages
        msg_path = os.path.join(self.data_dir, "messages.csv")
        if os.path.exists(msg_path):
            with open(msg_path, mode="r", encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    uid = (r.get("user_id") or "").strip()
                    self.messages_by_user.setdefault(uid, []).append(r)

        # 5. Financial Events
        ev_path = os.path.join(self.data_dir, "financial_events.csv")
        if os.path.exists(ev_path):
            with open(ev_path, mode="r", encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    eid = (r.get("event_id") or "").strip()
                    uid = (r.get("user_id") or r.get("profile_id") or "").strip()
                    self.events_by_id[eid] = r
                    self.events_by_user.setdefault(uid, []).append(r)

        # 6. Request Payment Options
        opts_path = os.path.join(self.data_dir, "request_payment_options.csv")
        if os.path.exists(opts_path):
            with open(opts_path, mode="r", encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    rid = (r.get("request_id") or "").strip()
                    self.options_by_request.setdefault(rid, []).append(r)

    def get_fx_rate(self, from_curr: str, to_curr: str, dt_obj: datetime.date) -> Decimal:
        """Finds latest exchange rate on or before dt_obj using binary search."""
        from_curr, to_curr = from_curr.upper(), to_curr.upper()
        if from_curr == to_curr:
            return Decimal("1.0")

        dt_str = format_date(dt_obj)
        series = self.rates_index.get((from_curr, to_curr))
        if not series and (from_curr, "USD") in self.rates_index:
            series = self.rates_index[(from_curr, "USD")]

        if not series:
            return Decimal("1.0")

        dates = [item[0] for item in series]
        idx = bisect.bisect_right(dates, dt_str) - 1
        if idx >= 0:
            return series[idx][1]
        return series[0][1]

    def resolve_event_amount(self, ev: dict, home_curr: str, ev_date: datetime.date):
        """
        Resolves event amount:
        - Resolves images strictly.
        - Converts foreign currency exactly once.
        - Unresolved credits return (None, 'unresolved_credit').
        - Unresolved debits return (None, 'unresolved_debit').
        """
        raw_amt = ev.get("amount")
        ev_id = ev.get("event_id", "").strip()
        curr = (ev.get("currency") or home_curr).strip().upper()
        direction = (ev.get("direction") or "debit").strip().lower()

        # Direct explicit amount
        if raw_amt not in (None, "", "null", "None"):
            amt = to_dec(raw_amt)
            if curr != home_curr:
                amt = amt * self.get_fx_rate(curr, home_curr, ev_date)
            return round_curr(amt), "resolved"

        # Image resolution
        img_id = self.image_by_event.get(ev_id)
        if img_id and img_id in self.IMAGE_MAPPINGS:
            mapped = self.IMAGE_MAPPINGS[img_id]
            if mapped is None:
                return (None, f"unresolved_{direction}")
            if isinstance(mapped, tuple):
                base_amt, img_curr = mapped
                amt = base_amt * self.get_fx_rate(img_curr, home_curr, ev_date)
                return round_curr(amt), "resolved"
            amt = mapped
            if curr != home_curr and curr != "USD":
                amt = amt * self.get_fx_rate(curr, home_curr, ev_date)
            return round_curr(amt), "resolved"

        return (None, f"unresolved_{direction}")

    def process_events(self, user_id: str, home_curr: str, req_date: datetime.date) -> list:
        """
        Precedence rules:
        1. Explicit cancellation / amendment / settlement
        2. Newer event from same source
        3. Settled over pending
        4. Conservative resolution for remaining ambiguities
        """
        raw_events = self.events_by_user.get(user_id, [])

        cancelled_events = set()
        amended_amounts = {}

        # 1. Parse cancellations and amendments from messages
        for msg in self.messages_by_user.get(user_id, []):
            content = msg.get("message") or msg.get("content") or ""
            for cid in re.findall(r"cancel(?:led)?\s+(?:event_)?(\w+)", content, re.I):
                cancelled_events.add(cid if cid.startswith("event_") else f"event_{cid}")
            m_amend = re.search(r"amend(?:ed)?\s+(?:event_)?(\w+)\s+(?:to\s+)?([\d\.,]+)", content, re.I)
            if m_amend:
                eid, amt_s = m_amend.groups()
                eid = eid if eid.startswith("event_") else f"event_{eid}"
                amended_amounts[eid] = to_dec(amt_s)

        # 2. Parse cancellations/amendments from events
        for ev in raw_events:
            st = (ev.get("status") or "").lower()
            typ = (ev.get("type") or ev.get("event_type") or "").lower()
            ref = (ev.get("reference_event_id") or ev.get("related_event_id") or "").strip()
            if st == "cancelled" or typ == "cancellation":
                if ref:
                    cancelled_events.add(ref)
            if (st == "amended" or typ == "amendment") and ref:
                amt = to_dec(ev.get("amount"))
                if amt > DECIMAL_ZERO:
                    amended_amounts[ref] = amt

        # 3. Deduplicate events by source reference / event_id
        event_dict = {}
        for ev in raw_events:
            eid = (ev.get("event_id") or "").strip()
            if eid in cancelled_events:
                continue

            ref_key = (ev.get("transaction_reference") or ev.get("source_id") or eid).strip()
            st = (ev.get("status") or "settled").lower()

            if ref_key in event_dict:
                existing = event_dict[ref_key]
                exist_st = (existing.get("status") or "settled").lower()
                if exist_st == "pending" and st == "settled":
                    event_dict[ref_key] = ev
                    continue
                if ev.get("created_at", "") > existing.get("created_at", ""):
                    event_dict[ref_key] = ev
                    continue
                if eid > existing.get("event_id", ""):
                    event_dict[ref_key] = ev
                    continue
            else:
                event_dict[ref_key] = ev

        # 4. Resolve amounts and classify
        cleaned_events = []
        user_prof = self.profiles.get(user_id, {})
        protected_set = user_prof.get("protected_categories", self.PROTECTED_CATEGORIES)

        for ev in event_dict.values():
            eid = (ev.get("event_id") or "").strip()
            d = parse_date(ev.get("date") or ev.get("event_date"))
            if not d:
                continue

            direction = (ev.get("direction") or "debit").strip().lower()
            status = (ev.get("status") or "settled").strip().lower()
            cat = (ev.get("category") or "").strip().lower()
            typ = (ev.get("type") or ev.get("event_type") or "").strip().lower()

            if direction == "credit" and status == "pending":
                continue

            if direction == "credit" and d > req_date:
                if any(w in cat or w in typ for w in ["bonus", "lottery", "investment", "commission", "refund"]):
                    continue

            if eid in amended_amounts:
                amt = amended_amounts[eid]
                res_status = "resolved"
            else:
                amt, res_status = self.resolve_event_amount(ev, home_curr, d)

            if res_status == "unresolved_credit":
                continue

            is_unresolved_debit = (res_status == "unresolved_debit")
            if is_unresolved_debit:
                amt = DECIMAL_ZERO

            is_protected = (cat in protected_set) or any(p in cat for p in protected_set)
            is_discretionary = (not is_protected) and (direction == "debit")

            cleaned_events.append({
                "event_id": eid,
                "date": d,
                "amount": amt,
                "direction": direction,
                "status": status,
                "category": cat,
                "is_protected": is_protected,
                "is_discretionary": is_discretionary,
                "is_unresolved_debit": is_unresolved_debit,
                "raw": ev,
            })

        cleaned_events.sort(key=lambda x: x["date"])
        return cleaned_events

    def simulate_cash_flow_trajectory(
        self,
        current_balance: Decimal,
        events: list,
        start_date: datetime.date,
        horizon_days: int = 90,
        spending_cuts: dict = None,
        planned_payments: list = None
    ) -> tuple:
        """
        Simulates forward chronological daily balance trajectory.
        Returns:
            (min_balance_reached, daily_balances_dict, has_unresolved_debit_violation)
        """
        spending_cuts = spending_cuts or {}
        planned_payments = planned_payments or []

        ev_by_date = {}
        for ev in events:
            if ev["date"] >= start_date:
                ev_by_date.setdefault(ev["date"], []).append(ev)

        pmts_by_date = {}
        for p_date, p_amt in planned_payments:
            pmts_by_date.setdefault(p_date, []).append(p_amt)

        balance = current_balance
        min_balance_seen = balance
        daily_balances = {start_date: balance}
        unresolved_debit_seen = False

        curr = start_date
        end_date = start_date + timedelta(days=horizon_days)

        while curr <= end_date:
            if curr in pmts_by_date:
                for p_amt in pmts_by_date[curr]:
                    balance -= p_amt

            if curr in ev_by_date:
                for ev in ev_by_date[curr]:
                    if ev.get("is_unresolved_debit"):
                        unresolved_debit_seen = True

                    eid = ev["event_id"]
                    amt = ev["amount"]

                    if eid in spending_cuts:
                        cut_val = spending_cuts[eid]
                        if cut_val == "cancel":
                            amt = DECIMAL_ZERO
                        elif isinstance(cut_val, Decimal):
                            amt = max(DECIMAL_ZERO, cut_val)

                    if ev["direction"] == "credit":
                        balance += amt
                    else:
                        balance -= amt

            if balance < min_balance_seen:
                min_balance_seen = balance

            daily_balances[curr] = balance
            curr += timedelta(days=1)

        return min_balance_seen, daily_balances, unresolved_debit_seen

    def calculate_safe_today(
        self,
        current_balance: Decimal,
        min_balance: Decimal,
        events: list,
        req_date: datetime.date,
        requested_amount: Decimal,
    ) -> Decimal:
        """
        amount_safe_to_pay is the largest amount safely payable on request_date
        while guaranteeing projected balance >= min_balance at all future dates.
        """
        min_seen, _, unresolved_debit_seen = self.simulate_cash_flow_trajectory(
            current_balance=current_balance,
            events=events,
            start_date=req_date,
            horizon_days=90,
            planned_payments=[]
        )

        if unresolved_debit_seen:
            return DECIMAL_ZERO

        max_safe = min_seen - min_balance
        if max_safe <= DECIMAL_ZERO:
            return DECIMAL_ZERO
        return max(DECIMAL_ZERO, min(requested_amount, round_curr(max_safe)))

    def find_earliest_safe_full_date(
        self,
        current_balance: Decimal,
        min_balance: Decimal,
        events: list,
        req_date: datetime.date,
        requested_amount: Decimal,
        horizon_days: int = 120
    ):
        """
        Finds the first chronological date on or after req_date where paying
        the FULL purchase preserves balance >= min_balance for the entire forecast window.
        """
        curr = req_date
        end_date = req_date + timedelta(days=horizon_days)

        while curr <= end_date:
            min_seen, _, unresolved_debit_seen = self.simulate_cash_flow_trajectory(
                current_balance=current_balance,
                events=events,
                start_date=req_date,
                horizon_days=(curr - req_date).days + 60,
                planned_payments=[(curr, requested_amount)]
            )
            if not unresolved_debit_seen and min_seen >= min_balance:
                return curr
            curr += timedelta(days=1)

        return None

    def validate_payment_option(
        self,
        opt: dict,
        current_balance: Decimal,
        min_balance: Decimal,
        events: list,
        req_date: datetime.date,
        requested_amount: Decimal,
        deadline: datetime.date = None
    ) -> tuple:
        """
        Individually validates a supplied payment option:
        - Accepts '|' and ';' delimiters.
        - Exact sum matches requested amount.
        - All payment dates valid and <= deadline.
        - Balance never violates minimum balance.
        """
        raw_schedule = opt.get("payment_schedule") or opt.get("schedule") or opt.get("payment_plan") or ""
        if not raw_schedule:
            return False, [], "Empty schedule"

        items = [x.strip() for x in re.split(r"[|;]", raw_schedule) if x.strip()]
        payments = []
        total = DECIMAL_ZERO

        for item in items:
            parts = item.split(":")
            if len(parts) != 2:
                return False, [], "Invalid item format"
            p_date = parse_date(parts[0])
            p_amt = to_dec(parts[1])
            if not p_date or p_amt <= DECIMAL_ZERO:
                return False, [], "Invalid date or non-positive amount"
            if p_date < req_date:
                return False, [], "Payment date in past"
            if deadline and p_date > deadline:
                return False, [], "Payment date exceeds deadline"
            payments.append((p_date, p_amt))
            total += p_amt

        if round_curr(total) != round_curr(requested_amount):
            return False, [], f"Total mismatch: {total} vs {requested_amount}"

        max_p_date = max(p[0] for p in payments)
        sim_days = (max_p_date - req_date).days + 60
        min_seen, _, unresolved_debit_seen = self.simulate_cash_flow_trajectory(
            current_balance=current_balance,
            events=events,
            start_date=req_date,
            horizon_days=sim_days,
            planned_payments=payments
        )
        if unresolved_debit_seen or min_seen < min_balance:
            return False, [], "Violates minimum balance or has unresolved debit"

        return True, payments, "Valid"

    def evaluate_spending_changes(
        self,
        current_balance: Decimal,
        min_balance: Decimal,
        events: list,
        req_date: datetime.date,
        requested_amount: Decimal,
    ) -> tuple:
        """
        Evaluates non-protected discretionary adjustments:
        - Single cancellations: event_id:cancel
        - Single reductions: event_id:target_amount
        - Composite adjustments: event_1:cancel|event_2:target_amount
        """
        discretionary_debits = [
            ev for ev in events
            if ev["date"] >= req_date and ev["is_discretionary"] and ev["amount"] > DECIMAL_ZERO
        ]
        if not discretionary_debits:
            return False, {}, ""

        # 1. Single cancellation
        for ev in discretionary_debits:
            eid = ev["event_id"]
            cuts = {eid: "cancel"}
            min_seen, _, unres = self.simulate_cash_flow_trajectory(
                current_balance=current_balance,
                events=events,
                start_date=req_date,
                horizon_days=90,
                spending_cuts=cuts,
                planned_payments=[(req_date, requested_amount)]
            )
            if not unres and min_seen >= min_balance:
                return True, cuts, f"{eid}:cancel"

        # 2. Targeted reduction to specific amount
        min_seen_no_cut, _, _ = self.simulate_cash_flow_trajectory(
            current_balance=current_balance,
            events=events,
            start_date=req_date,
            horizon_days=90,
            planned_payments=[(req_date, requested_amount)]
        )
        shortfall = min_balance - min_seen_no_cut

        for ev in discretionary_debits:
            eid = ev["event_id"]
            if shortfall > DECIMAL_ZERO and ev["amount"] > shortfall:
                new_amt = round_curr(ev["amount"] - shortfall)
                cuts = {eid: new_amt}
                min_seen, _, unres = self.simulate_cash_flow_trajectory(
                    current_balance=current_balance,
                    events=events,
                    start_date=req_date,
                    horizon_days=90,
                    spending_cuts=cuts,
                    planned_payments=[(req_date, requested_amount)]
                )
                if not unres and min_seen >= min_balance:
                    return True, cuts, f"{eid}:{format_amount(new_amt)}"

        # 3. Composite adjustment: cancel one event and reduce another
        if len(discretionary_debits) >= 2:
            for i, ev1 in enumerate(discretionary_debits):
                for j, ev2 in enumerate(discretionary_debits):
                    if i == j:
                        continue
                    cuts = {ev1["event_id"]: "cancel"}
                    min_seen_cut1, _, _ = self.simulate_cash_flow_trajectory(
                        current_balance=current_balance,
                        events=events,
                        start_date=req_date,
                        horizon_days=90,
                        spending_cuts=cuts,
                        planned_payments=[(req_date, requested_amount)]
                    )
                    shortfall_rem = min_balance - min_seen_cut1
                    if shortfall_rem > DECIMAL_ZERO and ev2["amount"] > shortfall_rem:
                        new_amt2 = round_curr(ev2["amount"] - shortfall_rem)
                        cuts[ev2["event_id"]] = new_amt2
                        min_seen_comp, _, unres = self.simulate_cash_flow_trajectory(
                            current_balance=current_balance,
                            events=events,
                            start_date=req_date,
                            horizon_days=90,
                            spending_cuts=cuts,
                            planned_payments=[(req_date, requested_amount)]
                        )
                        if not unres and min_seen_comp >= min_balance:
                            desc = f"{ev1['event_id']}:cancel|{ev2['event_id']}:{format_amount(new_amt2)}"
                            return True, cuts, desc

        return False, {}, ""

    def evaluate_request(self, req: dict) -> dict:
        """Evaluates a single purchase request deterministically."""
        req_id = (req.get("request_id") or "").strip()
        uid = (req.get("user_id") or req.get("profile_id") or "").strip()
        req_date = parse_date(req.get("request_date") or req.get("date"))
        amount = to_dec(req.get("requested_amount") or req.get("amount") or req.get("purchase_amount"))
        deadline = parse_date(req.get("desired_completion_date") or req.get("deadline") or req.get("purchase_deadline"))
        allows_partial = str(req.get("allows_partial_payment") or "false").strip().lower() == "true"

        prof = self.profiles.get(uid, {
            "current_balance": DECIMAL_ZERO,
            "minimum_balance_to_keep": DECIMAL_ZERO,
            "home_currency": "USD",
            "protected_categories": self.PROTECTED_CATEGORIES
        })
        current_balance = prof["current_balance"]
        min_balance = prof["minimum_balance_to_keep"]
        home_curr = prof["home_currency"]

        events = self.process_events(uid, home_curr, req_date)
        safe_today = self.calculate_safe_today(current_balance, min_balance, events, req_date, amount)

        # 1. Affordable Now (Full Payment Today)
        if safe_today >= amount:
            return {
                "request_id": req_id,
                "amount_safe_to_pay": format_amount(amount),
                "affordability_status": "affordable_now",
                "recommended_payment_method": "full_payment",
                "payment_plan": "",
                "earliest_date_for_full_payment": format_date(req_date),
                "spending_changes_needed": "",
                "decision_explanation": (
                    f"Affordable now. Balance remains safely above minimum reserve requirement "
                    f"after full purchase of {format_amount(amount)} {home_curr}."
                ),
            }

        # 2. Evaluate Supplied Payment Options and Synthesized Partial Payment
        valid_plans = []
        supplied_options = self.options_by_request.get(req_id, [])

        for opt in supplied_options:
            is_valid, pmts, _ = self.validate_payment_option(
                opt, current_balance, min_balance, events, req_date, amount, deadline
            )
            if is_valid:
                opt_id = opt.get("payment_option_id") or opt.get("option_id") or "opt"
                opt_type = (opt.get("option_type") or opt.get("type") or "installments").strip().lower()
                method = "partial_payment" if "partial" in opt_type else "installments"
                schedule_str = "|".join(f"{format_date(d)}:{format_amount(a)}" for d, a in pmts)
                last_d = max(p[0] for p in pmts)
                valid_plans.append({
                    "option_id": opt_id,
                    "method": method,
                    "schedule_str": schedule_str,
                    "payments": pmts,
                    "completes_by_deadline": (deadline is None) or (last_d <= deadline),
                    "total_paid": sum(p[1] for p in pmts),
                    "start_date": min(p[0] for p in pmts),
                    "num_payments": len(pmts),
                    "spending_changes": ""
                })

        # Dynamic Partial Payment Plan Synthesis
        if allows_partial and safe_today > DECIMAL_ZERO and safe_today < amount:
            rem_amt = amount - safe_today
            max_search_days = (deadline - req_date).days if deadline else 90
            earliest_rem_d = None
            curr_d = req_date + timedelta(days=1)
            end_search_d = req_date + timedelta(days=max_search_days)

            while curr_d <= end_search_d:
                test_pmts = [(req_date, safe_today), (curr_d, rem_amt)]
                sim_days = (curr_d - req_date).days + 60
                min_seen, _, unres = self.simulate_cash_flow_trajectory(
                    current_balance=current_balance,
                    events=events,
                    start_date=req_date,
                    horizon_days=sim_days,
                    planned_payments=test_pmts
                )
                if not unres and min_seen >= min_balance:
                    earliest_rem_d = curr_d
                    break
                curr_d += timedelta(days=1)

            if earliest_rem_d and (deadline is None or earliest_rem_d <= deadline):
                synth_schedule = f"{format_date(req_date)}:{format_amount(safe_today)}|{format_date(earliest_rem_d)}:{format_amount(rem_amt)}"
                valid_plans.append({
                    "option_id": "synth_partial",
                    "method": "partial_payment",
                    "schedule_str": synth_schedule,
                    "payments": [(req_date, safe_today), (earliest_rem_d, rem_amt)],
                    "completes_by_deadline": True,
                    "total_paid": amount,
                    "start_date": req_date,
                    "num_payments": 2,
                    "spending_changes": ""
                })

        # Rank plans according to Challenge Ranking Hierarchy
        if valid_plans:
            valid_plans.sort(key=lambda p: (
                0 if p["completes_by_deadline"] else 1,
                0 if not p["spending_changes"] else 1,
                p["total_paid"],
                p["start_date"],
                p["num_payments"],
                p["option_id"]
            ))
            best = valid_plans[0]
            earliest_d = max(p[0] for p in best["payments"])
            if best["method"] == "partial_payment":
                expl = f"Affordable with plan using partial payment: {format_amount(safe_today)} now and remainder on {format_date(earliest_d)}."
            else:
                expl = f"Affordable with plan using supplied installment option."
            return {
                "request_id": req_id,
                "amount_safe_to_pay": format_amount(safe_today),
                "affordability_status": "affordable_with_plan",
                "recommended_payment_method": best["method"],
                "payment_plan": best["schedule_str"],
                "earliest_date_for_full_payment": format_date(earliest_d),
                "spending_changes_needed": "",
                "decision_explanation": expl,
            }

        # 3. Affordable with Spending Adjustments
        can_cut, _, cut_desc = self.evaluate_spending_changes(
            current_balance, min_balance, events, req_date, amount
        )
        if can_cut:
            return {
                "request_id": req_id,
                "amount_safe_to_pay": format_amount(safe_today),
                "affordability_status": "affordable_with_plan",
                "recommended_payment_method": "full_payment",
                "payment_plan": "",
                "earliest_date_for_full_payment": format_date(req_date),
                "spending_changes_needed": cut_desc,
                "decision_explanation": f"Affordable with plan by applying spending adjustments: {cut_desc}.",
            }

        # 4. Affordable Later (Wait for confirmed income/salary)
        earliest_full_date = self.find_earliest_safe_full_date(
            current_balance, min_balance, events, req_date, amount
        )
        if earliest_full_date:
            return {
                "request_id": req_id,
                "amount_safe_to_pay": format_amount(safe_today),
                "affordability_status": "affordable_later",
                "recommended_payment_method": "wait",
                "payment_plan": "",
                "earliest_date_for_full_payment": format_date(earliest_full_date),
                "spending_changes_needed": "",
                "decision_explanation": (
                    f"Affordable later. Full purchase safe on {format_date(earliest_full_date)} "
                    f"after confirmed income arrives."
                ),
            }

        # 5. Not Affordable
        return {
            "request_id": req_id,
            "amount_safe_to_pay": format_amount(safe_today),
            "affordability_status": "not_affordable",
            "recommended_payment_method": "not_recommended",
            "payment_plan": "",
            "earliest_date_for_full_payment": "",
            "spending_changes_needed": "",
            "decision_explanation": (
                f"Purchase of {format_amount(amount)} {home_curr} violates reserve constraints "
                f"across the forecast window."
            ),
        }