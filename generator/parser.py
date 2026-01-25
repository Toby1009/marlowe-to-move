import json
from marlowe_types import (
    # Contract Types
    Contract,
    Close,
    Pay,
    If,
    When,
    Let,
    Assert,  # ADDED
    Case,

    # Party and Payee
    Party,
    AddressParty,
    RoleParty,
    Payee,
    AccountPayee,
    PartyPayee,

    # Token
    Token,

    # Action Types
    Deposit,
    Choice,
    Notify,

    # Value Types
    Value,
    AvailableMoney,
    Constant,
    AddValue,
    SubValue,
    MulValue,
    DivValue,
    NegValue,
    ChoiceValue,
    TimeIntervalStart,  # ADDED
    TimeIntervalEnd,    # ADDED
    UseValue,
    Cond,

    # Observation Types
    Observation,
    TrueObs,
    FalseObs,
    AndObs,             # ADDED
    OrObs,              # ADDED
    NotObs,             # ADDED
    ChoseSomething,     # ADDED
    ValueGE,            # ADDED
    ValueGT,            # ADDED
    ValueLT,            # ADDED
    ValueLE,            # ADDED
    ValueEQ,            # ADDED

    # Helpers
    ChoiceId,           # ADDED
    Bound               # ADDED
)

# === ADDED Helper Parsers ===

def parse_choice_id(data: dict) -> ChoiceId:
    """Parses a ChoiceId object """
    return ChoiceId(
        name = data["choice_name"],
        by = parse_party(data["choice_owner"])
    )

def parse_bound(data: dict) -> Bound:
    """Parses a Bound object """
    return Bound(
        from_value=data["from"],
        to_value=data["to"]
    )

# === Observation Parser (FIXED) ===
def parse_observation(data) -> Observation:
    """Parses any Observation type """
    if data is True:
        return TrueObs()
    elif data is False:
        return FalseObs()

    if isinstance(data, dict):
        # Logical Ops
        if "both" in data and "and" in data:
            return AndObs(parse_observation(data["both"]), parse_observation(data["and"]))
        if "either" in data and "or" in data:
            return OrObs(parse_observation(data["either"]), parse_observation(data["or"]))
        if "not" in data:
            return NotObs(parse_observation(data["not"]))

        # Choice
        if "chose_something_for" in data:
            return ChoseSomething(parse_choice_id(data["chose_something_for"]))

        # Value Comparisons
        if "value" in data:
            val_lhs = parse_value(data["value"])
            if "ge_than" in data:
                return ValueGE(val_lhs, parse_value(data["ge_than"]))
            if "gt" in data:
                return ValueGT(val_lhs, parse_value(data["gt"]))
            if "lt" in data:
                return ValueLT(val_lhs, parse_value(data["lt"]))
            if "le_than" in data:
                return ValueLE(val_lhs, parse_value(data["le_than"]))
            if "equal_to" in data:
                return ValueEQ(val_lhs, parse_value(data["equal_to"]))

    raise ValueError(f"Unsupported observation: {data}")

# === Core Parsers (Party, Payee, Token are OK) ===

def parse_party(data: dict) -> Party:
    if "role_token" in data:
        return RoleParty(role_token=data["role_token"])
    elif "address" in data:
        return AddressParty(address=data["address"])
    else:
        raise ValueError(f"Invalid Party format: {data}")

def parse_payee(data: dict) -> Payee:
    if "account" in data:
        return AccountPayee(account=parse_party(data["account"]))
    elif "party" in data:
        return PartyPayee(party=parse_party(data["party"]))
    else:
        raise ValueError(f"Invalid Payee format: {data}")

def parse_token(data: dict) -> Token:
    return Token(
        currency_symbol=data.get("currency_symbol", ""),
        token_name=data.get("token_name", ""),
    )

# === Action Parser (FIXED) ===

def parse_action(data: dict):
    if "deposits" in data:
        return Deposit(
            party=parse_party(data["party"]),
            into_account=parse_party(data["into_account"]),
            token=parse_token(data["of_token"]),
            amount=parse_value(data["deposits"]), # Correct, 'deposits' is a Value [cite: 1893]
        )
    elif "for_choice" in data:  # CHANGED: Key is "for_choice" [cite: 1895]
        return Choice(
            choice_id= parse_choice_id(data["for_choice"]), # CHANGED: Must parse ChoiceId
            bounds=[parse_bound(b) for b in data["choose_between"]] # CHANGED: Key is "choose_between" [cite: 1896, 1907]
        )
    elif "notify_if" in data: # CHANGED: Key is "notify_if"
        return Notify(observation=parse_observation(data["notify_if"]))
    else:
        raise ValueError(f"Unsupported action: {data}")


