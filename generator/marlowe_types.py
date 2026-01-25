from dataclasses import dataclass
from typing import List, Union


# === Contract Variants ===
@dataclass
class Close:
    kind: str = "close"


@dataclass
class Pay:
    from_account: "Party"
    to: "Payee"
    token: "Token"
    value: "Value"
    then: "Contract"


@dataclass
class If:
    cond: "Observation"
    then: "Contract"
    else_: "Contract"


@dataclass
class When:
    cases: List["Case"]
    timeout: int
    timeout_continuation: "Contract"


@dataclass
class Let:
    name: str
    value: "Value"
    then: "Contract"


@dataclass
class Assert:
    obs: "Observation"
    then: "Contract"


Contract = Union[Close, Pay, If, When, Let, Assert]

# === Case and Actions ===

@dataclass
class Bound:
    from_value: int
    to_value: int

@dataclass
class Deposit:
    into_account: "Party"
    party: "Party"
    token: "Token"
    amount: "Value"


@dataclass
class Choice:
    choice_id: "ChoiceId"
    bounds: List[Bound]


@dataclass
class Notify:
    observation: "Observation"


Action = Union[Deposit, Choice, Notify]


@dataclass
class Case:
    action: Action
    then: Contract


@dataclass
class ChoiceId:
    name: str
    by: "Party"


@dataclass
class Token:
    currency_symbol: str
    token_name: str


@dataclass
class AddressParty:
    address: str


@dataclass
class RoleParty:
    role_token: str


Party = Union[AddressParty, RoleParty]


@dataclass
class AccountPayee:
    account: Party


@dataclass
class PartyPayee:
    party: Party


Payee = Union[AccountPayee, PartyPayee]


# === Value AST 節點 ===


@dataclass
class AvailableMoney:
    token: "Token"
    party: "Party"


@dataclass
class Constant:
    value: int


@dataclass
class NegValue:
    value: "Value"


@dataclass
class AddValue:
    lhs: "Value"
    rhs: "Value"


@dataclass
class SubValue:
    lhs: "Value"
    rhs: "Value"


@dataclass
class MulValue:
    lhs: "Value"
    rhs: "Value"


@dataclass
class DivValue:
    lhs: "Value"
    rhs: "Value"


@dataclass
class ChoiceValue:
    choice_id: "ChoiceId"


@dataclass
class TimeIntervalStart:
    pass


@dataclass
class TimeIntervalEnd:
    pass


@dataclass
class UseValue:
    value_id: str


@dataclass
class Cond:
    condition: "Observation"
    true_value: "Value"
    false_value: "Value"


Value = Union[
    AvailableMoney,
    Constant,
    NegValue,
    AddValue,
    SubValue,
    MulValue,
    DivValue,
    ChoiceValue,
    TimeIntervalStart,
    TimeIntervalEnd,
    UseValue,
    Cond,
]


# === Observation AST 節點 ===


@dataclass
class AndObs:
    left: "Observation"
    right: "Observation"


@dataclass
class OrObs:
    left: "Observation"
    right: "Observation"


@dataclass
class NotObs:
    obs: "Observation"


@dataclass
class ChoseSomething:
    choice_id: "ChoiceId"


@dataclass
class ValueGE:
    lhs: "Value"
    rhs: "Value"


@dataclass
class ValueGT:
    lhs: "Value"
    rhs: "Value"


@dataclass
class ValueLT:
    lhs: "Value"
    rhs: "Value"


@dataclass
class ValueLE:
    lhs: "Value"
    rhs: "Value"


@dataclass
class ValueEQ:
    lhs: "Value"
    rhs: "Value"


@dataclass
class TrueObs:
    pass


@dataclass
class FalseObs:
    pass


Observation = Union[
    AndObs,
    OrObs,
    NotObs,
    ChoseSomething,
    ValueGE,
    ValueGT,
    ValueLT,
    ValueLE,
    ValueEQ,
    TrueObs,
    FalseObs,
]


@dataclass
class Condition:
    op: str
    lhs: Value
    rhs: Value