def parse_case(data: dict) -> Case:
    return Case(action=parse_action(data["case"]), then=parse_contract(data["then"]))

# === Value Parser (FIXED) ===

def parse_value(data) -> "Value":
    """Parses any Value type [cite: 1643-1690]"""
    if isinstance(data, int):
        return Constant(data)

    if isinstance(data, str): # ADDED: Handle string constants
        if data == "time_interval_start":
            return TimeIntervalStart()
        if data == "time_interval_end":
            return TimeIntervalEnd()

    if isinstance(data, dict):
        if "amount_of_token" in data and "in_account" in data:
            # CHANGED: Must parse inner objects
            return AvailableMoney(
                token=parse_token(data["amount_of_token"]),
                party=parse_party(data["in_account"])
            )
        if "value_of_choice" in data:
            # CHANGED: Must parse ChoiceId
            return ChoiceValue(parse_choice_id(data["value_of_choice"]))

        # Arithmetic
        if "add" in data and "and" in data:
            # CHANGED: Arguments were swapped
            return AddValue(parse_value(data["add"]), parse_value(data["and"]))
        if "value" in data and "minus" in data:
            # CHANGED: Keys were "sub" and list
            return SubValue(parse_value(data["value"]), parse_value(data["minus"]))
        if "multiply" in data and "times" in data:
            # CHANGED: Arguments were swapped and not recursive
            return MulValue(parse_value(data["multiply"]), parse_value(data["times"]))
        if "divide" in data and "by" in data:
            # CHANGED: Keys were "div" and list
            return DivValue(parse_value(data["divide"]), parse_value(data["by"]))
        if "negate" in data:
            return NegValue(parse_value(data["negate"]))

        # Other
        if "constant" in data:
            return Constant(data["constant"])
        if "use_value" in data:
            return UseValue(data["use_value"])
        if "if" in data and "then" in data and "else" in data:
            # CHANGED: Structure was nested under "cond"
            return Cond(
                condition=parse_observation(data["if"]),
                true_value=parse_value(data["then"]),
                false_value=parse_value(data["else"]),
            )

    raise ValueError(f"Unsupported value: {data}")

# === Contract Parser (FIXED) ===

def parse_contract(data) -> Contract:
    if isinstance(data, str):
        if data == "close":
            return Close()
        else:
            raise ValueError(f"Unknown contract shorthand: {data}")

    if not isinstance(data, dict):
        raise ValueError(f"Invalid contract data: {data}")

    if "if" in data and "then" in data and "else" in data:
        return If(
            cond=parse_observation(data["if"]),
            then=parse_contract(data["then"]),
            else_=parse_contract(data["else"]),
        )
    if "then" in data and "let" in data and "be" in data:
        return Let(
            name=data["let"],
            value=parse_value(data["be"]),
            then=parse_contract(data["then"]),
        )

    # ADDED: Missing Assert contract [cite: 2038-2042, 2063-2064]
    if "assert" in data and "then" in data:
        return Assert(
            obs=parse_observation(data["assert"]),
            then=parse_contract(data["then"])
        )

    if (
        "token" in data
        and "to" in data
        and "then" in data
        and "pay" in data
        and "from_account" in data
    ):
        return Pay(
            from_account=parse_party(data["from_account"]),
            to=parse_payee(data["to"]),
            token=parse_token(data["token"]),
            value=parse_value(data["pay"]),
            then=parse_contract(data["then"]),
        )
    if "when" in data and "timeout" in data and "timeout_continuation" in data:
        return When(
            cases=[parse_case(c) for c in data["when"]],
            timeout=data["timeout"],
            timeout_continuation=parse_contract(data["timeout_continuation"]),
        )

    raise ValueError(f"Unrecognized contract structure: {data}")


# === Example usage ===
if __name__ == "__main__":
    # 測試 JSON (請確保您有一個 test.json 檔案)
    try:
        with open("swap_ada.json") as f:
            json_data = json.load(f)

        contract_ast = parse_contract(json_data)
        print("Successfully parsed contract:")
        print(contract_ast)

    except FileNotFoundError:
        print("Error: test case not found. Please create one.")
    except (ValueError, KeyError) as e:
        print(f"Error parsing JSON: {e}")
